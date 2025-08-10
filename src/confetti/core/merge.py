from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from .source import RegisteredSource
from .filters import Filter, should_include_key
from .types import ProvenanceRecord


def merge_sources(
    registered_sources: List[RegisteredSource],
) -> Tuple[Dict[str, Any], Dict[str, ProvenanceRecord]]:
    effective: Dict[str, Any] = {}
    provenance: Dict[str, ProvenanceRecord] = {}

    for rs in registered_sources:
        payload = rs.source.load(filter=rs.filter, depth=rs.depth)
        for key, value in payload.items():
            if not should_include_key(key, rs.filter):
                continue
            # last source wins
            effective[key] = value
            provenance[key] = ProvenanceRecord(
                key=key,
                source_id=rs.source.id,
                source_key=key,
                timestamp_loaded=datetime.utcnow(),
            )

    return effective, provenance
