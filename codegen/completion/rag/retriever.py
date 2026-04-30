"""
Retriever for RAG - retrieves relevant code snippets for a given query
"""

from dataclasses import dataclass
from typing import List, Optional

from .vector_store import VectorStore, get_vector_store
from .config import DEFAULT_TOP_K, MAX_CONTEXT_CHUNKS, SIMILARITY_THRESHOLD


@dataclass
class RetrievalResult:
    """Represents a retrieval result"""

    content: str
    source: str
    language: Optional[str]
    score: float
    chunk_index: int = 0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "language": self.language,
            "score": self.score,
            "chunk_index": self.chunk_index,
        }


def retrieve_relevant_code(
    query: str,
    vector_store: Optional[VectorStore] = None,
    top_k: int = DEFAULT_TOP_K,
    language: Optional[str] = None,
    max_context_chunks: int = MAX_CONTEXT_CHUNKS,
    project_path: str = "",
    min_score: float = SIMILARITY_THRESHOLD,
) -> List[RetrievalResult]:
    """
    Retrieve relevant code snippets for a given query.

    Args:
        query: The query text (e.g., code context from the editor)
        vector_store: Optional vector store instance (uses global if not provided)
        top_k: Number of results to retrieve
        language: Optional programming language filter
        max_context_chunks: Maximum chunks to include in context (for deduplication by source)
        project_path: Project path for vector store isolation
        min_score: Minimum similarity score threshold

    Returns:
        List of RetrievalResult objects, deduplicated by source file
    """
    if vector_store is None:
        vector_store = get_vector_store(project_path)

    if not vector_store.exists():
        return []

    # Search for similar chunks with threshold
    raw_results = vector_store.search(
        query, top_k=top_k * 3, filter_language=language, min_score=min_score
    )

    # Deduplicate by source, keeping highest-scoring chunk from each file
    seen_sources = set()
    results: List[RetrievalResult] = []

    for metadata, score in raw_results:
        source = metadata["source"]

        if source not in seen_sources:
            seen_sources.add(source)
            results.append(
                RetrievalResult(
                    content=metadata["content"],
                    source=source,
                    language=metadata.get("language"),
                    score=score,
                    chunk_index=metadata.get("chunk_index", 0),
                )
            )

            if len(results) >= max_context_chunks:
                break

    return results


def format_retrieval_context(
    results: List[RetrievalResult],
    include_source: bool = True,
    max_length: int = 2000,
) -> str:
    """
    Format retrieval results into a context string for LLM consumption.

    Args:
        results: List of RetrievalResult objects
        include_source: Whether to include source file path in output
        max_length: Maximum total length of the context

    Returns:
        Formatted context string
    """
    if not results:
        return ""

    context_parts = []
    total_length = 0

    for result in results:
        part = []

        if include_source:
            part.append(f"// Source: {result.source}")

        part.append(result.content)

        chunk_text = "\n".join(part)

        # Check if adding this chunk would exceed max_length
        if total_length + len(chunk_text) > max_length:
            # Try to fit a truncated version
            remaining = max_length - total_length
            if remaining > 100:  # Only add if we have space for meaningful content
                part[-1] = result.content[: remaining - len(part[0]) - 5] + "..."
                chunk_text = "\n".join(part)
                context_parts.append(chunk_text)
            break

        context_parts.append(chunk_text)
        total_length += len(chunk_text) + 2  # +2 for newlines

    return "\n\n".join(context_parts)


def augment_context_with_retrieval(
    prompt: str,
    suffix: str = "",
    vector_store: Optional[VectorStore] = None,
    include_context: bool = True,
    project_path: str = "",
) -> str:
    """
    Augment a code prompt with retrieved relevant context.

    Args:
        prompt: The code prompt (before cursor)
        suffix: The code suffix (after cursor)
        vector_store: Optional vector store instance
        include_context: Whether to include the retrieved context
        project_path: Project path for vector store isolation

    Returns:
        Augmented prompt with RAG context
    """
    full_context = prompt
    if suffix:
        full_context += "\n" + suffix

    results = retrieve_relevant_code(
        query=full_context,
        vector_store=vector_store,
        project_path=project_path,
    )

    if not results:
        return prompt

    # Format and append the retrieved context
    rag_context = format_retrieval_context(results)

    if not rag_context:
        return prompt

    # Prepend RAG context directly as natural code context
    augmented = f"{rag_context}\n\n{prompt}"

    return augmented
