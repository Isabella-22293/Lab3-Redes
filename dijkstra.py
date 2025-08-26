from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import heapq

@dataclass
class Graph:
    # node -> list[(neighbor, weight)]
    adj: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)

    @staticmethod
    def from_topology(config: dict) -> "Graph":
        g = Graph()
        cfg = config.get("config", {})
        # Asegurar que todos los nodos existan en adj
        for node in cfg.keys():
            g.adj.setdefault(node, [])
        # Evitar duplicados de aristas
        seen_edges = set()
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
        self.adj.setdefault(u, []).append((v, w))

    def neighbors(self, u: str) -> List[Tuple[str, float]]:
        return self.adj.get(u, [])

def dijkstra(graph: Graph, source: str) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
    dist: Dict[str, float] = {node: float('inf') for node in graph.adj.keys()}
    prev: Dict[str, Optional[str]] = {node: None for node in graph.adj.keys()}
    if source not in dist:
        dist[source] = 0.0
        prev[source] = None
    else:
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
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev

def build_next_hop(prev: Dict[str, Optional[str]], source: str) -> Dict[str, str]:
    next_hop: Dict[str, str] = {}
    for dest in prev.keys():
        if dest == source:
            continue
        if prev.get(dest) is None:
            continue
        cur = dest
        while prev.get(cur) is not None and prev[cur] != source:
            cur = prev[cur]
        if prev.get(cur) == source:
            next_hop[dest] = cur
    return next_hop
