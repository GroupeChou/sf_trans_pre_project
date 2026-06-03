"""Method card sharing — Community knowledge sharing for prediction methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MethodCard:
    card_id: str
    title: str
    author: str
    site_code: str
    share_scope: str  # "team", "region", "all"

    skill_combo: list[str]
    params: dict[str, Any] = field(default_factory=dict)
    author_notes: str = ""

    usage_count: int = 0
    avg_mape: float = 0.0
    thumbs_up: int = 0
    thumbs_down: int = 0
    comments: list[dict] = field(default_factory=list)

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_certified: bool = False

    def to_display(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "title": self.title,
            "author": self.author,
            "site_code": self.site_code,
            "share_scope": self.share_scope,
            "skill_combo": self.skill_combo,
            "author_notes": self.author_notes,
            "usage_count": self.usage_count,
            "avg_mape": f"{self.avg_mape:.1%}",
            "rating": f"👍 {self.thumbs_up} 👎 {self.thumbs_down}",
            "is_certified": self.is_certified,
        }


class CommunityHub:
    """Community knowledge sharing for prediction methods."""

    def __init__(self):
        self._cards: dict[str, MethodCard] = {}

    def share(self, card: MethodCard) -> None:
        self._cards[card.card_id] = card

    def get(self, card_id: str) -> MethodCard | None:
        return self._cards.get(card_id)

    def search(
        self,
        site_code: str | None = None,
        keyword: str | None = None,
        scope: str | None = None,
    ) -> list[MethodCard]:
        results = []
        for card in self._cards.values():
            if site_code and card.site_code != site_code:
                continue
            if scope and card.share_scope != scope:
                continue
            if keyword and keyword.lower() not in card.title.lower():
                continue
            results.append(card)
        return results

    def rank_by_mape(self, limit: int = 10) -> list[MethodCard]:
        sorted_cards = sorted(
            self._cards.values(),
            key=lambda c: c.avg_mape,
        )
        return sorted_cards[:limit]

    def rate(self, card_id: str, is_up: bool) -> None:
        card = self._cards.get(card_id)
        if not card:
            return
        if is_up:
            card.thumbs_up += 1
        else:
            card.thumbs_down += 1

    def comment(self, card_id: str, author: str, text: str) -> None:
        card = self._cards.get(card_id)
        if not card:
            return
        card.comments.append({
            "author": author,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def certify(self, card_id: str) -> None:
        card = self._cards.get(card_id)
        if card:
            card.is_certified = True

    def list_all(self) -> list[MethodCard]:
        return list(self._cards.values())
