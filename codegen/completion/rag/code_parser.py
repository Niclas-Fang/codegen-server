"""
Code Parser for Graph-RAG
Uses Language Server Protocol (LSP) for precise AST extraction.
Falls back to regex-based parsing when LSP is unavailable.
Optimized for C/C++ with clangd.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, variable)."""
    name: str
    entity_type: str
    source_file: str
    line_start: int = 0
    line_end: int = 0
    content: str = ""
    signature: str = ""
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelation:
    """Represents a relationship between two code entities."""
    source: str
    target: str
    relation_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    entities: List[CodeEntity]
    relations: List[CodeRelation]
    errors: List[str] = field(default_factory=list)


def parse_file_with_lsp(
    file_path: Path,
    lsp_client: Optional[Any] = None,
) -> ParseResult:
    """
    Parse a code file using LSP (preferred) or regex fallback.
    
    Args:
        file_path: Path to the code file
        lsp_client: Optional LSP client instance
    
    Returns:
        ParseResult with entities and relations
    """
    # Try LSP first if available
    if lsp_client is not None and getattr(lsp_client, '_initialized', False):
        try:
            return _parse_with_lsp(file_path, lsp_client)
        except Exception:
            pass
    
    # Fallback to regex-based parsing
    return _parse_with_regex(file_path)


def _parse_with_lsp(file_path: Path, lsp_client: Any) -> ParseResult:
    """Parse file using Language Server Protocol."""
    entities = []
    relations = []
    errors = []
    
    # Open document in LSP
    lsp_client.open_document(str(file_path))
    
    try:
        # Get all symbols in the document
        symbols = lsp_client.get_document_symbols(str(file_path))
        
        # Convert LSP symbols to our entity format
        _convert_symbols(symbols, str(file_path), entities, relations)
        
        # Extract call relationships by analyzing function bodies
        _extract_call_relations_lsp(symbols, str(file_path), lsp_client, entities, relations)
        
    except Exception as e:
        errors.append(f"LSP parse error for {file_path}: {e}")
    finally:
        lsp_client.close_document(str(file_path))
    
    return ParseResult(entities=entities, relations=relations, errors=errors)


def _convert_symbols(
    symbols: List[Any],
    file_path: str,
    entities: List[CodeEntity],
    relations: List[CodeRelation],
    parent_name: Optional[str] = None,
):
    """Recursively convert LSP symbols to our entity format."""
    file_name = Path(file_path).name
    
    for symbol in symbols:
        entity_type = _map_lsp_kind_to_entity(symbol.kind)
        
        # Read symbol content from file
        content = _extract_symbol_content(file_path, symbol)
        
        entity = CodeEntity(
            name=symbol.name,
            entity_type=entity_type,
            source_file=file_path,
            line_start=symbol.range_start.get("line", 0) + 1,
            line_end=symbol.range_end.get("line", 0) + 1,
            content=content,
            signature=symbol.detail or f"{symbol.kind} {symbol.name}",
            parent=parent_name,
        )
        entities.append(entity)
        
        # Create contains relation
        container = parent_name if parent_name else file_name
        relations.append(CodeRelation(
            source=container,
            target=symbol.name,
            relation_type="contains",
        ))
        
        # Handle inheritance for classes
        if entity_type == "class" and symbol.detail:
            # Parse inheritance from detail like "class Foo : public Bar"
            _parse_inheritance(symbol.detail, symbol.name, relations)
        
        # Recursively process children
        if symbol.children:
            _convert_symbols(
                symbol.children,
                file_path,
                entities,
                relations,
                parent_name=symbol.name,
            )


def _extract_call_relations_lsp(
    symbols: List[Any],
    file_path: str,
    lsp_client: Any,
    entities: List[CodeEntity],
    relations: List[CodeRelation],
):
    """Extract function call relationships using LSP references."""
    for symbol in symbols:
        if symbol.kind in ("function", "method"):
            # Get references to this function
            refs = lsp_client.get_references(
                file_path,
                symbol.selection_start.get("line", 0),
                symbol.selection_start.get("character", 0),
            )
            
            for ref in refs:
                # Find which function contains this reference
                caller = _find_containing_function(
                    ref.uri.replace("file://", ""),
                    ref.start_line,
                    entities,
                )
                if caller and caller != symbol.name:
                    relations.append(CodeRelation(
                        source=caller,
                        target=symbol.name,
                        relation_type="calls",
                    ))
        
        # Recurse into children
        if symbol.children:
            _extract_call_relations_lsp(
                symbol.children, file_path, lsp_client, entities, relations
            )


def _find_containing_function(
    file_path: str,
    line: int,
    entities: List[CodeEntity],
) -> Optional[str]:
    """Find the function that contains a given line."""
    candidates = [
        e for e in entities
        if e.source_file == file_path
        and e.entity_type in ("function", "method")
        and e.line_start <= line + 1 <= e.line_end
    ]
    
    if candidates:
        # Return the most specific (smallest range) function
        candidates.sort(key=lambda e: e.line_end - e.line_start)
        return candidates[0].name
    
    return None


def _map_lsp_kind_to_entity(lsp_kind: str) -> str:
    """Map LSP symbol kind to our entity type."""
    kind_map = {
        "file": "file",
        "module": "module",
        "namespace": "namespace",
        "package": "package",
        "class": "class",
        "method": "method",
        "property": "property",
        "field": "field",
        "constructor": "constructor",
        "enum": "enum",
        "interface": "interface",
        "function": "function",
        "variable": "variable",
        "constant": "constant",
        "string": "string",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "key": "key",
        "null": "null",
        "enum_member": "enum_member",
        "struct": "class",
        "event": "event",
        "operator": "operator",
        "type_parameter": "type_parameter",
    }
    return kind_map.get(lsp_kind, "unknown")


def _extract_symbol_content(file_path: str, symbol: Any) -> str:
    """Extract the source code content of a symbol."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        start_line = symbol.range_start.get("line", 0)
        end_line = symbol.range_end.get("line", 0)
        
        # Extract lines (0-indexed)
        content_lines = lines[start_line:end_line + 1]
        return "".join(content_lines)
    except Exception:
        return ""


def _parse_inheritance(detail: str, class_name: str, relations: List[CodeRelation]):
    """Parse inheritance relationships from class detail string."""
    # Pattern: "class Foo : public Bar, private Baz"
    if ":" in detail:
        inheritance_part = detail.split(":", 1)[1]
        for base in inheritance_part.split(","):
            base = base.strip()
            # Remove access specifiers
            for access in ("public ", "private ", "protected ", "virtual "):
                base = base.replace(access, "")
            base = base.strip()
            if base and base != class_name:
                relations.append(CodeRelation(
                    source=class_name,
                    target=base,
                    relation_type="inherits",
                ))


def _parse_with_regex(file_path: Path) -> ParseResult:
    """Fallback regex-based C/C++ parser."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return ParseResult(entities=[], relations=[], errors=[str(e)])
    
    entities = []
    relations = []
    
    # File entity
    entities.append(CodeEntity(
        name=file_path.name,
        entity_type="file",
        source_file=str(file_path),
        content=content,
    ))
    
    # Functions
    func_pattern = re.compile(
        r'(?:^|\n)\s*(?:\w+\s+)+?(\w+)\s*\(([^)]*)\)\s*(?:const\s+)?(?:noexcept\s+)?\{',
        re.MULTILINE
    )
    for match in func_pattern.finditer(content):
        name = match.group(1)
        if name in ("if", "while", "for", "switch", "catch", "return"):
            continue
        line_num = content[:match.start()].count("\n") + 1
        
        entities.append(CodeEntity(
            name=name,
            entity_type="function",
            source_file=str(file_path),
            line_start=line_num,
            signature=match.group(0).strip()[:100],
        ))
        relations.append(CodeRelation(
            source=file_path.name,
            target=name,
            relation_type="contains",
        ))
    
    # Classes and structs
    class_pattern = re.compile(
        r'(?:^|\n)\s*(?:class|struct)\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?',
        re.MULTILINE
    )
    for match in class_pattern.finditer(content):
        name = match.group(1)
        parent = match.group(2)
        line_num = content[:match.start()].count("\n") + 1
        
        entities.append(CodeEntity(
            name=name,
            entity_type="class",
            source_file=str(file_path),
            line_start=line_num,
            signature=match.group(0).strip(),
        ))
        relations.append(CodeRelation(
            source=file_path.name,
            target=name,
            relation_type="contains",
        ))
        
        if parent:
            relations.append(CodeRelation(
                source=name,
                target=parent,
                relation_type="inherits",
            ))
    
    # Includes
    include_pattern = re.compile(r'#include\s+[<"]([^>"]+)[>"]')
    for match in include_pattern.finditer(content):
        relations.append(CodeRelation(
            source=file_path.name,
            target=match.group(1),
            relation_type="imports",
        ))
    
    # Namespaces
    namespace_pattern = re.compile(
        r'(?:^|\n)\s*namespace\s+(\w+)\s*\{',
        re.MULTILINE
    )
    for match in namespace_pattern.finditer(content):
        name = match.group(1)
        line_num = content[:match.start()].count("\n") + 1
        
        entities.append(CodeEntity(
            name=name,
            entity_type="namespace",
            source_file=str(file_path),
            line_start=line_num,
            signature=f"namespace {name}",
        ))
        relations.append(CodeRelation(
            source=file_path.name,
            target=name,
            relation_type="contains",
        ))
    
    return ParseResult(entities=entities, relations=relations)


def parse_project(
    directory: Path,
    lsp_client: Optional[Any] = None,
    extensions: Tuple[str, ...] = (".cpp", ".c", ".h", ".hpp", ".cc", ".cxx"),
) -> Tuple[List[CodeEntity], List[CodeRelation]]:
    """
    Parse all code files in a directory.
    
    Args:
        directory: Root directory to scan
        lsp_client: Optional LSP client for precise parsing
        extensions: File extensions to parse (default: C/C++ extensions)
    
    Returns:
        Combined entities and relations from all files
    """
    all_entities = []
    all_relations = []
    
    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            result = parse_file_with_lsp(file_path, lsp_client)
            all_entities.extend(result.entities)
            all_relations.extend(result.relations)
    
    return all_entities, all_relations
