"""Data loader for populating the Evidence Blackboard."""

from __future__ import annotations

from datetime import datetime

from src.evidence.blackboard import EvidenceBlackboard, EvidenceEntry, EvidenceType


class DataLoader:
    """Loads data from various sources into the Evidence Blackboard."""

    def __init__(self, blackboard: EvidenceBlackboard):
        self.blackboard = blackboard

    async def load_timeseries(
        self,
        site_code: str,
        target_date: str,
        lookback_days: int = 30,
    ) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.TIMESERIES_VOLUME,
            source="satis_oe_system",
            content_ref=f"timeseries:{site_code}:{target_date}:{lookback_days}d",
            quality_score=0.95,
        )
        self.blackboard.add(entry)

    async def load_city_dynamic(self, site_code: str, target_date: str) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.CITY_DYNAMIC_FORECAST,
            source="satis_oewm_system",
            content_ref=f"city_dynamic:{site_code}:{target_date}",
            quality_score=0.90,
        )
        self.blackboard.add(entry)

    async def load_customer_reports(self, site_code: str) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.CUSTOMER_REPORTED_VOLUME,
            source="kadm_system",
            content_ref=f"customer_report:{site_code}:{datetime.utcnow().strftime('%Y-%m-%d')}",
            quality_score=0.75,
        )
        self.blackboard.add(entry)

    async def load_weather_alerts(self, site_code: str) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.WEATHER_ALERT,
            source="weather_api",
            content_ref=f"weather:{site_code}:{datetime.utcnow().isoformat()}",
            quality_score=0.85,
        )
        self.blackboard.add(entry)

    async def load_vehicle_eta(self, site_code: str) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.VEHICLE_ETA_LIST,
            source="oe_transport_monitor",
            content_ref=f"vehicle_eta:{site_code}",
            quality_score=0.80,
        )
        self.blackboard.add(entry)

    async def load_diversion_records(self, site_code: str) -> None:
        entry = EvidenceEntry(
            type=EvidenceType.DIVERSION_RECORD,
            source="satis_oe_diversion",
            content_ref=f"diversion:{site_code}",
            quality_score=0.70,
        )
        self.blackboard.add(entry)
