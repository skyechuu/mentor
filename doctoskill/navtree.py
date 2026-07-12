from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NavNode:
    title: str
    url: Optional[str]
    children: list["NavNode"] = field(default_factory=list)


def iter_nodes(node: NavNode):
    for child in node.children:
        yield child
        yield from iter_nodes(child)
