"""In-memory fake of the aio-pika surface pico-rabbitmq uses.

Tests exercise our glue (discovery, dispatch, ack/reject policy,
publisher stubs) against a broker-less fake; aio-pika itself is trusted.
"""

import asyncio
import json

import pytest

import pico_rabbitmq.registrar as registrar_module


class FakeMessage:
    def __init__(self, body: bytes):
        self.body = body
        self.acked = False
        self.rejected = False

    def process(self, requeue=False):
        message = self

        class _Ctx:
            async def __aenter__(self):
                return message

            async def __aexit__(self, exc_type, exc, tb):
                if exc_type is None:
                    message.acked = True
                else:
                    message.rejected = True
                return False

        return _Ctx()


class FakeQueue:
    def __init__(self, broker, name):
        self._broker = broker
        self.name = name
        self.callback = None
        self.bindings = []

    async def bind(self, exchange, routing_key=""):
        self.bindings.append((exchange.name, routing_key))

    async def consume(self, callback):
        self.callback = callback


class FakeExchange:
    def __init__(self, broker, name, type_=""):
        self._broker = broker
        self.name = name
        self.type = type_
        self.published = []

    async def publish(self, message, routing_key=""):
        import fnmatch

        self.published.append((routing_key, message.body))
        for queue in self._broker.queues.values():
            if self.name == "":
                match = queue.name == routing_key
            else:
                match = any(ex == self.name and fnmatch.fnmatch(routing_key, pattern) for ex, pattern in queue.bindings)
            if match and queue.callback is not None:
                await queue.callback(FakeMessage(message.body))


class FakeChannel:
    def __init__(self, broker):
        self._broker = broker
        self.default_exchange = FakeExchange(broker, "")
        self.prefetch = None

    async def set_qos(self, prefetch_count):
        self.prefetch = prefetch_count

    async def declare_exchange(self, name, type_, durable=True):
        self._broker.exchanges[name] = FakeExchange(self._broker, name, type_)
        return self._broker.exchanges[name]

    async def declare_queue(self, name, durable=True):
        self._broker.queues[name] = FakeQueue(self._broker, name)
        return self._broker.queues[name]


class FakeConnection:
    def __init__(self, broker):
        self._broker = broker
        self.closed = False

    async def channel(self):
        self._broker.channel = FakeChannel(self._broker)
        return self._broker.channel

    async def close(self):
        self.closed = True


class FakeBroker:
    def __init__(self):
        self.queues = {}
        self.exchanges = {}
        self.channel = None
        self.connection = None
        self.connect_urls = []

    async def connect_robust(self, url):
        self.connect_urls.append(url)
        self.connection = FakeConnection(self)
        return self.connection


class FakeAioPika:
    def __init__(self, broker):
        self._broker = broker
        self.connect_robust = broker.connect_robust

    @staticmethod
    def ExchangeType(value):
        return value

    class Message:
        def __init__(self, body, content_type=""):
            self.body = body
            self.content_type = content_type


@pytest.fixture
def broker(monkeypatch):
    fake = FakeBroker()
    monkeypatch.setattr(registrar_module, "aio_pika", FakeAioPika(fake))
    return fake


@pytest.fixture
def deliver(broker):
    """Push a message into a consumed queue from the test thread."""

    def _deliver(queue_name: str, payload) -> FakeMessage:
        queue = broker.queues[queue_name]
        message = FakeMessage(json.dumps(payload).encode())
        asyncio.run_coroutine_threadsafe(queue.callback(message), broker.loop).result(timeout=5)
        return message

    return _deliver


@pytest.fixture
def make_container(make_container, broker):
    """Extends the plugin fixture: deliver() needs the registrar loop on the fake broker."""
    plugin_make = make_container

    def _make(*modules, config=None):
        container = plugin_make(*modules, config=config)
        from pico_rabbitmq import RabbitRegistrar

        broker.loop = container.get(RabbitRegistrar)._loop
        return container

    return _make
