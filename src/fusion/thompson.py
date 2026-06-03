"""Thompson Sampling — Dynamic Skill weight learning via Bayesian bandits."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SkillPosterior:
    """Bayesian posterior for a Skill's performance in a given bucket."""

    mu: float = 0.0
    sigma: float = 0.5
    n: int = 0


@dataclass
class ThompsonSampler:
    """Thompson Sampling-based Skill selection for the Dynamic Team Router."""

    decay_factor: float = 0.92
    min_sigma: float = 0.05
    cold_start_samples: int = 30
    _posteriors: dict[str, dict[str, SkillPosterior]] = field(default_factory=dict)

    def select_skills(
        self,
        bucket: str,
        candidate_skills: list[str],
        n_select: int,
    ) -> list[tuple[str, float]]:
        """Select top-N skills using Thompson Sampling.

        Returns list of (skill_id, sampled_score).
        """
        scores = []
        for skill_id in candidate_skills:
            posterior = self._get_posterior(skill_id, bucket)
            if posterior.n < self.cold_start_samples:
                sample = np.random.uniform(0.3, 0.7)
            else:
                sample = np.random.normal(posterior.mu, posterior.sigma)
            scores.append((skill_id, sample))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n_select]

    def update(
        self,
        skill_id: str,
        bucket: str,
        reward: float,
    ) -> None:
        """Update posterior after observing actual outcome at T+1."""
        posterior = self._get_posterior(skill_id, bucket)

        posterior.mu = self.decay_factor * posterior.mu + (1 - self.decay_factor) * reward
        posterior.sigma = max(self.min_sigma, posterior.sigma * 0.98)
        posterior.n += 1

    def _get_posterior(self, skill_id: str, bucket: str) -> SkillPosterior:
        if skill_id not in self._posteriors:
            self._posteriors[skill_id] = {}
        if bucket not in self._posteriors[skill_id]:
            self._posteriors[skill_id][bucket] = SkillPosterior()
        return self._posteriors[skill_id][bucket]

    def get_posterior(self, skill_id: str, bucket: str) -> SkillPosterior:
        return self._get_posterior(skill_id, bucket)

    def get_all_posteriors(self) -> dict[str, dict[str, SkillPosterior]]:
        return dict(self._posteriors)

    def get_best_skill(self, bucket: str, candidate_skills: list[str]) -> str:
        selected = self.select_skills(bucket, candidate_skills, n_select=1)
        return selected[0][0] if selected else candidate_skills[0]

    def reset(self) -> None:
        self._posteriors.clear()
