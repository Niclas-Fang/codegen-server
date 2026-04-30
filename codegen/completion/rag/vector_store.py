"""
FAISS Vector Store for RAG
Provides embedding generation and vector storage using FAISS
with per-project isolation and embedding cache
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

from .chunker import Chunk, Document
from .config import (
    get_index_paths,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EMBEDDING_CACHE_SIZE,
)


class EmbeddingCache:
    """LRU cache for text embeddings to avoid recomputation."""
    
    def __init__(self, max_size: int = EMBEDDING_CACHE_SIZE):
        self.max_size = max_size
        self._cache: dict[str, np.ndarray] = {}
        self._access_order: list[str] = []
    
    def _update_access(self, key: str):
        """Move key to most recently used position."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def get(self, text: str) -> Optional[np.ndarray]:
        """Get embedding from cache if exists."""
        key = hash(text)
        if key in self._cache:
            self._update_access(key)
            return self._cache[key]
        return None
    
    def put(self, text: str, embedding: np.ndarray):
        """Store embedding in cache."""
        key = hash(text)
        if key in self._cache:
            self._update_access(key)
            self._cache[key] = embedding
            return
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            if oldest in self._cache:
                del self._cache[oldest]
        
        self._cache[key] = embedding
        self._access_order.append(key)
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()


class VectorStore:
    """
    FAISS-based vector store for code chunks with per-project isolation.
    """

    def __init__(
        self,
        project_path: str = "",
        embedding_model: str = EMBEDDING_MODEL,
        embedding_dimension: int = EMBEDDING_DIMENSION,
    ):
        self.project_path = project_path
        index_path, metadata_path = get_index_paths(project_path)
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension

        self._index = None
        self._metadata: List[dict] = []
        self._embedding_model = None  # Lazy loaded
        self._embedding_cache = EmbeddingCache()

    @property
    def index(self):
        """Lazy load FAISS index"""
        if self._index is None:
            self._load_index()
        return self._index

    def _load_index(self):
        """Load existing index from disk"""
        try:
            import faiss

            if self.index_path.exists():
                self._index = faiss.read_index(str(self.index_path))
                self._load_metadata()
            else:
                # Create new index
                self._index = faiss.IndexIDMap(
                    faiss.IndexFlatIP(self.embedding_dimension)
                )
        except ImportError:
            raise ImportError(
                "FAISS not installed. Install with: pip install faiss-cpu"
            )

    def _load_metadata(self):
        """Load metadata from disk"""
        if self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)

    def _save_index(self):
        """Save index and metadata to disk"""
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    def _get_embedding_model(self):
        """Lazy load sentence transformer model"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer(self.embedding_model)
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedding_model

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts with caching."""
        model = self._get_embedding_model()
        
        # Check cache for each text
        embeddings_list = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cached = self._embedding_cache.get(text)
            if cached is not None:
                embeddings_list.append(cached)
            else:
                embeddings_list.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Compute embeddings for uncached texts
        if uncached_texts:
            new_embeddings = model.encode(uncached_texts, show_progress_bar=False)
            # Normalize embeddings for cosine similarity
            norms = np.linalg.norm(new_embeddings, axis=1, keepdims=True)
            new_embeddings = new_embeddings / norms
            new_embeddings = new_embeddings.astype(np.float32)
            
            # Store in cache and fill results
            for idx, text, emb in zip(uncached_indices, uncached_texts, new_embeddings):
                self._embedding_cache.put(text, emb)
                embeddings_list[idx] = emb
        
        return np.array(embeddings_list)

    def add_chunks(self, chunks: List[Chunk]) -> int:
        """
        Add chunks to the vector store.

        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0

        texts = [chunk.content for chunk in chunks]
        embeddings = self._embed_texts(texts)

        # Get IDs (use current length as starting point)
        start_id = len(self._metadata)
        ids = np.array(range(start_id, start_id + len(chunks)), dtype=np.int64)

        # Add to index
        self.index.add_with_ids(embeddings, ids)

        for i, chunk in enumerate(chunks):
            mtime = 0.0
            if chunk.source:
                try:
                    mtime = os.path.getmtime(chunk.source)
                except OSError:
                    pass
            self._metadata.append(
                {
                    "id": start_id + i,
                    "content": chunk.content,
                    "source": chunk.source,
                    "language": chunk.language,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "mtime": mtime,
                }
            )

        self._save_index()
        return len(chunks)

    def remove_by_source(self, source: str) -> int:
        """Remove all chunks from a specific source file.
        
        Returns:
            Number of chunks removed
        """
        import faiss
        
        # Find indices to remove
        to_remove = []
        new_metadata = []
        id_mapping = {}
        new_id = 0
        
        for old_id, meta in enumerate(self._metadata):
            if meta.get("source") == source:
                to_remove.append(old_id)
            else:
                id_mapping[old_id] = new_id
                new_metadata.append(meta)
                new_id += 1
        
        if not to_remove:
            return 0
        
        # Rebuild index without removed items
        self._metadata = new_metadata
        if self._metadata:
            # Re-embed all remaining metadata
            texts = [m["content"] for m in self._metadata]
            embeddings = self._embed_texts(texts)
            ids = np.array(range(len(self._metadata)), dtype=np.int64)
            
            self._index = faiss.IndexIDMap(
                faiss.IndexFlatIP(self.embedding_dimension)
            )
            self._index.add_with_ids(embeddings, ids)
        else:
            self._index = faiss.IndexIDMap(
                faiss.IndexFlatIP(self.embedding_dimension)
            )
        
        self._save_index()
        return len(to_remove)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_language: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Tuple[dict, float]]:
        """
        Search for similar chunks with similarity threshold.

        Args:
            query: Query text to search for
            top_k: Number of results to return
            filter_language: Optional language filter
            min_score: Minimum similarity score (0.0 to 1.0)

        Returns:
            List of (metadata_dict, score) tuples
        """
        if self._metadata is None or len(self._metadata) == 0:
            return []

        # Embed query
        query_embedding = self._embed_texts([query])

        # Search
        search_k = min(top_k * 3, len(self._metadata))  # Oversearch to handle filtering
        scores, indices = self.index.search(query_embedding, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            
            # Apply similarity threshold
            if score < min_score:
                continue

            metadata = self._metadata[idx]

            # Apply language filter
            if filter_language and metadata.get("language") != filter_language:
                continue

            results.append((metadata, float(score)))

            if len(results) >= top_k:
                break

        return results

    def get_chunk(self, chunk_id: int) -> Optional[dict]:
        """Get a specific chunk by ID"""
        if 0 <= chunk_id < len(self._metadata):
            return self._metadata[chunk_id]
        return None

    def count(self) -> int:
        """Get number of chunks in the store"""
        # Ensure index is loaded (count is often queried without prior index access)
        if self._index is None:
            self._load_index()
        return len(self._metadata)

    def clear(self):
        """Clear the vector store"""
        import faiss

        self._index = faiss.IndexIDMap(faiss.IndexFlatIP(self.embedding_dimension))
        self._metadata = []
        self._embedding_cache.clear()
        if self.index_path.exists():
            self.index_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()

    def exists(self) -> bool:
        """Check if an index exists on disk"""
        return self.index_path.exists() and self.metadata_path.exists()
    
    def get_sources(self) -> set[str]:
        """Get all indexed source files."""
        return set(m.get("source", "") for m in self._metadata)

    def get_source_mtimes(self) -> dict[str, float]:
        """Get the latest mtime for each indexed source file."""
        mtimes: dict[str, float] = {}
        for m in self._metadata:
            src = m.get("source", "")
            if src:
                mtimes[src] = max(mtimes.get(src, 0.0), m.get("mtime", 0.0))
        return mtimes


# Global store cache to avoid reloading
_store_cache: dict[str, VectorStore] = {}


def get_vector_store(project_path: str = "") -> VectorStore:
    """Get or create a vector store for a project.
    
    Uses a global cache to avoid reloading the same store.
    """
    cache_key = project_path or "default"
    if cache_key not in _store_cache:
        _store_cache[cache_key] = VectorStore(project_path=project_path)
    return _store_cache[cache_key]


def clear_store_cache():
    """Clear the global store cache."""
    _store_cache.clear()
