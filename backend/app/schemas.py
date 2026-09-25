from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resource_type: Optional[str] = None
    url: Optional[str] = None
    host: Optional[str] = None
    integrity: Optional[str] = None
    crossorigin: Optional[str] = None
    async_attr: bool = False
    defer_attr: bool = False
    provider: Optional[str] = None
    category: Optional[str] = None


class ContentAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    status: str
    analysis_type: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    page_title: Optional[str] = None
    resources: List[ResourceRead] = []


class ContentAnalysisListItem(BaseModel):
    """Summary row for the analysis history (GET /api/analyses)."""

    id: int
    target: str
    status: str
    analysis_type: str
    created_at: datetime
    page_title: Optional[str] = None
    resource_count: int
    script_count: int
    iframe_count: int
    stylesheet_count: int
    preconnect_count: int


class DiscoverRequest(BaseModel):
    target: str


class DiscoverResponse(BaseModel):
    analysis: ContentAnalysisRead
    resource_count: int
    script_count: int
    iframe_count: int
    stylesheet_count: int
    preconnect_count: int


# ---------------------------------------------------------------------------
# Structural diff (GET /api/analyses/{id}/diff?against={other_id})
# ---------------------------------------------------------------------------


class ResourceDiffEntry(BaseModel):
    resource_type: Optional[str] = None
    url: Optional[str] = None
    host: Optional[str] = None
    integrity: Optional[str] = None
    crossorigin: Optional[str] = None
    async_attr: bool = False
    defer_attr: bool = False
    provider: Optional[str] = None
    category: Optional[str] = None


class ModifiedResourceDiff(BaseModel):
    resource_type: str
    url: str
    changes: List[str] = []
    provider_changed: bool = False
    provider_base: Optional[str] = None
    provider_other: Optional[str] = None
    base: ResourceDiffEntry
    other: ResourceDiffEntry


class DiffSummary(BaseModel):
    base_total: int
    other_total: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    provider_changes_count: int
    similarity_score: float


class DiffAnalysisRef(BaseModel):
    id: int
    target: str
    created_at: datetime


class DiffResponse(BaseModel):
    base: DiffAnalysisRef
    against: DiffAnalysisRef
    summary: DiffSummary
    added: List[ResourceDiffEntry]
    removed: List[ResourceDiffEntry]
    modified: List[ModifiedResourceDiff]
    provider_changes: List[ModifiedResourceDiff]


# ---------------------------------------------------------------------------
# Content drift (GET /api/targets/{domain}/drift)
# ---------------------------------------------------------------------------


class DriftStep(BaseModel):
    from_analysis_id: int
    to_analysis_id: int
    from_created_at: datetime
    to_created_at: datetime
    resource_delta: int
    resource_delta_pct: Optional[float] = None
    providers_added: List[str] = []
    providers_removed: List[str] = []
    severity: str  # low | medium | high
    alert: str


class DriftSummary(BaseModel):
    analysis_count: int
    severity: str  # low | medium | high
    total_resource_delta: int
    providers_added: List[str] = []
    providers_removed: List[str] = []
    alert: str


class DriftResponse(BaseModel):
    domain: str
    first_created_at: Optional[datetime] = None
    last_created_at: Optional[datetime] = None
    summary: DriftSummary
    steps: List[DriftStep] = []
