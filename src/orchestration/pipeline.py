"""Pipeline builder — Assemble the full 12-node prediction pipeline."""

from __future__ import annotations

from src.orchestration.graph import PredictionGraph
from src.orchestration.nodes.parse_intent import parse_intent_node
from src.orchestration.nodes.build_evidence import build_evidence_node
from src.orchestration.nodes.event_encode import event_encode_node
from src.orchestration.nodes.score_difficulty import score_difficulty_node
from src.orchestration.nodes.select_team import select_team_node
from src.orchestration.nodes.run_skills import run_skills_node
from src.orchestration.nodes.quality_gate import quality_gate_node
from src.orchestration.nodes.debate import debate_node
from src.orchestration.nodes.fuse import fuse_node
from src.orchestration.nodes.calibrate import calibrate_node
from src.orchestration.nodes.hitl_gate import hitl_gate_node
from src.orchestration.nodes.publish import publish_node


def build_prediction_pipeline() -> PredictionGraph:
    """Build and return the full 12-node prediction pipeline."""
    graph = PredictionGraph()

    # Step 1: Intent parsing (LLM ~300 tokens)
    graph.add_node("parse_intent", parse_intent_node, consumes_tokens=True)

    # Step 2: Build evidence blackboard (pure code)
    graph.add_node("build_evidence", build_evidence_node)

    # Step 3: Event encoding (LLM ~800 tokens, conditional)
    graph.add_node("event_encode", event_encode_node, consumes_tokens=True)

    # Step 4: DAAO difficulty scoring (pure code)
    graph.add_node("score_difficulty", score_difficulty_node)

    # Step 5: Dynamic team selection (pure code)
    graph.add_node("select_team", select_team_node)

    # Step 6: Parallel Skill execution (pure code)
    graph.add_node("run_skills", run_skills_node)

    # Step 7: Quality gate / disagreement detection (pure code)
    graph.add_node("quality_gate", quality_gate_node)

    # Step 8: Bounded debate (LLM ~1500 tokens, conditional)
    graph.add_node("debate", debate_node, consumes_tokens=True)

    # Step 9: Bayesian fusion (pure math)
    graph.add_node("fuse", fuse_node)

    # Step 10: Conformal calibration (pure stats)
    graph.add_node("calibrate", calibrate_node)

    # Step 11: HITL gate (pure threshold check)
    graph.add_node("hitl_gate", hitl_gate_node)

    # Step 12: Publish (pure code)
    graph.add_node("publish", publish_node)

    # ── Edges ──
    graph.add_edge("parse_intent", "build_evidence")
    graph.add_conditional_edges("build_evidence", {
        lambda s: s.get("has_unstructured_event", False): "event_encode",
        lambda s: not s.get("has_unstructured_event", False): "score_difficulty",
    })
    graph.add_edge("event_encode", "score_difficulty")
    graph.add_edge("score_difficulty", "select_team")
    graph.add_edge("select_team", "run_skills")
    graph.add_edge("run_skills", "quality_gate")
    graph.add_conditional_edges("quality_gate", {
        lambda s: s.get("disagreement", {}).get("requires_debate", False): "debate",
        lambda s: not s.get("disagreement", {}).get("requires_debate", False): "fuse",
    })
    graph.add_edge("debate", "fuse")
    graph.add_edge("fuse", "calibrate")
    graph.add_edge("calibrate", "hitl_gate")
    graph.add_conditional_edges("hitl_gate", {
        lambda s: s.get("hitl", {}).get("required", False): "publish",
        lambda s: not s.get("hitl", {}).get("required", False): "publish",
    })

    graph.set_entry_point("parse_intent")

    return graph
