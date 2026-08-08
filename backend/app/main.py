import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from xwa_sdk import Event, to_dict

from . import analyzer, database, models, schemas

SERVICE_VERSION = "0.1.0"


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
def read_root():
    return {"status": "ok", "service": "musha", "version": SERVICE_VERSION}


@app.get("/api/health")
def health(db: Session = Depends(database.get_db)):
    try:
        db.execute(database.text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "database": db_status, "version": SERVICE_VERSION}


@app.post("/api/content/inventory", response_model=schemas.DiscoverResponse)
async def inventory(
    request: schemas.DiscoverRequest,
    db: Session = Depends(database.get_db),
):
    analysis = models.ContentAnalysis(
        target=request.target, status="RUNNING", started_at=datetime.utcnow()
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    try:
        result = await analyzer.analyze_target(request.target)
        analysis.page_title = result["title"]
        for resource in result["resources"]:
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
        analysis.status = "COMPLETED"
        analysis.finished_at = datetime.utcnow()
        db.commit()
    except analyzer.TargetError as exc:
        analysis.status = "ERROR"
        analysis.finished_at = datetime.utcnow()
        analysis.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    db.refresh(analysis)
    counts = _counts(analysis)
    return schemas.DiscoverResponse(analysis=analysis, **counts)


def _counts(analysis: models.ContentAnalysis) -> dict:
    by_type: dict[str, int] = {}
    for resource in analysis.resources:
        by_type[resource.resource_type] = by_type.get(resource.resource_type, 0) + 1
    return {
        "resource_count": len(analysis.resources),
        "script_count": by_type.get("script", 0),
        "iframe_count": by_type.get("iframe", 0),
        "stylesheet_count": by_type.get("stylesheet", 0),
    }


@app.websocket("/api/content/live")
async def websocket_inventory(websocket: WebSocket, target: str):
    """Stream the inventory pipeline as xwa-sdk Events."""
    await websocket.accept()
    seq = 0

    def event(event_type: str, payload=None) -> str:
        nonlocal seq
        seq += 1
        return json.dumps(
            to_dict(
                Event(
                    seq=seq,
                    type=event_type,
                    tool="musha",
                    analysis_id=target,
                    ts=_utcnow(),
                    payload=payload,
                )
            )
        )

    try:
        await websocket.send_text(event("analysis_started", {"target": target}))
        result = await analyzer.analyze_target(target)
        await websocket.send_text(
            event("analysis_progress", {"page": result["final_url"], "title": result["title"]})
        )
        for resource in result["resources"]:
            await websocket.send_text(event("item_found", {
                "kind": resource.resource_type,
                "url": resource.url,
                "provider": resource.provider,
            }))
        await websocket.send_text(
            event("analysis_completed", {"resource_count": len(result["resources"])})
        )
    except analyzer.TargetError as exc:
        await websocket.send_text(
            event("analysis_error", {"code": "TARGET_ERROR", "message": str(exc)})
        )
    except WebSocketDisconnect:
        return
