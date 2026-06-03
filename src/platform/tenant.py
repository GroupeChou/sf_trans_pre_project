"""Multi-tenant isolation for the SaaS platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    quota_per_minute: int = 100
    allowed_skills: list[str] = field(default_factory=list)
    allowed_sites: list[str] = field(default_factory=list)
    features: dict[str, bool] = field(default_factory=dict)
    is_active: bool = True


class TenantManager:
    """Manages multi-tenant isolation and configuration."""

    def __init__(self):
        self._tenants: dict[str, TenantConfig] = {}

    def register(self, config: TenantConfig) -> None:
        self._tenants[config.tenant_id] = config

    def get(self, tenant_id: str) -> TenantConfig | None:
        return self._tenants.get(tenant_id)

    def is_active(self, tenant_id: str) -> bool:
        tenant = self.get(tenant_id)
        return tenant is not None and tenant.is_active

    def can_access_skill(self, tenant_id: str, skill_id: str) -> bool:
        tenant = self.get(tenant_id)
        if not tenant:
            return False
        if not tenant.allowed_skills:
            return True
        return skill_id in tenant.allowed_skills

    def can_access_site(self, tenant_id: str, site_code: str) -> bool:
        tenant = self.get(tenant_id)
        if not tenant:
            return False
        if not tenant.allowed_sites:
            return True
        return site_code in tenant.allowed_sites

    def list_tenants(self) -> list[TenantConfig]:
        return list(self._tenants.values())

    def deactivate(self, tenant_id: str) -> None:
        if tenant_id in self._tenants:
            self._tenants[tenant_id].is_active = False
