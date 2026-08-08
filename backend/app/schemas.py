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


class DiscoverRequest(BaseModel):
    target: str


class DiscoverResponse(BaseModel):
    analysis: ContentAnalysisRead
    resource_count: int
    script_count: int
    iframe_count: int
    stylesheet_count: int
