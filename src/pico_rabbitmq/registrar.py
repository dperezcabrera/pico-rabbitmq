"""Connection owner and dispatcher.

Runs a dedicated asyncio loop in a daemon thread so consumers and
publishers work in any app — sync scripts, FastAPI, celery workers —
without lifespan wiring. Consumers resolve their component through the
container per message (prototype scope = fresh instance per message).

Delivery semantics: ack on success; on exception the message is
rejected WITHOUT requeue (log + drop) so a poison message cannot spin
the consumer. Configure a dead-letter exchange on the queue if you
need to keep failures.
"""

import asyncio
import concurrent.futures
import inspect
import json
import logging
import threading
from typing import Any

import aio_pika
from pico_ioc import PicoContainer, cleanup, component, configure

from .config import RabbitSettings
from .decorators import CONSUMER_META

logger = logging.getLogger(__name__)


@component
class RabbitRegistrar:
    def __init__(self, container: PicoContainer, settings: RabbitSettings):
        self._container = container
        self._settings = settings
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._connection = None
        self._channel = None
        self._exchanges: dict = {}
        self._started = threading.Event()
        self._lock = threading.Lock()

    @property
    def publish_timeout(self) -> float:
        return self._settings.publish_timeout_seconds

    # ── lifecycle ────────────────────────────────────────────────

    @configure
    def start(self) -> None:
        if not self._settings.enabled:
            return
        consumers = list(self._discover_consumers())
        if consumers:
            self._ensure_loop()
            self._run(self._setup_consumers(consumers))

    @cleanup
    def stop(self) -> None:
        if self._loop is None:
            return
        if self._connection is not None:
            self._run(self._connection.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        self._loop.close()
        self._loop = None
        self._thread = None
        self._started.clear()

    def _ensure_loop(self) -> None:
        with self._lock:
            if self._loop is not None:
                return
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, name="pico-rabbitmq", daemon=True)
            self._thread.start()
            self._run(self._connect())

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=self._settings.publish_timeout_seconds)

    async def _connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._settings.url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=self._settings.prefetch_count)
        self._started.set()

    async def _exchange_of(self, name: str, exchange_type: str = "topic"):
        if not name:
            return self._channel.default_exchange
        if name not in self._exchanges:
            self._exchanges[name] = await self._channel.declare_exchange(
                name, aio_pika.ExchangeType(exchange_type), durable=True
            )
        return self._exchanges[name]

    # ── consumer side ────────────────────────────────────────────

    def _discover_consumers(self):
        locator = getattr(self._container, "_locator", None)
        metadata_map = getattr(locator, "_metadata", {}) if locator else {}
        for md in metadata_map.values():
            cls = getattr(md, "concrete_class", None)
            if not inspect.isclass(cls):
                continue
            for name, fn in inspect.getmembers(cls, inspect.isfunction):
                meta = getattr(fn, CONSUMER_META, None)
                if meta is not None:
                    yield cls, name, meta

    async def _setup_consumers(self, consumers) -> None:
        for cls, method_name, meta in consumers:
            queue = await self._channel.declare_queue(meta["queue"], durable=True)
            if meta["exchange"]:
                exchange = await self._exchange_of(meta["exchange"], meta["exchange_type"])
                await queue.bind(exchange, routing_key=meta["routing_key"] or meta["queue"])
            await queue.consume(self._handler_for(cls, method_name))
            logger.info("consuming %s -> %s.%s", meta["queue"], cls.__name__, method_name)

    def _handler_for(self, cls, method_name):
        async def handle(message) -> None:
            async with message.process(requeue=False):
                body = json.loads(message.body)
                instance = await self._container.aget(cls)
                result = getattr(instance, method_name)(body)
                if inspect.iscoroutine(result):
                    await result

        async def safe_handle(message) -> None:
            try:
                await handle(message)
            except Exception:  # noqa: BLE001
                logger.exception("consumer %s.%s failed; message dropped", cls.__name__, method_name)

        return safe_handle

    # ── publisher side ───────────────────────────────────────────

    def publish(self, exchange: str, routing_key: str, message: Any) -> concurrent.futures.Future:
        if not self._settings.enabled:
            raise RuntimeError("pico-rabbitmq is disabled (rabbitmq.enabled=false)")
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(self._do_publish(exchange, routing_key, message), self._loop)

    async def _do_publish(self, exchange_name: str, routing_key: str, message: Any) -> None:
        exchange = await self._exchange_of(exchange_name)
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        await exchange.publish(aio_pika.Message(body=body, content_type="application/json"), routing_key=routing_key)
