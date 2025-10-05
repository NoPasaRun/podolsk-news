import asyncio
import contextlib
import json
from typing import Dict, Any

from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_until_first_complete

from orm.models import Source
from routes.source import get_broker
from utils.auth import get_current_user_ws
from utils.enums import SourceStatus


async def send_source_on_check(ws: WebSocket, json_text: str):
    broker, user = get_broker(ws), await get_current_user_ws(ws)
    try:
        obj: Dict[str, Any] = json.loads(json_text)
    except json.JSONDecodeError:
        return await ws.send_json({"type": "error", "error": "bad_json"})

    source_id = int(obj.get("source_id", 0))

    if (source := await Source.get_or_none(id=source_id, status=SourceStatus.ERROR)) is None:
        return await ws.send_json({"type": "error", "error": "source_not_found", "source_id": source_id})

    source.status = SourceStatus.VALIDATING
    await source.save()
    await broker.publish_in({"source_id": source_id, "user_id": user.id})
    await ws.send_json({"status": SourceStatus.VALIDATING, "source_id": source_id})

    return source_id, user.id


async def source_ws(websocket: WebSocket):
    await websocket.accept(subprotocol="bearer")
    broker = get_broker(websocket)
    key = queue = None

    try:
        init_txt = await websocket.receive_text()
        if not (key := await send_source_on_check(websocket, init_txt)):
            raise WebSocketDisconnect()
        queue = await broker.register(key)

        stop = asyncio.Event()
        async def reader():
            try:
                while not stop.is_set():
                    txt = await websocket.receive_text()
                    await send_source_on_check(websocket, txt)
            except WebSocketDisconnect:
                pass
            finally:
                stop.set()

        async def sender():
            try:
                while not stop.is_set():
                    data = await queue.get()
                    await websocket.send_json(data)
            finally:
                stop.set()

        await run_until_first_complete((reader, {}), (sender, {}))

    finally:
        with contextlib.suppress(Exception):
            if key is not None and queue is not None:
                await broker.unregister(key, queue)
        with contextlib.suppress(Exception):
            await websocket.close()
