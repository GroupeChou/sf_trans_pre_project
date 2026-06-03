"""API Gateway — MCP/A2A protocol compliant gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GatewayConfig:
    enable_mcp: bool = True
    enable_a2a: bool = True
    enable_rest: bool = True


class PlatformGateway:
    """Unified API Gateway supporting MCP, A2A, and REST protocols."""

    def __init__(self, config: GatewayConfig | None = None):
        self.config = config or GatewayConfig()

    async def tools_list(self, tenant_id: str) -> list[dict[str, Any]]:
        """MCP: List available tools for a tenant."""
        return [
            {
                "name": "predict_arrival_volume",
                "description": "Predict arrival volume for a transit site",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "site_code": {"type": "string"},
                        "target_date": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["site_code", "text"],
                },
            },
            {
                "name": "list_skills",
                "description": "List available prediction Skills",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                    },
                },
            },
        ]

    def get_agent_card(self) -> dict[str, Any]:
        """A2A: Return the platform's Agent Card."""
        return {
            "name": "转运场地在线预测智能体平台",
            "description": "Multi-tenant SaaS prediction agent platform for logistics transit sites",
            "version": "0.1.0",
            "capabilities": {
                "forecasting": True,
                "streaming": False,
                "push_notifications": False,
                "state_transition_history": True,
            },
            "skills": [
                {
                    "id": "predict_arrival_volume",
                    "name": "Predict Arrival Volume",
                    "description": "Predict daily arrival volume for a transit site using multi-skill agent team",
                }
            ],
        }
