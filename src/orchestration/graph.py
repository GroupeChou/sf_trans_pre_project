"""LangGraph StateGraph — 12-node prediction pipeline.

This is the core orchestration engine that wires together:
  parse_intent → build_evidence → [event_encode] → score_difficulty →
  select_team → run_skills → quality_gate → [debate] → fuse →
  calibrate → hitl_gate → [human_review] → publish
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from src.orchestration.state import ForecastState


@dataclass
class PipelineNode:
    """A node in the prediction pipeline."""
    name: str
    handler: Callable[[ForecastState], dict[str, Any]]
    consumes_tokens: bool = False
    conditional: bool = False
    condition_fn: Callable[[ForecastState], bool] | None = None


class PredictionGraph:
    """Manages the prediction pipeline as a directed graph of nodes.

    In production, this wraps LangGraph's StateGraph. For the MVP, we implement
    the graph semantics directly to avoid heavy dependencies while maintaining
    the same interface and execution model.
    """

    def __init__(self):
        self._nodes: dict[str, PipelineNode] = {}
        self._edges: dict[str, list[str]] = {}
        self._conditional_edges: dict[str, dict[str, Callable]] = {}
        self._entry_point: str | None = None

    def add_node(self, name: str, handler: Callable, **kwargs: Any) -> None:
        self._nodes[name] = PipelineNode(
            name=name,
            handler=handler,
            consumes_tokens=kwargs.get("consumes_tokens", False),
            conditional=kwargs.get("conditional", False),
            condition_fn=kwargs.get("condition_fn"),
        )
        self._edges[name] = []

    def add_edge(self, from_node: str, to_node: str) -> None:
        if from_node not in self._edges:
            self._edges[from_node] = []
        self._edges[from_node].append(to_node)

    def add_conditional_edges(
        self,
        from_node: str,
        condition_map: dict[Callable, str],
    ) -> None:
        self._conditional_edges[from_node] = {}
        for fn, target in condition_map.items():
            key = target if isinstance(target, str) else str(target)
            self._conditional_edges[from_node][key] = fn

    def set_entry_point(self, name: str) -> None:
        self._entry_point = name

    async def invoke(self, initial_state: ForecastState) -> ForecastState:
        """Execute the pipeline by walking nodes in topological order."""
        state = dict(initial_state)
        state["execution_path"] = state.get("execution_path", [])
        state["token_used"] = state.get("token_used", 0)

        current = self._entry_point
        visited = set()

        while current is not None and current not in visited:
            visited.add(current)
            node = self._nodes.get(current)
            if node is None:
                break

            state["execution_path"].append(current)

            try:
                handler = node.handler
                if inspect.iscoroutinefunction(handler):
                    result = await handler(state)
                else:
                    result = handler(state)
                if result:
                    state.update(result)
            except Exception as exc:
                state["error"] = str(exc)
                # On error, route to publish to ensure graceful degradation
                if "publish" in self._nodes:
                    current = "publish"
                    continue
                break

            current = self._get_next_node(current, state)

        return ForecastState(**{k: state.get(k) for k in ForecastState.__required_keys__ if k in state})  # type: ignore

    def _get_next_node(self, current: str, state: dict) -> str | None:
        if current in self._conditional_edges:
            for target, condition_fn in self._conditional_edges[current].items():
                try:
                    if condition_fn(state):
                        return target
                except Exception:
                    continue
            return None

        edges = self._edges.get(current, [])
        return edges[0] if edges else None

    def visualize(self) -> str:
        """Return Mermaid flowchart of the pipeline."""
        lines = ["flowchart TD"]
        for node_name in self._nodes:
            node = self._nodes[node_name]
            marker = "🔴" if node.consumes_tokens else "🟢"
            lines.append(f"    {node_name}[{marker} {node_name}]")

        for src, targets in self._edges.items():
            for tgt in targets:
                lines.append(f"    {src} --> {tgt}")

        for src, conds in self._conditional_edges.items():
            for tgt in conds:
                lines.append(f"    {src} -.-> {tgt}")

        return "\n".join(lines)
