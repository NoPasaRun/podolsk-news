from fastapi import APIRouter
from tortoise.expressions import F
from datetime import datetime, timezone
from orm.models import Cluster
from schemes.telemetry import EventBatch

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events")
async def ingest(batch: EventBatch):
    deltas = {}
    now = datetime.now(timezone.utc)

    for ev in batch.events:
        if ev.type == "impression":
            delta = 1.0
        elif ev.type == "dwell":
            secs = (ev.dwell_ms or 0) / 1000.0
            delta = max(0.0, int(secs // 5)) * 1.0
        elif ev.type == "click":
            delta = 5.0
        elif ev.type == "outbound":
            delta = 8.0
        else:
            delta = 0.0

        if delta <= 0 or not ev.cluster_id:
            continue

        try:
            cl = await Cluster.get(id=ev.cluster_id)
            hours = max(0.0, (now - cl.first_published_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0)
            recency = 2.718281828 ** (-hours / 48.0)
        except Exception:
            recency = 1.0

        deltas[ev.cluster_id] = deltas.get(ev.cluster_id, 0.0) + delta * recency

    for cid, d in deltas.items():
        await Cluster.filter(id=cid).update(weight=F("weight") + int(round(d)))

    return {"status": "ok", "updated": len(deltas)}
