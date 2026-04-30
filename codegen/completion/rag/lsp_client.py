"""
LSP Client for Graph-RAG
Communicates with C/C++ Language Server (clangd) via JSON-RPC over stdin/stdout.
Provides precise AST information for code knowledge graph construction.
"""

import json
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LSPSymbol:
    """Represents a symbol extracted via LSP."""
    name: str
    kind: str
    uri: str
    range_start: Dict[str, int]
    range_end: Dict[str, int]
    selection_start: Dict[str, int]
    selection_end: Dict[str, int]
    detail: str = ""
    children: List["LSPSymbol"] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class LSPReference:
    """Represents a reference to a symbol."""
    uri: str
    start_line: int
    start_char: int
    end_line: int
    end_char: int


class LSPClient:
    """
    Generic LSP client for communicating with Language Servers.
    Primarily designed for C/C++ via clangd, but works with any LSP server.
    """
    
    LSP_KIND_MAP = {
        1: "file",
        2: "module",
        3: "namespace",
        4: "package",
        5: "class",
        6: "method",
        7: "property",
        8: "field",
        9: "constructor",
        10: "enum",
        11: "interface",
        12: "function",
        13: "variable",
        14: "constant",
        15: "string",
        16: "number",
        17: "boolean",
        18: "array",
        19: "object",
        20: "key",
        21: "null",
        22: "enum_member",
        23: "struct",
        24: "event",
        25: "operator",
        26: "type_parameter",
    }
    
    def __init__(
        self,
        command: str = "clangd",
        args: Optional[List[str]] = None,
        workspace_path: str = "",
    ):
        self.command = command
        self.args = args or []
        self.workspace_path = workspace_path
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._initialized = False
        self._shutdown = False
    
    @staticmethod
    def is_command_available(command: str) -> bool:
        """Check if a command is available in PATH."""
        return shutil.which(command) is not None

    def start(self) -> bool:
        """Start the Language Server process."""
        try:
            # Add compile_commands.json hint if workspace is set
            if self.workspace_path and "--compile-commands-dir" not in self.args:
                self.args.extend(["--compile-commands-dir", str(self.workspace_path)])
            
            self.process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            # Send initialize request
            return self._initialize()
            
        except FileNotFoundError:
            raise RuntimeError(
                f"Language Server not found: {self.command}\n"
                "Please install clangd or specify the correct path."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start Language Server: {e}")
    
    def stop(self):
        """Shutdown the Language Server gracefully."""
        if self.process and self.process.poll() is None:
            try:
                self._send_request("shutdown", {})
                self._send_notification("exit", {})
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            finally:
                self._shutdown = True
                for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
                    if pipe:
                        try:
                            pipe.close()
                        except Exception:
                            pass
    
    def _initialize(self) -> bool:
        """Send initialize request to Language Server."""
        workspace_uri = Path(self.workspace_path).resolve().as_uri() if self.workspace_path else ""
        
        result = self._send_request("initialize", {
            "processId": os.getpid(),
            "rootUri": workspace_uri,
            "capabilities": {
                "textDocument": {
                    "documentSymbol": {
                        "hierarchicalDocumentSymbolSupport": True,
                    },
                    "references": {
                        "dynamicRegistration": False,
                    },
                    "definition": {
                        "dynamicRegistration": False,
                        "linkSupport": True,
                    },
                },
                "workspace": {
                    "symbol": {
                        "dynamicRegistration": False,
                    },
                },
            },
            "workspaceFolders": [
                {"uri": workspace_uri, "name": Path(self.workspace_path).name}
            ] if workspace_uri else [],
        })
        
        if result is not None:
            self._initialized = True
            self._send_notification("initialized", {})
            return True
        return False
    
    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id
    
    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or self.process.poll() is not None:
            return None
        
        req_id = self._next_id()
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        
        self._write_message(message)
        return self._read_response(req_id)
    
    def _send_notification(self, method: str, params: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or self.process.poll() is not None:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self._write_message(message)
    
    def _write_message(self, message: Dict[str, Any]):
        """Write a JSON-RPC message to the server stdin."""
        content = json.dumps(message)
        header = f"Content-Length: {len(content.encode('utf-8'))}\r\n\r\n"
        
        try:
            self.process.stdin.write(header + content)
            self.process.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("Language Server process has terminated")
    
    def _read_response(self, expected_id: int) -> Optional[Any]:
        """Read and parse a JSON-RPC response."""
        while True:
            # Read header
            header = self._read_line()
            if not header:
                return None
            
            # Parse Content-Length
            content_length = 0
            while header.strip():
                if header.lower().startswith("content-length:"):
                    content_length = int(header.split(":")[1].strip())
                header = self._read_line()
            
            if content_length == 0:
                continue
            
            # Read content
            content = self.process.stdout.read(content_length)
            try:
                message = json.loads(content)
            except json.JSONDecodeError:
                continue
            
            # Check if it's a response to our request
            if "id" in message and message["id"] == expected_id:
                if "error" in message:
                    raise RuntimeError(f"LSP error: {message['error']}")
                return message.get("result")
            
            # Skip notifications and other responses
            if "id" not in message:
                continue
    
    def _read_line(self) -> str:
        """Read a line from server stdout."""
        line = self.process.stdout.readline()
        return line if line else ""
    
    def open_document(self, file_path: str, content: str = "", language_id: str = "cpp"):
        """Notify server that a document is open."""
        uri = Path(file_path).resolve().as_uri()
        
        if not content:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except:
                content = ""
        
        self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })
    
    def close_document(self, file_path: str):
        """Notify server that a document is closed."""
        uri = Path(file_path).resolve().as_uri()
        self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })
    
    def get_document_symbols(self, file_path: str) -> List[LSPSymbol]:
        """
        Get all symbols in a document.
        
        Returns hierarchical symbols (functions, classes, namespaces, etc.)
        """
        uri = Path(file_path).resolve().as_uri()
        
        result = self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        
        if not result:
            return []
        
        return self._parse_symbols(result, uri)
    
    def get_references(
        self,
        file_path: str,
        line: int,
        character: int,
        include_declaration: bool = True,
    ) -> List[LSPReference]:
        """Find all references to a symbol."""
        uri = Path(file_path).resolve().as_uri()
        
        result = self._send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration},
        })
        
        if not result:
            return []
        
        references = []
        for ref in result:
            refs_range = ref.get("range", {})
            start = refs_range.get("start", {})
            end = refs_range.get("end", {})
            references.append(LSPReference(
                uri=ref.get("uri", ""),
                start_line=start.get("line", 0),
                start_char=start.get("character", 0),
                end_line=end.get("line", 0),
                end_char=end.get("character", 0),
            ))
        
        return references
    
    def get_definition(
        self,
        file_path: str,
        line: int,
        character: int,
    ) -> Optional[Dict[str, Any]]:
        """Get the definition location of a symbol."""
        uri = Path(file_path).resolve().as_uri()
        
        result = self._send_request("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })
        
        if result and len(result) > 0:
            return result[0]
        return None
    
    def get_workspace_symbols(self, query: str = "") -> List[LSPSymbol]:
        """Search symbols across the entire workspace."""
        result = self._send_request("workspace/symbol", {
            "query": query,
        })
        
        if not result:
            return []
        
        symbols = []
        for item in result:
            loc = item.get("location", {})
            uri = loc.get("uri", "")
            rng = loc.get("range", {})
            start = rng.get("start", {})
            end = rng.get("end", {})
            
            symbols.append(LSPSymbol(
                name=item.get("name", ""),
                kind=self.LSP_KIND_MAP.get(item.get("kind", 0), "unknown"),
                uri=uri,
                range_start=start,
                range_end=end,
                selection_start=start,
                selection_end=end,
                detail=item.get("containerName", ""),
            ))
        
        return symbols
    
    def _parse_symbols(
        self,
        items: List[Dict[str, Any]],
        uri: str,
        parent_detail: str = "",
    ) -> List[LSPSymbol]:
        """Recursively parse LSP symbol information."""
        symbols = []
        
        for item in items:
            name = item.get("name", "")
            kind_num = item.get("kind", 0)
            kind = self.LSP_KIND_MAP.get(kind_num, "unknown")
            detail = item.get("detail", "") or parent_detail
            
            # Handle both DocumentSymbol and SymbolInformation formats
            if "range" in item:
                rng = item.get("range", {})
                sel_rng = item.get("selectionRange", rng)
                children = item.get("children", [])
            else:
                loc = item.get("location", {})
                rng = loc.get("range", {})
                sel_rng = rng
                children = []
                uri = loc.get("uri", uri)
            
            start = rng.get("start", {})
            end = rng.get("end", {})
            sel_start = sel_rng.get("start", {})
            sel_end = sel_rng.get("end", {})
            
            symbol = LSPSymbol(
                name=name,
                kind=kind,
                uri=uri,
                range_start=start,
                range_end=end,
                selection_start=sel_start,
                selection_end=sel_end,
                detail=detail,
            )
            
            # Recursively parse children
            if children:
                symbol.children = self._parse_symbols(children, uri, detail)
            
            symbols.append(symbol)
        
        return symbols
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class FallbackCodeParser:
    """
    Fallback parser when LSP is unavailable.
    Uses regex-based parsing for C/C++.
    """
    
    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
    
    def parse(self) -> Tuple[List[Any], List[Any]]:
        """Simple regex-based C/C++ parsing."""
        import re
        from .code_parser import CodeEntity, CodeRelation
        
        entities = []
        relations = []
        
        # Add file entity
        entities.append(CodeEntity(
            name=Path(self.file_path).name,
            entity_type="file",
            source_file=self.file_path,
            content=self.content,
        ))
        
        # Function definitions
        func_pattern = re.compile(
            r'(?:^|\n)\s*(?:\w+\s+)+?(\w+)\s*\(([^)]*)\)\s*(?:const\s+)?(?:noexcept\s+)?\{',
            re.MULTILINE
        )
        for match in func_pattern.finditer(self.content):
            name = match.group(1)
            if name in ("if", "while", "for", "switch", "catch", "return"):
                continue
            line_num = self.content[:match.start()].count("\n") + 1
            
            entities.append(CodeEntity(
                name=name,
                entity_type="function",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0).strip()[:100],
            ))
            relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=name,
                relation_type="contains",
            ))
        
        # Classes/structs
        class_pattern = re.compile(
            r'(?:^|\n)\s*(?:class|struct)\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+(\w+))?',
            re.MULTILINE
        )
        for match in class_pattern.finditer(self.content):
            name = match.group(1)
            parent = match.group(2)
            line_num = self.content[:match.start()].count("\n") + 1
            
            entities.append(CodeEntity(
                name=name,
                entity_type="class",
                source_file=self.file_path,
                line_start=line_num,
                signature=match.group(0).strip(),
            ))
            relations.append(CodeRelation(
                source=Path(self.file_path).name,
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
        for match in include_pattern.finditer(self.content):
            relations.append(CodeRelation(
                source=Path(self.file_path).name,
                target=match.group(1),
                relation_type="imports",
            ))
        
        return entities, relations
