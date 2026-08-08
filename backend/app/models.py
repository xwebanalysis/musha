from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class ContentAnalysis(Base):
    """An analysis session against a target (xwa-sdk Analysis)."""

    __tablename__ = "content_analyses"
    id = Column(Integer, primary_key=True, index=True)
    target = Column(String, index=True)
    status = Column(String, default="RUNNING")  # RUNNING, COMPLETED, ERROR
    analysis_type = Column(String, default="content_scan")
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    page_title = Column(String, nullable=True)

    resources = relationship(
        "ThirdPartyResource", back_populates="analysis", cascade="all, delete-orphan"
    )


class ThirdPartyResource(Base):
    """An external resource referenced by the page (script, iframe, stylesheet)."""

    __tablename__ = "third_party_resources"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("content_analyses.id", ondelete="CASCADE"))

    resource_type = Column(String)  # script, iframe, stylesheet, preconnect
    url = Column(Text)
    host = Column(String, nullable=True)
    integrity = Column(String, nullable=True)
    crossorigin = Column(String, nullable=True)
    async_attr = Column(Integer, default=0)
    defer_attr = Column(Integer, default=0)
    provider = Column(String, nullable=True)
    category = Column(String, nullable=True)  # analytics, cdn, ads, social, ...

    analysis = relationship("ContentAnalysis", back_populates="resources")
