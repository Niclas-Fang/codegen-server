"""
Code Parser for Graph-RAG
Extracts AST nodes and relationships from source code.
Supports Python (ast), with regex fallback for other languages.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, variable)."""
    name: str
    entity_type: str  # 'function', 'class', 'method', 'variable', 'import'
    source_file: str
    line_start: int = 0
    line_end: int = 0
    content: str = ""
    signature: str = ""
    parent: Optional[str] = None  # Parent class/function name
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeRelation:
    """Represents a relationship between two code entities."""
    source: str  # Source entity name
    target: str  # Target entity name
    relation_type: str  # 'calls', 'imports', 'inherits', 'contains', 'references'
    metadata: Dict[str, Any] = field(default_factory=dict)


class PythonCodeParser:
    """Parse Python code using the ast module."""
    
    def __init__(self, file_path: Path, content: str):
        self.file_path = str(file_path)
        self.content = content
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []
        self._line_offsets = self._compute_line_offsets()
    
    def _compute_line_offsets(self) -> List[int]:
        offsets = [0]
        for i, char in enumerate(self.content):
            if char == "\n":
                offsets.append(i + 1)
        return offsets
    
    def _get_line_number(self, pos: int) -> int:
        for i, offset in enumerate(self._line_offsets):
            if pos < offset:
                return i
        return len(self._line_offsets)
    
    def _get_source_segment(self, node: ast.AST) -> str:
        try:
            start = self._line_offsets[node.lineno - 1] + node.col_offset
            end = self._line_offsets[node.end_lineno - 1] + node.end_col_offset
            return self.content[start:end]
        except (AttributeError, IndexError):
            return ""
    
    def parse(self) -> tuple[List[CodeEntity], List[CodeRelation]]:
        try:
            tree = ast.parse(self.content)
        except SyntaxError:
            return self._fallback_parse()
        
        self._visit_module(tree)
        return self.entities, self.relations
    
    def _visit_module(self, node: ast.Module):
        # Add file entity
        file_entity = CodeEntity(
            name=Path(self.file_path).name,
            entity_type="file",
            source_file=self.file_path,
            line_start=1,
            line_end=len(self.content.splitlines()),
            content=self.content,
        )
        self.entities.append(file_entity)
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child)
            elif isinstance(child, ast.ClassDef):
                self._visit_class(child)
            elif isinstance(child, ast.Import):
                self._visit_import(child)
            elif isinstance(child, ast.ImportFrom):
                self._visit_import_from(child)
        
        # Second pass: find call relationships
        self._extract_calls(node)
    
    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, parent: Optional[str] = None):
        name = node.name
        content = self._get_source_segment(node)
        
        # Build signature
        args_str = self._format_args(node.args)
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"
        signature = f"def {name}({args_str}){returns}:"
        
        entity = CodeEntity(
            name=name,
            entity_type="method" if parent else "function",
            source_file=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno,
            content=content,
            signature=signature,
            parent=parent,
        )
        self.entities.append(entity)
        
        # File contains function
        self.relations.append(CodeRelation(
            source=Path(self.file_path).name,
            target=name,
            relation_type="contains",
        ))
        
        # Visit nested functions and classes
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child, parent=name)
            elif isinstance(child, ast.ClassDef):
                self._visit_class(child, parent=name)
    
    def _visit_class(self, node: ast.ClassDef, parent: Optional[str] = None):
        name = node.name
        content = self._get_source_segment(node)
        
        # Build inheritance signature
        bases = [ast.unparse(base) for base in node.bases]
        bases_str = f"({', '.join(bases)})" if bases else ""
        signature = f"class {name}{bases_str}:"
        
        entity = CodeEntity(
            name=name,
            entity_type="class",
            source_file=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno,
            content=content,
            signature=signature,
            parent=parent,
        )
        self.entities.append(entity)
        
        # File contains class
        container = parent if parent else Path(self.file_path).name
        self.relations.append(CodeRelation(
            source=container,
            target=name,
            relation_type="contains",
        ))
        
        # Inheritance relationships
        for base in node.bases:
            base_name = ast.unparse(base)
            self.relations.append(CodeRelation(
                source=name,
                target=base_name,
                relation_type="inherits",
            ))
        
        # Visit methods
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._visit_function(child, parent=name)
            elif isinstance(child, ast.ClassDef):
                self._visit_class(child, parent=name)
    
    def _visit_import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            entity = CodeEntity(
                name=name,
                entity_type="import",
                source_file=self.file_path,
                line_start=node.lineno,
                line_end=node.end_lineno,
                signature=f"import {alias.name}",
            )
            self.entities.append(entity)
            
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="imports",
            ))
    
    def _visit_import_from(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            entity = CodeEntity(
                name=name,
                entity_type="import",
                source_file=self.file_path,
                line_start=node.lineno,
                line_end=node.end_lineno,
                signature=f"from {module} import {alias.name}",
            )
            self.entities.append(entity)
            
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=full_name,
                relation_type="imports",
            ))
    
    def _extract_calls(self, tree: ast.AST):
        """Extract function call relationships."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    call_name = func.id
                    # Find the containing function/class
                    container = self._find_container(node)
                    if container:
                        self.relations.append(CodeRelation(
                            source=container,
                            target=call_name,
                            relation_type="calls",
                        ))
                elif isinstance(func, ast.Attribute):
                    # method call like obj.method()
                    call_name = ast.unparse(func)
                    container = self._find_container(node)
                    if container:
                        self.relations.append(CodeRelation(
                            source=container,
                            target=call_name,
                            relation_type="calls",
                        ))
    
    def _find_container(self, node: ast.AST) -> Optional[str]:
        """Find the containing function or class name."""
        # This is a simplified version - in practice we'd track parent nodes
        return None
    
    def _format_args(self, args: ast.arguments) -> str:
        """Format function arguments."""
        parts = []
        
        # Positional args
        all_args = args.posonlyargs + args.args
        defaults_start = len(all_args) - len(args.defaults)
        
        for i, arg in enumerate(all_args):
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            if i >= defaults_start:
                default = args.defaults[i - defaults_start]
                arg_str += f"={ast.unparse(default)}"
            parts.append(arg_str)
        
        # *args
        if args.vararg:
            parts.append(f"*{args.vararg.arg}")
        
        # **kwargs
        if args.kwarg:
            parts.append(f"**{args.kwarg.arg}")
        
        return ", ".join(parts)
    
    def _fallback_parse(self) -> tuple[List[CodeEntity], List[CodeRelation]]:
        """Fallback regex-based parser for files with syntax errors."""
        return RegexCodeParser(self.file_path, self.content).parse()


class RegexCodeParser:
    """Regex-based parser for non-Python languages or fallback."""
    
    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []
    
    def parse(self) -> tuple[List[CodeEntity], List[CodeRelation]]:
        ext = Path(self.file_path).suffix.lower()
        
        # Add file entity
        self.entities.append(CodeEntity(
            name=Path(self.file_path).name,
            entity_type="file",
            source_file=self.file_path,
            content=self.content,
        ))
        
        if ext == ".py":
            self._parse_python_regex()
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            self._parse_javascript()
        elif ext in (".java", ".cs"):
            self._parse_java_like()
        elif ext in (".cpp", ".c", ".h", ".hpp"):
            self._parse_cpp()
        elif ext == ".go":
            self._parse_go()
        elif ext == ".rs":
            self._parse_rust()
        else:
            # Generic: just chunk the file
            pass
        
        return self.entities, self.relations
    
    def _parse_python_regex(self):
        # Function definitions
        func_pattern = re.compile(r'^(async\s+)?def\s+(\w+)\s*\(([^)]*)\)', re.MULTILINE)
        for match in func_pattern.finditer(self.content):
            name = match.group(2)
            signature = match.group(0)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
                signature=signature,
            ))
            
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Class definitions
        class_pattern = re.compile(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?:', re.MULTILINE)
        for match in class_pattern.finditer(self.content):
            name = match.group(1)
            bases = match.group(2) or ""
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="class",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0),
            ))
            
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
            
            # Inheritance
            if bases:
                for base in [b.strip() for b in bases.split(",")]:
                    self.relations.append(CodeRelation(
                        source=name,
                        target=base,
                        relation_type="inherits",
                    ))
        
        # Imports
        import_pattern = re.compile(r'^(?:from\s+(\S+)\s+)?import\s+(.+)$', re.MULTILINE)
        for match in import_pattern.finditer(self.content):
            module = match.group(1) or ""
            imports = match.group(2)
            line_num = self.content[:match.start()].count("\n") + 1
            
            for imp in [i.strip().split()[0] for i in imports.split(",")]:
                full_name = f"{module}.{imp}" if module else imp
                self.relations.append(CodeRelation(
                    source=Path(self.file_path).name,
                    target=full_name,
                    relation_type="imports",
                ))
    
    def _parse_javascript(self):
        # Functions
        func_pattern = re.compile(
            r'(?:^|\n)\s*(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
            re.MULTILINE
        )
        for match in func_pattern.finditer(self.content):
            name = match.group(1)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0).strip(),
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Arrow functions with const
        arrow_pattern = re.compile(
            r'(?:^|\n)\s*const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>',
            re.MULTILINE
        )
        for match in arrow_pattern.finditer(self.content):
            name = match.group(1)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0).strip(),
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Classes
        class_pattern = re.compile(r'(?:^|\n)\s*class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{', re.MULTILINE)
        for match in class_pattern.finditer(self.content):
            name = match.group(1)
            parent = match.group(2)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="class",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0).strip(),
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
            
            if parent:
                self.relations.append(CodeRelation(
                    source=name,
                    target=parent,
                    relation_type="inherits",
                ))
        
        # Imports
        import_pattern = re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
        for match in import_pattern.finditer(self.content):
            module = match.group(1)
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=module,
                relation_type="imports",
            ))
    
    def _parse_java_like(self):
        # Methods
        method_pattern = re.compile(
            r'(?:^|\n)\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?(?:\w+\s+)+(\w+)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        for match in method_pattern.finditer(self.content):
            name = match.group(1)
            if name in ("if", "while", "for", "switch", "catch"):
                continue
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="method",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Classes
        class_pattern = re.compile(r'(?:^|\n)\s*(?:public\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', re.MULTILINE)
        for match in class_pattern.finditer(self.content):
            name = match.group(1)
            parent = match.group(2)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="class",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
            
            if parent:
                self.relations.append(CodeRelation(
                    source=name,
                    target=parent,
                    relation_type="inherits",
                ))
    
    def _parse_cpp(self):
        # Functions
        func_pattern = re.compile(
            r'(?:^|\n)\s*(?:\w+\s+)+?(\w+)\s*\(([^)]*)\)\s*(?:const\s+)?(?:noexcept\s+)?\{',
            re.MULTILINE
        )
        for match in func_pattern.finditer(self.content):
            name = match.group(1)
            if name in ("if", "while", "for", "switch", "catch"):
                continue
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Includes
        include_pattern = re.compile(r'#include\s+[<"]([^>"]+)[>"]')
        for match in include_pattern.finditer(self.content):
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=match.group(1),
                relation_type="imports",
            ))
    
    def _parse_go(self):
        # Functions
        func_pattern = re.compile(r'(?:^|\n)func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(', re.MULTILINE)
        for match in func_pattern.finditer(self.content):
            name = match.group(1)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
    
    def _parse_rust(self):
        # Functions
        func_pattern = re.compile(r'(?:^|\n)\s*fn\s+(\w+)\s*(?:<[^>]+>)?\s*\(', re.MULTILINE)
        for match in func_pattern.finditer(self.content):
            name = match.group(1)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Structs
        struct_pattern = re.compile(r'(?:^|\n)\s*struct\s+(\w+)', re.MULTILINE)
        for match in struct_pattern.finditer(self.content):
            name = match.group(1)
            line_num = self.content[:match.start()].count("\n") + 1
            
            self.entities.append(CodeEntity(
                name=name,
                entity_type="class",
                source_file=self.file_path,
                line_start=line_num,
            ))
            self.relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))


def parse_file(file_path: Path) -> tuple[List[CodeEntity], List[CodeRelation]]:
    """Parse a code file and extract entities and relations."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return [], []
    
    ext = file_path.suffix.lower()
    
    if ext == ".py":
        parser = PythonCodeParser(file_path, content)
    else:
        parser = RegexCodeParser(str(file_path), content)
    
    return parser.parse()
