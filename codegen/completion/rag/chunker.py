"""
Document and Chunk structures for RAG
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class Document:
    """Represents a source document"""

    content: str
    source: str  # file path or source identifier
    doc_type: str = "code"  # code, docs, comments
    language: Optional[str] = None  # programming language if code
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.language is None:
            self.language = self._detect_language(self.source)

    @staticmethod
    def _detect_language(source: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = Path(source).suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
        }
        return language_map.get(ext)


@dataclass
class Chunk:
    """Represents a chunk of a document"""

    content: str
    document: Document
    chunk_index: int
    start_char: int
    end_char: int

    @property
    def source(self) -> str:
        return self.document.source

    @property
    def language(self) -> Optional[str]:
        return self.document.language

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "language": self.language,
        }


"""
Code chunker for RAG - splits code files into manageable chunks
"""

import re
from pathlib import Path
from typing import List, Iterator, Optional
from .chunker import Document, Chunk
from .config import CHUNK_SIZE, CHUNK_OVERLAP, CODE_EXTENSIONS, EXCLUDE_DIRS


class CodeChunker:
    """
    Splits code files into overlapping chunks for embedding and retrieval.

    Uses a simple character-based chunking with overlap to ensure context
    is preserved across chunks. For code, we also try to respect structural
    boundaries (functions, classes) when possible.
    """

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_file(self, file_path: Path) -> List[Chunk]:
        """Chunk a single code file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        doc = Document(
            content=content,
            source=str(file_path),
            doc_type="code",
        )
        return self.chunk_document(doc)

    def chunk_document(self, document: Document) -> List[Chunk]:
        """Split a document into chunks with overlap"""
        content = document.content
        chunks = []

        # Try to split by function/class boundaries first
        code_chunks = self._split_by_structure(content, document.language)

        if len(code_chunks) <= 1:
            # No structure found or single chunk, use simple character chunking
            code_chunks = self._chunk_by_size(content)

        # Create Chunk objects with proper indexing
        for i, (start, end, chunk_content) in enumerate(code_chunks):
            if chunk_content.strip():  # Skip empty chunks
                chunks.append(
                    Chunk(
                        content=chunk_content.strip(),
                        document=document,
                        chunk_index=i,
                        start_char=start,
                        end_char=end,
                    )
                )

        return chunks

    def _split_by_structure(self, content: str, language: Optional[str]) -> List[tuple]:
        """Try to split code by structural elements (functions, classes)"""
        if not language:
            return []

        # Language-specific patterns for functions/classes
        patterns = {
            "python": [
                r"(?:^|\n)(def \w+\s*\([^)]*\)\s*(?:->\s*\w+)?\s*:)",
                r"(?:^|\n)(class \w+\s*(?:\([^)]*\))?\s*:)",
                r"(?:^|\n)(async def \w+\s*\([^)]*\))",
            ],
            "javascript": [
                r"(?:^|\n)(function\s+\w+\s*\([^)]*\)\s*\{)",
                r"(?:^|\n)(const\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{)",
                r"(?:^|\n)(class\s+\w+\s*(?:extends\s+\w+)?\s*\{)",
                r"(?:^|\n)(export\s+(?:default\s+)?(?:function|class|const)\s+\w+)",
            ],
            "typescript": [
                r"(?:^|\n)(function\s+\w+\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{)",
                r"(?:^|\n)(const\s+\w+\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{)",
                r"(?:^|\n)(class\s+\w+\s*(?:extends\s+\w+)?\s*\{)",
                r"(?:^|\n)(export\s+(?:default\s+)?(?:function|class|const|interface)\s+\w+)",
            ],
            "java": [
                r"(?:^|\n)(public|private|protected)?\s*(?:static\s+)?\s*(?:final\s+)?\s*(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*(?:throws\s+\S+\s*)?\{",
                r"(?:^|\n)(class\s+\w+\s*(?:extends\s+\w+)?\s*(?:implements\s+[\w,\s]+)?\s*\{)",
            ],
            "cpp": [
                r"(?:^|\n)((?:\w+\s+)+?\w+\s+\w+\s*\([^)]*\)\s*(?:const)?\s*(?:noexcept)?\s*\{)",
                r"(?:^|\n)(class\s+\w+\s*(?:public|private|protected)?\s*(?::\s*public\s+\w+)?\s*\{)",
                r"(?:^|\n)(template\s*<[^>]+>\s*(?:(?:inline|static|const)?\s*)*(?:\w+\s+)+?\w+\s*\()",
            ],
            "go": [
                r"(?:^|\n)(func\s+(?:\([^)]+\)\s+)?\w+\s*\([^)]*\)\s*(?:\w+\s+)?\{)",
                r"(?:^|\n)(type\s+\w+\s+(?:struct|interface)\s*\{)",
            ],
            "rust": [
                r"(?:^|\n)(fn\s+\w+\s*(?:<[^>]+>)?\s*\([^)]*\)\s*(?:->\s*[\w&]+)?\s*\{)",
                r"(?:^|\n)(impl(?:\s+<[^>]+>)?\s+(?:\w+\s+)?for\s+\w+\s*\{)",
                r"(?:^|\n)(struct\s+\w+\s*(?:<[^>]+>)?\s*(?:where\s+[^;]+)?\s*\{)",
                r"(?:^|\n)(enum\s+\w+\s*(?:<[^>]+>)?\s*\{)",
            ],
        }

        lang_patterns = patterns.get(language, [])
        if not lang_patterns:
            return []

        # Find all structural boundaries
        boundaries = [0]  # Start with beginning of file
        for pattern in lang_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                boundaries.append(match.start())

        if len(boundaries) <= 1:
            return []

        boundaries.sort()
        boundaries.append(len(content))

        # Create chunks based on boundaries
        chunks = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]

            # If chunk is too large, it will be further split by _chunk_by_size
            # when we process it
            if end - start > self.chunk_size * 2:
                chunks.append((start, end, content[start:end]))
            else:
                chunks.append((start, end, content[start:end]))

        return chunks if len(chunks) > 1 else []

    def _chunk_by_size(self, content: str) -> List[tuple]:
        """Split content by size with overlap"""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + self.chunk_size
            chunk_content = content[start:end]

            # Try to break at a line boundary to avoid splitting in middle of line
            if end < len(content):
                last_newline = chunk_content.rfind("\n")
                if last_newline > self.chunk_size // 2:
                    chunk_content = chunk_content[:last_newline]
                    end = start + last_newline + 1

            chunks.append((start, end, chunk_content))

            # Move forward with overlap
            start = end - self.chunk_overlap
            chunk_index += 1

            # Avoid infinite loop for very small advances
            if start >= len(content):
                break

        return chunks

    def chunk_directory(
        self,
        directory: Path,
        extensions: List[str] = CODE_EXTENSIONS,
        exclude_dirs: List[str] = EXCLUDE_DIRS,
    ) -> Iterator[Chunk]:
        """Chunk all code files in a directory"""
        for item in directory.rglob("*"):
            if item.is_file():
                # Check if file should be indexed
                if item.suffix.lower() in extensions:
                    # Check if any parent is excluded
                    if not any(parent.name in exclude_dirs for parent in item.parents):
                        yield from self.chunk_file(item)


def load_code_files(directory: Path) -> List[Document]:
    """Load all code files from a directory as Documents"""
    documents = []
    chunker = CodeChunker()

    for chunk in chunker.chunk_directory(directory):
        # Group chunks by document
        documents.append(chunk.document)

    # Return unique documents
    seen = set()
    unique_docs = []
    for doc in documents:
        if doc.source not in seen:
            seen.add(doc.source)
            unique_docs.append(doc)

    return unique_docs
