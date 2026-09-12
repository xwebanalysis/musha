import csv
import io
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from xwa_sdk import Error, Event, to_dict

from . import analyzer, database, models, schemas, security

SERVICE_VERSION = "0.2.0"
TOOL = "musha"

ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL",
    502: "UPSTREAM_ERROR",
    503: "SERVICE_UNAVAILABLE",
}
RETRYABLE_STATUS = {429, 502, 503}


def _error_payload(code: str, message: str, detail=None, retryable: bool = False) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
            "retryable": retryable,
        }
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.wait_for_db()
    models.Base.metadata.create_all(bind=database.engine)
    yield


app = FastAPI(
    title="Musha API",
    description="Web content and DOM analysis",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, **security.cors_settings())
app.middleware("http")(security.auth_middleware)
app.middleware("http")(security.rate_limit_middleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else code
    detail = exc.detail if isinstance(exc.detail, dict) else None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(code, message, detail, exc.status_code in RETRYABLE_STATUS),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            "VALIDATION_ERROR",
            "Request validation failed.",
            {"errors": jsonable_encoder(exc.errors())},
        ),
    )


class TokenRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_in: int


def _utcnow() -> str:
    """UTC ISO-8601 timestamp for xwa-sdk events."""
    return datetime.now(timezone.utc).isoformat()


def _dbnow() -> datetime:
    """Naive UTC timestamp for database columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@app.get("/")
def read_root():
    return {"status": "ok", "service": TOOL, "version": SERVICE_VERSION}


@app.get("/api/health")
def health():
    db_status = "ok" if database.ping() else "error"
    return JSONResponse(
        status_code=200 if db_status == "ok" else 503,
        content={
            "status": db_status,
            "database": db_status,
            "version": SERVICE_VERSION,
            "tool": TOOL,
        },
    )


@app.post("/api/auth/token", response_model=TokenResponse)
def issue_token(request: TokenRequest):
    """Issue a signed token. Only available when MUSHA_JWT_SECRET is set."""
    if not security.AUTH_REQUIRED:
        raise HTTPException(status_code=403, detail="Auth is disabled (no MUSHA_JWT_SECRET).")
    if request.password != security.AUTH_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password.")
    return TokenResponse(
        token=security.issue_token(),
        expires_in=security.TOKEN_TTL_HOURS * 3600,
    )


def _persist_resources(
    db: Session, analysis: models.ContentAnalysis, resources: list
) -> None:
    for resource in resources:
        db.add(
            models.ThirdPartyResource(
                analysis_id=analysis.id,
                resource_type=resource.resource_type,
                url=resource.url,
                host=resource.host,
                integrity=resource.integrity,
                crossorigin=resource.crossorigin,
                async_attr=int(resource.async_attr),
                defer_attr=int(resource.defer_attr),
                provider=resource.provider,
                category=resource.category,
            )
        )


def _counts(analysis: models.ContentAnalysis) -> dict:
    by_type: dict[str, int] = {}
    for resource in analysis.resources:
        by_type[resource.resource_type] = by_type.get(resource.resource_type, 0) + 1
    return {
        "resource_count": len(analysis.resources),
        "script_count": by_type.get("script", 0),
        "iframe_count": by_type.get("iframe", 0),
        "stylesheet_count": by_type.get("stylesheet", 0),
        "preconnect_count": by_type.get("preconnect", 0),
    }


def _summary(analysis: models.ContentAnalysis) -> schemas.ContentAnalysisListItem:
    counts = _counts(analysis)
    return schemas.ContentAnalysisListItem(
        id=analysis.id,
        target=analysis.target,
        status=analysis.status,
        analysis_type=analysis.analysis_type,
        created_at=analysis.created_at,
        page_title=analysis.page_title,
        **counts,
    )


def _analysis_export(analysis: models.ContentAnalysis) -> dict:
    """Full JSON export of an analysis as a downloadable file."""
    return {
        "id": analysis.id,
        "target": analysis.target,
        "status": analysis.status,
        "analysis_type": analysis.analysis_type,
        "created_at": _iso(analysis.created_at),
        "started_at": _iso(analysis.started_at),
        "finished_at": _iso(analysis.finished_at),
        "error_message": analysis.error_message,
        "page_title": analysis.page_title,
        "resources": [
            {
                "resource_type": resource.resource_type,
                "url": resource.url,
                "host": resource.host,
                "integrity": resource.integrity,
                "crossorigin": resource.crossorigin,
                "async_attr": bool(resource.async_attr),
                "defer_attr": bool(resource.defer_attr),
                "provider": resource.provider,
                "category": resource.category,
            }
            for resource in analysis.resources
        ],
    }


def _resources_csv(analysis: models.ContentAnalysis) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "analysis_id",
            "target",
            "status",
            "page_title",
            "resource_type",
            "url",
            "host",
            "integrity",
            "crossorigin",
            "async",
            "defer",
            "provider",
            "category",
        ]
    )
    for resource in analysis.resources:
        writer.writerow(
            [
                analysis.id,
                analysis.target,
                analysis.status,
                analysis.page_title or "",
                resource.resource_type or "",
                resource.url or "",
                resource.host or "",
                resource.integrity or "",
                resource.crossorigin or "",
                int(resource.async_attr or 0),
                int(resource.defer_attr or 0),
                resource.provider or "",
                resource.category or "",
            ]
        )
    return buffer.getvalue()


@app.post("/api/content/inventory", response_model=schemas.DiscoverResponse)
async def inventory(
    request: schemas.DiscoverRequest,
    db: Session = Depends(database.get_db),
):
    analysis = models.ContentAnalysis(
        target=request.target, status="RUNNING", started_at=_dbnow()
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        result = await analyzer.analyze_target(request.target)
        analysis.page_title = result["title"]
        _persist_resources(db, analysis, result["resources"])
        analysis.status = "COMPLETED"
        analysis.finished_at = _dbnow()
        db.commit()
    except analyzer.TargetError as exc:
        analysis.status = "ERROR"
        analysis.finished_at = _dbnow()
        analysis.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db.refresh(analysis)
    return schemas.DiscoverResponse(analysis=analysis, **_counts(analysis))


@app.get("/api/analyses", response_model=list[schemas.ContentAnalysisListItem])
def list_analyses(db: Session = Depends(database.get_db)):
    rows = (
        db.query(models.ContentAnalysis)
        .order_by(models.ContentAnalysis.id.desc())
        .limit(50)
        .all()
    )
    return [_summary(row) for row in rows]


@app.get("/api/analyses/{analysis_id}", response_model=schemas.ContentAnalysisRead)
def get_analysis(analysis_id: int, db: Session = Depends(database.get_db)):
    analysis = db.get(models.ContentAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis


@app.get("/api/analyses/{analysis_id}/export")
def export_analysis(
    analysis_id: int,
    fmt: Literal["json", "csv"] = Query("json", alias="format"),
    db: Session = Depends(database.get_db),
):
    """Download an analysis as JSON (default) or CSV."""
    analysis = db.get(models.ContentAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    if fmt == "csv":
        return Response(
            content=_resources_csv(analysis),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="musha-analysis-{analysis.id}.csv"'
            },
        )

    return JSONResponse(
        content=_analysis_export(analysis),
        headers={
            "Content-Disposition": f'attachment; filename="musha-analysis-{analysis.id}.json"'
        },
    )


@app.delete("/api/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: int, db: Session = Depends(database.get_db)):
    analysis = db.get(models.ContentAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    db.delete(analysis)
    db.commit()
    return Response(status_code=204)


@app.delete("/api/analyses", status_code=204)
def delete_all_analyses(db: Session = Depends(database.get_db)):
    db.query(models.ContentAnalysis).delete()
    db.commit()
    return Response(status_code=204)


@app.websocket("/api/content/live")
async def websocket_inventory(websocket: WebSocket, target: str, token: str | None = None):
    """Persist the analysis and stream the inventory pipeline as xwa-sdk Events."""
    if security.AUTH_REQUIRED and not security.validate_ws_token(token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await websocket.accept()

    db = database.SessionLocal()
    analysis = models.ContentAnalysis(
        target=target, status="RUNNING", started_at=_dbnow()
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    analysis_id = str(analysis.id)
    seq = 0

    def event(event_type: str, payload=None) -> str:
        nonlocal seq
        seq += 1
        return json.dumps(
            to_dict(
                Event(
                    seq=seq,
                    type=event_type,
                    tool=TOOL,
                    analysis_id=analysis_id,
                    ts=_utcnow(),
                    payload=payload,
                )
            )
        )

    try:
        await websocket.send_text(event("analysis_started", {"target": target}))
        result = await analyzer.analyze_target(target)
        analysis.page_title = result["title"]
        _persist_resources(db, analysis, result["resources"])
        analysis.status = "COMPLETED"
        analysis.finished_at = _dbnow()
        db.commit()

        await websocket.send_text(
            event("analysis_progress", {"page": result["final_url"], "title": result["title"]})
        )
        for resource in result["resources"]:
            await websocket.send_text(event("item_found", {
                "kind": resource.resource_type,
                "url": resource.url,
                "provider": resource.provider,
            }))
        counts = _counts(analysis)
        await websocket.send_text(event("analysis_completed", counts))
    except analyzer.TargetError as exc:
        analysis.status = "ERROR"
        analysis.finished_at = _dbnow()
        analysis.error_message = str(exc)
        db.commit()
        try:
            await websocket.send_text(
                event("analysis_error", to_dict(Error(code="TARGET_ERROR", message=str(exc), retryable=True)))
            )
        except WebSocketDisconnect:
            return
    except WebSocketDisconnect:
        analysis.status = "CANCELLED"
        analysis.finished_at = _dbnow()
        db.commit()
    finally:
        db.close()
