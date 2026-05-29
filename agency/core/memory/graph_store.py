from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import networkx as nx


@dataclass
class GraphStore:
    """
    Minimal prerequisite graph store.

    Nodes: skills/topics (strings)
    Edge A -> B means: A is a prerequisite for B
    """

    graph: nx.DiGraph

    @classmethod
    def empty(cls) -> "GraphStore":
        return cls(graph=nx.DiGraph())

    def add_prereq(self, prereq: str, skill: str) -> None:
        self.graph.add_edge(prereq, skill)

    def prerequisites_for(self, skill: str) -> List[str]:
        if skill not in self.graph:
            return []
        return list(self.graph.predecessors(skill))

    def descendants(self, skill: str, depth: Optional[int] = None) -> List[str]:
        if skill not in self.graph:
            return []
        if depth is None:
            return list(nx.descendants(self.graph, skill))
        # bounded BFS
        out: List[str] = []
        frontier = [(skill, 0)]
        seen = {skill}
        while frontier:
            node, d = frontier.pop(0)
            if d >= depth:
                continue
            for nxt in self.graph.successors(node):
                if nxt in seen:
                    continue
                seen.add(nxt)
                out.append(nxt)
                frontier.append((nxt, d + 1))
        return out

