from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import heapq

@dataclass
class Graph:
    """
    Representa un grafo no dirigido con pesos en las aristas.
    """
    adj: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)

    @staticmethod
    def from_topology(config: dict) -> "Graph":
        """
        Construye un grafo a partir de un diccionario de configuración.
        """
        g = Graph()
        cfg = config.get("config", {}) if "config" in config else config
        seen_edges = set()

        # Aseguramos que todos los nodos existan
        for node in cfg.keys():
            g.adj.setdefault(node, [])

        # Construimos las aristas sin duplicarlas
        for u, neighs in cfg.items():
            for v in neighs:
                g.adj.setdefault(v, [])
                edge = tuple(sorted((u, v)))
                if edge in seen_edges:
                    continue
                seen_edges.add(edge)
                g.add_edge(u, v, 1.0)
                g.add_edge(v, u, 1.0)

        return g

    def add_edge(self, u: str, v: str, w: float = 1.0) -> None:
        """
        Agrega una arista dirigida de u a v con peso w.
        """
        self.adj.setdefault(u, []).append((v, w))

    def neighbors(self, u: str) -> List[Tuple[str, float]]:
        """
        Devuelve los vecinos del nodo u y sus pesos.
        """
        return self.adj.get(u, [])

def dijkstra(graph: Graph, source: str) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
    """
    Algoritmo de Dijkstra para calcular las distancias mínimas desde un nodo origen.
    """
    dist: Dict[str, float] = {node: float('inf') for node in graph.adj}
    prev: Dict[str, Optional[str]] = {node: None for node in graph.adj}

    if source not in dist:
        raise ValueError(f"El nodo fuente '{source}' no existe en el grafo")

    dist[source] = 0.0
    pq: List[Tuple[float, str]] = [(0.0, source)]
    visited = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        for v, w in graph.neighbors(u):
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    return dist, prev

def build_next_hop(prev: Dict[str, Optional[str]], source: str) -> Dict[str, str]:
    """
    Construye una tabla de siguiente salto desde el nodo fuente.
    """
    next_hop: Dict[str, str] = {}

    for dest in prev.keys():
        if dest == source or prev[dest] is None:
            continue

        cur = dest
        while prev[cur] is not None and prev[cur] != source:
            cur = prev[cur]

        if prev[cur] == source:
            next_hop[dest] = cur

    return next_hop
