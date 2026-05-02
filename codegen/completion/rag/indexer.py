"""
RAG Indexer - CLI tool to build and manage the code knowledge base

Usage:
    python -m completion.rag.indexer index <directory> [--project-path PATH]
    python -m completion.rag.indexer clear [--project-path PATH]
    python -m completion.rag.indexer stats [--project-path PATH]
    python -m completion.rag.indexer search <query> [--project-path PATH]
"""

import argparse
import os
from pathlib import Path

from completion.rag.chunker import CodeChunker
from completion.rag.vector_store import get_vector_store, clear_store_cache
from completion.rag.retriever import retrieve_relevant_code
from completion.rag.graph_store import get_graph_store, clear_graph_store_cache
from completion.rag.code_parser import parse_file_with_lsp
from completion.rag.config import get_vector_store_dir, LSP_COMMAND, LSP_FALLBACK_COMMANDS


def get_file_mtime(path: Path) -> float:
    """Get file modification time."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def build_index(directory: Path, project_path: str = "", verbose: bool = True, incremental: bool = True) -> int:
    """
    Build or incrementally update the RAG index (vector + graph) from a directory of code files.

    Args:
        directory: Root directory to index
        project_path: Project identifier for vector store isolation
        verbose: Whether to print progress
        incremental: If True, only update changed files. If False, full rebuild.

    Returns:
        Number of chunks indexed
    """
    if verbose:
        print(f"Indexing code from: {directory}")
        if project_path:
            print(f"Project: {project_path}")
        if incremental:
            print("Mode: Incremental (only changed files)")
        else:
            print("Mode: Full rebuild")

    chunker = CodeChunker()
    vector_store = get_vector_store(project_path)
    graph_store = get_graph_store(project_path)

    # Collect all chunks from disk
    all_chunks = list(chunker.chunk_directory(directory))
    
    if verbose:
        print(f"Found {len(all_chunks)} chunks in source files...")

    if not all_chunks:
        if verbose:
            print("No code files found to index.")
        return 0

    if not incremental:
        # Full rebuild: clear existing index and graph
        if vector_store.exists():
            if verbose:
                print("Clearing existing vector index for full rebuild...")
            vector_store.clear()
        if graph_store.exists():
            if verbose:
                print("Clearing existing graph for full rebuild...")
            graph_store.clear()
    else:
        # Incremental: determine which files changed
        if vector_store.exists():
            indexed_sources = vector_store.get_sources()
            current_sources_normalized = set()
            for c in all_chunks:
                src = c.source
                if not os.path.isabs(src):
                    src = str(directory / src)
                current_sources_normalized.add(os.path.normpath(src))
            
            # Find deleted files
            deleted_sources = []
            for src in indexed_sources:
                normalized_src = os.path.normpath(src)
                if normalized_src not in current_sources_normalized:
                    deleted_sources.append(src)
            
            # Remove deleted files from index
            if deleted_sources:
                if verbose:
                    print(f"Removing {len(deleted_sources)} deleted files from index...")
                for src in deleted_sources:
                    vector_store.remove_by_source(src)
            
            # Filter to only changed/new files
            changed_chunks = []
            indexed_mtimes = vector_store.get_source_mtimes()
            for chunk in all_chunks:
                src = chunk.source
                if not os.path.isabs(src):
                    src = str(directory / src)
                src = os.path.normpath(src)

                if src not in indexed_sources:
                    changed_chunks.append(chunk)
                else:
                    current_mtime = get_file_mtime(Path(src))
                    if current_mtime > indexed_mtimes.get(src, 0.0):
                        changed_chunks.append(chunk)
            
            if changed_chunks and verbose:
                print(f"Updating {len(set(c.source for c in changed_chunks))} changed/new files...")
            
            # Remove changed files from index before re-adding
            changed_sources = set()
            for chunk in changed_chunks:
                src = chunk.source
                if not os.path.isabs(src):
                    src = str(directory / src)
                changed_sources.add(os.path.normpath(src))
            
            for src in changed_sources:
                if src in indexed_sources:
                    vector_store.remove_by_source(src)
            
            all_chunks = changed_chunks
        else:
            if verbose:
                print("No existing index found. Performing full index...")

    if not all_chunks:
        if verbose:
            print("No changes detected. Index is up to date.")
        return 0

    # Build vector index
    batch_size = 100
    total_indexed = 0

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        indexed = vector_store.add_chunks(batch)
        total_indexed += indexed

        if verbose:
            print(f"Indexed {total_indexed}/{len(all_chunks)} chunks...")

    # Build graph using LSP if available
    if verbose:
        print("Building code knowledge graph...")
    
    lsp_client = None
    lsp_commands = [LSP_COMMAND] + [c for c in LSP_FALLBACK_COMMANDS if c != LSP_COMMAND]

    for cmd in lsp_commands:
        try:
            from completion.rag.lsp_client import LSPClient
            if not LSPClient.is_command_available(cmd):
                if verbose:
                    print(f"  LSP command not found: {cmd}")
                continue

            lsp_client = LSPClient(
                command=cmd,
                workspace_path=str(directory),
            )
            if lsp_client.start():
                if verbose:
                    print(f"  Connected to Language Server: {cmd}")
                break
            else:
                if verbose:
                    print(f"  Warning: Could not start {cmd}, trying next...")
                lsp_client = None
        except Exception as e:
            if verbose:
                print(f"  Warning: {cmd} unavailable ({e}), trying next...")
            lsp_client = None

    if lsp_client is None and verbose:
        print(f"  No Language Server available, using fallback parser")
    
    indexed_files = set(c.source for c in all_chunks)
    total_entities = 0
    total_relations = 0
    
    try:
        for file_path_str in indexed_files:
            file_path = Path(file_path_str)
            if not file_path.is_absolute():
                file_path = directory / file_path
            
            result = parse_file_with_lsp(file_path, lsp_client)
            if result.entities:
                graph_store.add_entities(result.entities)
                total_entities += len(result.entities)
            if result.relations:
                graph_store.add_relations(result.relations)
                total_relations += len(result.relations)
            if result.errors and verbose:
                for error in result.errors:
                    print(f"  Parse error: {error}")
    finally:
        if lsp_client:
            lsp_client.stop()
    
    if total_entities > 0 or total_relations > 0:
        graph_store._save_graph()

    if verbose:
        store_dir = get_vector_store_dir(project_path)
        print(
            f"Done! Indexed {total_indexed} chunks from {len(set(c.source for c in all_chunks))} files."
        )
        print(f"Graph: {total_entities} entities, {total_relations} relations")
        print(f"Index saved to: {store_dir}")

    return total_indexed


def clear_index(project_path: str = "", verbose: bool = True):
    """Clear the RAG index and graph for a project"""
    vector_store = get_vector_store(project_path)
    graph_store = get_graph_store(project_path)

    if not vector_store.exists() and not graph_store.exists():
        if verbose:
            print("No index found to clear.")
        return

    vector_store.clear()
    graph_store.clear()
    clear_store_cache()
    clear_graph_store_cache()

    if verbose:
        print("Index and graph cleared successfully.")


def show_stats(project_path: str = ""):
    """Show statistics about the current index and graph"""
    vector_store = get_vector_store(project_path)
    graph_store = get_graph_store(project_path)

    if not vector_store.exists() and not graph_store.exists():
        print("No index found. Run 'index' command first.")
        return

    # Vector store stats
    if vector_store.exists():
        count = vector_store.count()
        print(f"Vector index:")
        print(f"  Total chunks: {count}")

        languages = {}
        for metadata in vector_store._metadata:
            lang = metadata.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1

        print("\n  Chunks by language:")
        for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
            print(f"    {lang}: {count}")

        sources = set(m["source"] for m in vector_store._metadata)
        print(f"\n  Total source files: {len(sources)}")

    # Graph stats
    if graph_store.exists():
        stats = graph_store.get_stats()
        print(f"\nKnowledge graph:")
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Edges: {stats['edges']}")
        print(f"  Vector chunks: {stats['vector_chunks']}")


def search_index(query: str, project_path: str = "", top_k: int = 5):
    """Search the index for a query"""
    vector_store = get_vector_store(project_path)

    if not vector_store.exists():
        print("No index found. Run 'index' command first.")
        return

    results = retrieve_relevant_code(query, vector_store, top_k=top_k)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:\n")

    for i, result in enumerate(results, 1):
        print(f"--- Result {i} (score: {result.score:.4f}) ---")
        print(f"Source: {result.source}")
        print(f"Language: {result.language}")
        print(f"Content:\n{result.content[:500]}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="RAG Indexer - Build and search code knowledge base"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index a directory of code")
    index_parser.add_argument("directory", type=Path, help="Directory to index")
    index_parser.add_argument(
        "--project-path", type=str, default="",
        help="Project path for vector store isolation (default: shared store)",
    )
    index_parser.add_argument(
        "--full", action="store_true", help="Force full rebuild instead of incremental"
    )
    index_parser.add_argument(
        "--no-verbose", action="store_true", help="Suppress progress output"
    )

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear the index")
    clear_parser.add_argument(
        "--project-path", type=str, default="",
        help="Project path for vector store isolation (default: shared store)",
    )
    clear_parser.add_argument(
        "--no-verbose", action="store_true", help="Suppress output"
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.add_argument(
        "--project-path", type=str, default="",
        help="Project path for vector store isolation (default: shared store)",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search the index")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--project-path", type=str, default="",
        help="Project path for vector store isolation (default: shared store)",
    )
    search_parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results to return"
    )

    args = parser.parse_args()

    project_path = getattr(args, "project_path", "")

    if args.command == "index":
        build_index(
            args.directory,
            project_path=project_path,
            verbose=not args.no_verbose,
            incremental=not args.full,
        )
    elif args.command == "clear":
        clear_index(project_path=project_path, verbose=not args.no_verbose)
    elif args.command == "stats":
        show_stats(project_path=project_path)
    elif args.command == "search":
        search_index(args.query, project_path=project_path, top_k=args.top_k)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
