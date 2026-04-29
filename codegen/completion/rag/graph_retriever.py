"""
Graph Retriever for Graph-RAG
Provides high-level retrieval interface combining graph traversal with semantic search.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .graph_store import GraphStore, get_graph_store
from .config import DEFAULT_TOP_K, MAX_CONTEXT_CHUNKS, SIMILARITY_THRESHOLD


@dataclass
class GraphRetrievalResult:
    """Represents a Graph-RAG retrieval result."""
    content: str
    source: str
    entity_type: str
    score: float
    node_id: str
    relation_path: List[str] = None
    
    def __post_init__(self):
        if self.relation_path is None:
            self.relation_path = []
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "entity_type": self.entity_type,
            "score": self.score,
            "node_id": self.node_id,
            "relation_path": self.relation_path,
        }


def retrieve_with_graph_rag(
    query: str,
    graph_store: Optional[GraphStore] = None,
    top_k: int = DEFAULT_TOP_K,
    max_context_chunks: int = MAX_CONTEXT_CHUNKS,
    project_path: str = "",
    graph_hops: int = 2,
    min_score: float = SIMILARITY_THRESHOLD,
) -> List[GraphRetrievalResult]:
    """
    Retrieve relevant code using Graph-RAG.
    
    Combines semantic similarity (vector search) with graph traversal
    to find not just similar code, but related code through call chains,
    inheritance, and imports.
    
    Args:
        query: The query text (code context)
        graph_store: Optional graph store instance
        top_k: Number of seed results from semantic search
        max_context_chunks: Maximum results to return
        project_path: Project path for store isolation
        graph_hops: Number of graph traversal hops
        min_score: Minimum relevance score
    
    Returns:
        List of GraphRetrievalResult objects
    """
    if graph_store is None:
        graph_store = get_graph_store(project_path)
    
    if not graph_store.exists() and not graph_store.vector_store.exists():
        return []
    
    # Use Graph-RAG hybrid retrieval
    raw_results = graph_store.graph_rag_retrieve(
        query=query,
        top_k=top_k,
        graph_hops=graph_hops,
        min_score=min_score,
    )
    
    # Deduplicate by source file and convert to results
    seen_sources = set()
    results: List[GraphRetrievalResult] = []
    
    for node_id, score, content in raw_results:
        if not graph_store.graph.has_node(node_id):
            continue
        
        attrs = graph_store.graph.nodes[node_id]
        source = attrs.get("source_file", "")
        entity_type = attrs.get("entity_type", "unknown")
        
        # Use source file for deduplication
        source_key = source or node_id
        
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            results.append(GraphRetrievalResult(
                content=content,
                source=source,
                entity_type=entity_type,
                score=score,
                node_id=node_id,
            ))
        
        if len(results) >= max_context_chunks:
            break
    
    return results


def format_graph_retrieval_context(
    results: List[GraphRetrievalResult],
    include_source: bool = True,
    include_entity_type: bool = True,
    max_length: int = 2000,
) -> str:
    """
    Format Graph-RAG retrieval results into a context string.
    
    Args:
        results: List of GraphRetrievalResult objects
        include_source: Whether to include source file path
        include_entity_type: Whether to include entity type label
        max_length: Maximum total length
    
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
        
        if include_entity_type and result.entity_type != "file":
            part.append(f"// Type: {result.entity_type}")
        
        part.append(result.content)
        
        chunk_text = "\n".join(part)
        
        if total_length + len(chunk_text) > max_length:
            remaining = max_length - total_length
            if remaining > 100:
                part[-1] = result.content[:remaining - len("\n".join(part[:-1])) - 5] + "..."
                chunk_text = "\n".join(part)
                context_parts.append(chunk_text)
            break
        
        context_parts.append(chunk_text)
        total_length += len(chunk_text) + 2
    
    return "\n\n".join(context_parts)


def augment_context_with_graph_rag(
    prompt: str,
    suffix: str = "",
    graph_store: Optional[GraphStore] = None,
    project_path: str = "",
    use_graph_rag: bool = True,
) -> str:
    """
    Augment a code prompt with Graph-RAG retrieved context.
    
    Args:
        prompt: Code prompt (before cursor)
        suffix: Code suffix (after cursor)
        graph_store: Optional graph store
        project_path: Project path
        use_graph_rag: Whether to use Graph-RAG
    
    Returns:
        Augmented prompt with Graph-RAG context
    """
    if not use_graph_rag:
        return prompt
    
    full_context = prompt
    if suffix:
        full_context += "\n" + suffix
    
    results = retrieve_with_graph_rag(
        query=full_context,
        graph_store=graph_store,
        project_path=project_path,
    )
    
    if not results:
        return prompt
    
    rag_context = format_graph_retrieval_context(results)
    
    if not rag_context:
        return prompt
    
    return f"""// Relevant code from knowledge base (Graph-RAG):
{rag_context}

// Current code context:
{prompt}"""
