"""
Graph Store for Graph-RAG
Manages code knowledge graph using NetworkX with JSON serialization.
Hybrid approach: Graph for relationships + Vector store for semantic search.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from .code_parser import CodeEntity, CodeRelation
from .config import get_vector_store_dir


class GraphStore:
    """
    Code knowledge graph using NetworkX.

    Uses NetworkX for graph structure (entities and relations).
    Vector search is delegated to the shared get_vector_store() singleton.
    """

    def __init__(self, project_path: str = "", vector_store=None):
        self.project_path = project_path
        self._graph = None
        self._graph_path = self._get_graph_path()
        self._entity_map: Dict[str, dict] = {}  # node_id -> entity data
        self._name_index: Dict[str, str] = {}   # entity name -> node_id
        self._source_index: Dict[str, list] = {} # source_file -> [node_id, ...]
        # reuse the global vector store singleton for this project
        if vector_store is not None:
            self.vector_store = vector_store
        else:
            from .vector_store import get_vector_store
            self.vector_store = get_vector_store(project_path)

    def _get_graph_path(self) -> Path:
        store_dir = get_vector_store_dir(self.project_path)
        return store_dir / "code_graph.json"

    @property
    def graph(self):
        if self._graph is None:
            self._load_graph()
        return self._graph
    
    def _load_graph(self):
        try:
            import networkx as nx
        except ImportError:
            raise ImportError(
                "networkx not installed. Install with: pip install networkx"
            )
        
        if self._graph_path.exists():
            with open(self._graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._graph = nx.node_link_graph(data, edges="links")
            self._rebuild_indexes()
        else:
            self._graph = nx.DiGraph()

    def _rebuild_indexes(self):
        """Rebuild name and source reverse indexes from entity_map."""
        self._entity_map.clear()
        self._name_index.clear()
        self._source_index.clear()
        for node, attrs in self._graph.nodes(data=True):
            self._entity_map[node] = dict(attrs)
            name = attrs.get("name", "")
            source = attrs.get("source_file", "")
            if name:
                self._name_index[name] = node
            if source:
                self._source_index.setdefault(source, []).append(node)

    def _save_graph(self):
        import networkx as nx
        
        self._graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph, edges="links")
        with open(self._graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_entities(self, entities: List[CodeEntity]):
        """Add code entities as graph nodes."""
        import networkx as nx

        for entity in entities:
            node_id = self._node_id(entity)
            self.graph.add_node(
                node_id,
                name=entity.name,
                entity_type=entity.entity_type,
                source_file=entity.source_file,
                line_start=entity.line_start,
                line_end=entity.line_end,
                content=entity.content,
                signature=entity.signature,
                parent=entity.parent,
                **entity.metadata,
            )
            attrs = {
                "name": entity.name,
                "entity_type": entity.entity_type,
                "source_file": entity.source_file,
                "content": entity.content,
            }
            self._entity_map[node_id] = attrs
            # update reverse indexes
            self._name_index[entity.name] = node_id
            self._source_index.setdefault(entity.source_file, []).append(node_id)
    
    def add_relations(self, relations: List[CodeRelation]):
        """Add relationships as graph edges."""
        import networkx as nx
        
        for relation in relations:
            source_id = self._resolve_node_id(relation.source)
            target_id = self._resolve_node_id(relation.target)
            
            if source_id and target_id and self.graph.has_node(source_id):
                self.graph.add_edge(
                    source_id,
                    target_id,
                    relation_type=relation.relation_type,
                    **relation.metadata,
                )
    
    def _node_id(self, entity: CodeEntity) -> str:
        """Generate unique node ID for an entity."""
        if entity.entity_type == "file":
            return f"file:{entity.source_file}"
        return f"{entity.entity_type}:{entity.name}@{entity.source_file}"
    
    def _resolve_node_id(self, name: str) -> Optional[str]:
        """Resolve a name to a node ID — O(1) via reverse index."""
        # direct name lookup
        if name in self._name_index:
            return self._name_index[name]

        # try file entity (basename or full path)
        file_id = f"file:{name}"
        if name in self._name_index and self._name_index[name].startswith("file:"):
            return self._name_index[name]
        for nid in (self._source_index.get(name, []) or []):
            if nid.startswith("file:"):
                return nid
        if self.graph.has_node(file_id):
            return file_id

        return None
    
    def get_neighbors(
        self,
        node_id: str,
        relation_types: Optional[List[str]] = None,
        hops: int = 1,
    ) -> List[Tuple[str, str, dict]]:
        """
        Get neighboring nodes within N hops.
        
        Returns:
            List of (neighbor_id, relation_type, edge_attrs)
        """
        import networkx as nx
        
        if not self.graph.has_node(node_id):
            return []
        
        results = []
        seen = {node_id}
        
        # BFS traversal
        current_level = {node_id}
        for _ in range(hops):
            next_level = set()
            for current in current_level:
                if current not in self.graph:
                    continue
                for neighbor in self.graph.successors(current):
                    if neighbor not in seen:
                        edge_data = self.graph.get_edge_data(current, neighbor)
                        if edge_data:
                            rel_type = edge_data.get("relation_type", "")
                            if relation_types is None or rel_type in relation_types:
                                results.append((neighbor, rel_type, dict(edge_data)))
                                seen.add(neighbor)
                                next_level.add(neighbor)
            current_level = next_level
        
        return results
    
    def get_entity_content(self, node_id: str) -> Optional[str]:
        """Get the content of an entity."""
        if not self.graph.has_node(node_id):
            return None
        return self.graph.nodes[node_id].get("content", "")
    
    def get_entity_signature(self, node_id: str) -> Optional[str]:
        """Get the signature of an entity."""
        if not self.graph.has_node(node_id):
            return None
        return self.graph.nodes[node_id].get("signature", "")
    
    def search_by_semantics(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[Tuple[str, float]]:
        """
        Semantic search using vector store.
        
        Returns:
            List of (node_id, score) tuples
        """
        if not self.vector_store.exists():
            return []
        
        results = self.vector_store.search(query, top_k=top_k, min_score=min_score)
        
        # Map chunk results to graph nodes
        mapped_results = []
        for metadata, score in results:
            source_file = metadata.get("source", "")
            node_id = f"file:{source_file}"
            if self.graph.has_node(node_id):
                mapped_results.append((node_id, score))
            elif source_file in self._source_index:
                # use reverse index instead of scanning entity_map
                mapped_results.append((self._source_index[source_file][0], score))

        return mapped_results
    
    def graph_rag_retrieve(
        self,
        query: str,
        top_k: int = 5,
        graph_hops: int = 2,
        min_score: float = 0.3,
    ) -> List[Tuple[str, float, str]]:
        """
        Graph-RAG retrieval: semantic seed + graph expansion.
        
        Strategy:
        1. Semantic search to find seed nodes
        2. Graph traversal from seeds to find related entities
        3. Combine and rank results
        
        Returns:
            List of (node_id, relevance_score, content)
        """
        import networkx as nx
        
        if not self.vector_store.exists() and self.graph.number_of_nodes() == 0:
            return []
        
        # Step 1: Semantic search for seeds
        seed_results = self.search_by_semantics(query, top_k=top_k, min_score=min_score)
        
        # Step 2: Graph expansion
        all_results: Dict[str, float] = {}
        
        for seed_id, seed_score in seed_results:
            # Add seed with its score
            all_results[seed_id] = max(all_results.get(seed_id, 0), seed_score)
            
            # Expand via graph traversal
            neighbors = self.get_neighbors(
                seed_id,
                relation_types=["contains", "calls", "inherits", "imports"],
                hops=graph_hops,
            )
            
            for neighbor_id, rel_type, _ in neighbors:
                # Score decays with hop distance and relation type
                base_score = seed_score
                if rel_type == "contains":
                    decay = 0.9
                elif rel_type == "calls":
                    decay = 0.8
                elif rel_type == "inherits":
                    decay = 0.7
                elif rel_type == "imports":
                    decay = 0.6
                else:
                    decay = 0.5
                
                neighbor_score = base_score * decay
                all_results[neighbor_id] = max(
                    all_results.get(neighbor_id, 0),
                    neighbor_score,
                )
        
        # Step 3: Build final results with content
        final_results = []
        for node_id, score in sorted(all_results.items(), key=lambda x: -x[1]):
            content = self.get_entity_content(node_id)
            if not content:
                # For entities without content, use signature + name
                signature = self.get_entity_signature(node_id)
                name = self.graph.nodes[node_id].get("name", node_id)
                content = signature or name
            
            final_results.append((node_id, score, content))
        
        # Limit results
        return final_results[:top_k * 2]
    
    def get_stats(self) -> dict:
        """Get graph statistics."""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "vector_chunks": self.vector_store.count() if self.vector_store.exists() else 0,
        }
    
    def clear(self):
        """Clear the graph."""
        import networkx as nx

        self._graph = nx.DiGraph()
        self._entity_map.clear()
        self._name_index.clear()
        self._source_index.clear()
        if self._graph_path.exists():
            self._graph_path.unlink()
    
    def exists(self) -> bool:
        """Check if graph exists on disk."""
        return self._graph_path.exists()


# Global graph store cache
_graph_store_cache: Dict[str, GraphStore] = {}


def get_graph_store(project_path: str = "") -> GraphStore:
    """Get or create a graph store for a project."""
    cache_key = project_path or "default"
    if cache_key not in _graph_store_cache:
        _graph_store_cache[cache_key] = GraphStore(project_path=project_path)
    return _graph_store_cache[cache_key]


def clear_graph_store_cache():
    """Clear the global graph store cache."""
    _graph_store_cache.clear()
