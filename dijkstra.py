
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
        # formato: {"A": ["B","C"], "B":["A"], ...}
        for u, neighs in cfg.items():
            for v in neighs:
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
    next_hop: Dict[str, str] = {}
    for t in prev.keys():
        if t == source:
            continue
        path = []
        cur = t
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path = list(reversed(path))
        if path and path[0] == source and len(path) > 1:
            next_hop[t] = path[1]
    return next_hop
