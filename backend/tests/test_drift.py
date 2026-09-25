"""Unit tests for content drift detection (severity scoring + alerts)."""

from app.drift import analyze_drift, step_severity


def analysis(
    analysis_id: int,
    created_at: str,
    resources: int,
    providers: list[str] | None = None,
) -> dict:
    provider_names = providers if providers is not None else ["Google Tag Manager"]
    return {
        "id": analysis_id,
        "created_at": created_at,
        "resources": [
            {"resource_type": "script", "url": f"https://cdn.example.com/{i}.js", "provider": p}
            for i, p in enumerate(provider_names)
        ]
        + [
            {"resource_type": "script", "url": f"https://cdn.example.com/extra-{j}.js", "provider": None}
            for j in range(max(0, resources - len(provider_names)))
        ],
    }


def test_severity_thresholds():
    # small change -> low
    assert step_severity(2, 5.0, 0, 0) == "low"
    # >= 15% -> medium
    assert step_severity(4, 20.0, 0, 0) == "medium"
    # >= 30% and >= 10 -> high
    assert step_severity(12, 40.0, 0, 0) == "high"
    # percentage alone without absolute volume stays medium
    assert step_severity(3, 50.0, 0, 0) == "medium"
    # one provider disappeared -> medium
    assert step_severity(0, 0.0, 0, 1) == "medium"
    # two providers disappeared -> high
    assert step_severity(0, 0.0, 0, 2) == "high"
    # churn: one removed + two added -> high
    assert step_severity(0, 0.0, 2, 1) == "high"
    # two added, nothing removed -> medium
    assert step_severity(0, 0.0, 2, 0) == "medium"


def test_stable_window_reports_no_drift():
    result = analyze_drift(
        [
            analysis(1, "2026-09-20T10:00:00", 3, ["Google Tag Manager"]),
            analysis(2, "2026-09-21T10:00:00", 3, ["Google Tag Manager"]),
        ]
    )
    assert result.summary.severity == "low"
    assert "No drift detected" in result.summary.alert
    assert len(result.steps) == 1
    assert result.steps[0].resource_delta == 0


def test_provider_removal_scores_high_with_alert():
    result = analyze_drift(
        [
            analysis(1, "2026-09-20T10:00:00", 5, ["Google Analytics", "Hotjar"]),
            analysis(2, "2026-09-21T10:00:00", 4, ["Google Analytics"]),
        ]
    )
    assert result.summary.severity == "high"
    assert result.summary.providers_removed == ["Hotjar"]
    assert "providers removed: Hotjar" in result.summary.alert
    step = result.steps[0]
    assert step.severity == "high"
    assert step.resource_delta == -1
    assert step.resource_delta_pct == -20.0


def test_summary_is_worst_step_across_window():
    result = analyze_drift(
        [
            analysis(1, "2026-09-20T10:00:00", 2, ["Plausible"]),
            analysis(2, "2026-09-21T10:00:00", 2, ["Plausible"]),
            analysis(3, "2026-09-22T10:00:00", 20, ["Plausible", "Sentry", "Criteo"]),
        ]
    )
    # step 2->3 adds 18 resources (+900%) and two providers
    assert result.summary.severity == "high"
    assert result.summary.total_resource_delta == 18
    assert result.summary.providers_added == ["Criteo", "Sentry"]
    assert len(result.steps) == 2


def test_single_analysis_is_insufficient():
    result = analyze_drift([analysis(1, "2026-09-20T10:00:00", 3)])
    assert result.summary.analysis_count == 1
    assert result.summary.severity == "low"
    assert "at least two analyses" in result.summary.alert
    assert result.steps == []


def test_empty_window():
    result = analyze_drift([])
    assert result.summary.analysis_count == 0
    assert "No analyses found" in result.summary.alert
