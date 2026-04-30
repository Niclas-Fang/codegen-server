"""
RAG Configuration for Code Completion Enhancement
"""

import os
import hashlib
from pathlib import Path

# Base directory for RAG data
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Vector store configuration - supports per-project isolation
VECTOR_STORE_BASE_DIR = BASE_DIR / "rag_data" / "vector_stores"
VECTOR_STORE_BASE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_INDEX_NAME = "default"


def get_vector_store_dir(project_path: str = "") -> Path:
    """Get vector store directory for a specific project.
    
    Args:
        project_path: Absolute path to project directory. Empty string uses default.
        
    Returns:
        Path to the vector store directory for this project
    """
    if not project_path:
        return VECTOR_STORE_BASE_DIR / DEFAULT_INDEX_NAME
    
    # Use hash of project path to create unique directory
    # This handles paths with special characters and long paths
    path_hash = hashlib.md5(project_path.encode()).hexdigest()[:12]
    dir_name = f"{Path(project_path).name}_{path_hash}"
    store_dir = VECTOR_STORE_BASE_DIR / dir_name
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


def get_index_paths(project_path: str = "") -> tuple[Path, Path]:
    """Get index and metadata paths for a project.
    
    Returns:
        (index_path, metadata_path)
    """
    store_dir = get_vector_store_dir(project_path)
    return (store_dir / "code_index.faiss", store_dir / "metadata.json")


# Embedding configuration
EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_DIMENSION = 384  # for all-MiniLM-L6-v2

# Retrieval configuration
DEFAULT_TOP_K = 5
MAX_CONTEXT_CHUNKS = 3  # Number of chunks to include in context
SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score for RAG results

# Chunking configuration
CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 50  # characters

# Code file extensions to index
CODE_EXTENSIONS = [
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
]

# Directories to exclude from indexing
EXCLUDE_DIRS = [
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".egg-info",
    ".tox",
    ".mypy_cache",
    ".pixi",
    ".pytest_cache",
    ".ruff_cache",
    "rag_data",
]

# Whether RAG is enabled globally
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"

# Embedding cache configuration
EMBEDDING_CACHE_SIZE = int(os.getenv("RAG_EMBEDDING_CACHE_SIZE", "1000"))

# Language Server configuration
LSP_COMMAND = os.getenv("LSP_COMMAND", "clangd")
LSP_ARGS = os.getenv("LSP_ARGS", "").split() if os.getenv("LSP_ARGS") else []
LSP_FALLBACK_COMMANDS = os.getenv(
    "LSP_FALLBACK_COMMANDS", "clangd,ccls"
).split(",")

# Graph-RAG configuration
GRAPH_RAG_ENABLED = os.getenv("GRAPH_RAG_ENABLED", "true").lower() == "true"
GRAPH_HOPS = int(os.getenv("GRAPH_HOPS", "2"))
GRAPH_RELATION_DECAY = {
    "contains": 0.9,
    "calls": 0.8,
    "inherits": 0.7,
    "imports": 0.6,
}
