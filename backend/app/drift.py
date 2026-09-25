"""Content drift detection over consecutive analyses of the same domain.

Compares the resource inventories of consecutive analyses (ordered by
``created_at``) and scores the drift per step:

- **resource-count drift** — absolute delta and percentage change
- **provider drift** — providers that appeared or disappeared

Severity scoring (low / medium / high):

- **high** — resource count moved >= 30% AND >= 10 resources in a single
  step, or two or more providers disappeared, or one provider disappeared
  while two or more appeared, or a provider disappeared alongside a count
  change >= 15% (dependency churn).
- **medium** — resource count moved >= 15%, or two or more providers
  appeared, or exactly one provider disappeared.
- **low** — anything else (including a stable step with no changes).

The drift summary is the highest severity across all steps, with an alert
text that names the dominant cause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}

RESOURCE_CHURN_HIGH_PCT = 30.0
RESOURCE_CHURN_HIGH_ABS = 10
RESOURCE_CHURN_MEDIUM_PCT = 15.0
PROVIDER_REMOVED_HIGH = 2


@dataclass
class DriftStep:
    from_analysis_id: int
    to_analysis_id: int
    from_created_at: str
    to_created_at: str
    resource_delta: int
    resource_delta_pct: Optional[float]
    providers_added: List[str]
    providers_removed: List[str]
    severity: str
    alert: str


@dataclass
class DriftSummary:
    analysis_count: int
    severity: str
    total_resource_delta: int
    providers_added: List[str]
    providers_removed: List[str]
    alert: str


@dataclass
class DriftResult:
    first_created_at: Optional[str]
    last_created_at: Optional[str]
    summary: DriftSummary
    steps: List[DriftStep] = field(default_factory=list)


def step_severity(
    delta: int,
    delta_pct: Optional[float],
    providers_added: int,
    providers_removed: int,
) -> str:
    """Classify a single drift step as low/medium/high."""
    abs_delta = abs(delta)
    abs_pct = abs(delta_pct) if delta_pct is not None else 0.0

    if providers_removed >= PROVIDER_REMOVED_HIGH:
        return "high"
    if providers_removed >= 1 and providers_added >= 2:
        return "high"
    if abs_pct >= RESOURCE_CHURN_HIGH_PCT and abs_delta >= RESOURCE_CHURN_HIGH_ABS:
        return "high"
    if providers_removed >= 1 and abs_pct >= RESOURCE_CHURN_MEDIUM_PCT:
        return "high"
    if providers_removed == 1:
        return "medium"
    if abs_pct >= RESOURCE_CHURN_MEDIUM_PCT or providers_added >= 2:
        return "medium"
    return "low"


def _alert_text(
    severity: str,
    delta: int,
    delta_pct: Optional[float],
    providers_added: List[str],
    providers_removed: List[str],
) -> str:
    if delta == 0 and not providers_added and not providers_removed:
        return "Stable: no drift detected between analyses."
    parts: List[str] = []
    if delta:
        sign = "+" if delta > 0 else ""
        parts.append(f"resource count {sign}{delta} ({_pct(delta_pct)})")
    if providers_added:
        parts.append(f"providers added: {', '.join(providers_added)}")
    if providers_removed:
        parts.append(f"providers removed: {', '.join(providers_removed)}")
    return f"{severity.capitalize()} drift: {'; '.join(parts)}."


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def providers_of(analysis: dict) -> set:
    """Set of provider names present in an analysis's resources."""
    providers = set()
    for resource in analysis.get("resources", []):
        provider = (resource.get("provider") if isinstance(resource, dict) else resource.provider) or None
        if provider:
            providers.add(provider)
    return providers


def analyze_drift(analyses: List[dict]) -> DriftResult:
    """Score the drift across consecutive analyses of one domain.

    ``analyses`` are plain dicts with ``id``, ``created_at`` (ISO string) and
    ``resources``. Consecutive pairs are compared in chronological order.
    """
    ordered = sorted(analyses, key=lambda a: (a["created_at"], a["id"]))
    steps: List[DriftStep] = []
    cumulative_added: set = set()
    cumulative_removed: set = set()

    for previous, current in zip(ordered, ordered[1:]):
        prev_providers = providers_of(previous)
        curr_providers = providers_of(current)
        added = sorted(curr_providers - prev_providers)
        removed = sorted(prev_providers - curr_providers)

        prev_count = len(previous.get("resources", []))
        curr_count = len(current.get("resources", []))
        delta = curr_count - prev_count
        delta_pct = round(100 * delta / prev_count, 1) if prev_count else None

        severity = step_severity(delta, delta_pct, len(added), len(removed))
        steps.append(
            DriftStep(
                from_analysis_id=previous["id"],
                to_analysis_id=current["id"],
                from_created_at=previous["created_at"],
                to_created_at=current["created_at"],
                resource_delta=delta,
                resource_delta_pct=delta_pct,
                providers_added=added,
                providers_removed=removed,
                severity=severity,
                alert=_alert_text(severity, delta, delta_pct, added, removed),
            )
        )
        cumulative_added.update(added)
        cumulative_removed.update(removed)

    if not ordered:
        summary = DriftSummary(
            analysis_count=0,
            severity="low",
            total_resource_delta=0,
            providers_added=[],
            providers_removed=[],
            alert="No analyses found for this domain.",
        )
        return DriftResult(first_created_at=None, last_created_at=None, summary=summary, steps=[])

    first_count = len(ordered[0].get("resources", []))
    last_count = len(ordered[-1].get("resources", []))
    total_delta = last_count - first_count

    if len(ordered) < 2:
        summary = DriftSummary(
            analysis_count=len(ordered),
            severity="low",
            total_resource_delta=0,
            providers_added=[],
            providers_removed=[],
            alert="Insufficient data: at least two analyses are required to measure drift.",
        )
    else:
        severity = max(
            (step.severity for step in steps),
            key=lambda s: SEVERITY_ORDER[s],
        )
        if total_delta == 0 and not cumulative_added and not cumulative_removed:
            alert = "No drift detected across the analysis window."
            severity = "low"
        else:
            causes: List[str] = []
            if total_delta:
                sign = "+" if total_delta > 0 else ""
                causes.append(f"resource count {sign}{total_delta}")
            if cumulative_added:
                causes.append(f"providers added: {', '.join(sorted(cumulative_added))}")
            if cumulative_removed:
                causes.append(f"providers removed: {', '.join(sorted(cumulative_removed))}")
            alert = f"{severity.capitalize()} drift: {'; '.join(causes)}."
        summary = DriftSummary(
            analysis_count=len(ordered),
            severity=severity,
            total_resource_delta=total_delta,
            providers_added=sorted(cumulative_added),
            providers_removed=sorted(cumulative_removed),
            alert=alert,
        )

    return DriftResult(
        first_created_at=ordered[0]["created_at"],
        last_created_at=ordered[-1]["created_at"],
        summary=summary,
        steps=steps,
    )
