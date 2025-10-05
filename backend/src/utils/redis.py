import asyncio
import contextlib
import json
from typing import Dict, Set, Tuple

from redis.asyncio import Redis


Key = Tuple[int, int]  # (source_id, user_id)


class RedisBroker:
    def __init__(self, url: str, in_channel: str, out_channel: str):
        self._url = url
        self._in = in_channel
        self._out = out_channel

        self._pub: Redis | None = None
        self._sub: Redis | None = None
        self._task: asyncio.Task | None = None

        # key -> набор очередей подписчиков
        self._listeners: Dict[Key, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task:
            return
        self._pub = Redis.from_url(self._url, encoding="utf-8", decode_responses=True)
        self._sub = Redis.from_url(self._url, encoding="utf-8", decode_responses=True)

        async def _runner():
            pubsub = self._sub.pubsub()
            await pubsub.subscribe(self._out)
            try:
                while True:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if not msg or msg.get("type") != "message":
                        continue
                    try:
                        data = json.loads(msg["data"])
                    except json.JSONDecodeError:
                        continue
                    src = data.get("source_id")
                    uid = data.get("user_id")
                    if not isinstance(src, int) or not isinstance(uid, int):
                        continue
                    await self._dispatch((src, uid), data)
            finally:
                with contextlib.suppress(Exception):
                    await pubsub.unsubscribe(self._out)
                with contextlib.suppress(Exception):
                    await pubsub.close()

        self._task = asyncio.create_task(_runner())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task
            self._task = None
        if self._pub:
            with contextlib.suppress(Exception):
                await self._pub.aclose()
            self._pub = None
        if self._sub:
            with contextlib.suppress(Exception):
                await self._sub.aclose()
            self._sub = None

    async def publish_in(self, payload: dict) -> None:
        assert self._pub is not None, "Broker not started"
        await self._pub.publish(self._in, json.dumps(payload))

    async def register(self, key: Key, max_queue: int = 100) -> asyncio.Queue:
        """Регистрирует слушателя и возвращает его очередь сообщений."""
        q: asyncio.Queue = asyncio.Queue(maxsize=max_queue)
        async with self._lock:
            self._listeners.setdefault(key, set()).add(q)
        return q

    async def unregister(self, key: Key, q: asyncio.Queue) -> None:
        async with self._lock:
            s = self._listeners.get(key)
            if not s:
                return
            s.discard(q)
            if not s:
                self._listeners.pop(key, None)

    async def _dispatch(self, key: Key, data: dict) -> None:
        async with self._lock:
            queues = list(self._listeners.get(key, ()))
        for q in queues:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                async with self._lock:
                    s = self._listeners.get(key)
                    if s and q in s:
                        s.discard(q)
                        if not s:
                            self._listeners.pop(key, None)
