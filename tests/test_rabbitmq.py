import sys

import pytest
from pico_ioc import component

from pico_rabbitmq import RabbitRegistrar, consumer, publish, publisher


@component
class OrderHandler:
    seen = []
    async_seen = []

    @consumer("orders")
    def on_order(self, message: dict):
        OrderHandler.seen.append(message)

    @consumer("orders-async", exchange="events", routing_key="orders.*")
    async def on_order_async(self, message: dict):
        OrderHandler.async_seen.append(message)


@component
class Exploder:
    attempts = 0

    @consumer("poison")
    def on_message(self, message: dict):
        Exploder.attempts += 1
        raise RuntimeError("boom")


@publisher
class OrderEvents:
    @publish(routing_key="orders")
    def order_created(self, message): ...

    @publish(exchange="events", routing_key="orders.created")
    async def order_created_async(self, message): ...


def test_consumer_receives_json_and_acks(make_container, broker, deliver):
    OrderHandler.seen = []
    make_container(sys.modules[__name__])
    message = deliver("orders", {"id": 1})
    assert OrderHandler.seen == [{"id": 1}]
    assert message.acked is True


def test_async_consumer_and_binding(make_container, broker, deliver):
    OrderHandler.async_seen = []
    make_container(sys.modules[__name__])
    assert ("events", "orders.*") in broker.queues["orders-async"].bindings
    deliver("orders-async", {"id": 2})
    assert OrderHandler.async_seen == [{"id": 2}]


def test_failing_consumer_rejects_without_requeue(make_container, broker, deliver):
    Exploder.attempts = 0
    make_container(sys.modules[__name__])
    message = deliver("poison", {"bad": True})
    assert Exploder.attempts == 1
    assert message.rejected is True
    assert message.acked is False


def test_sync_publish_reaches_bound_queue(make_container, broker):
    OrderHandler.seen = []
    container = make_container(sys.modules[__name__])
    container.get(OrderEvents).order_created({"id": 3})
    assert OrderHandler.seen == [{"id": 3}]
    assert broker.channel.default_exchange.published[0][0] == "orders"


@pytest.mark.asyncio
async def test_async_publish_via_named_exchange(make_container, broker):
    OrderHandler.async_seen = []
    container = make_container(sys.modules[__name__])
    await container.get(OrderEvents).order_created_async({"id": 4})
    assert OrderHandler.async_seen == [{"id": 4}]
    assert broker.exchanges["events"].published[0][0] == "orders.created"


def test_prefetch_and_connection_lifecycle(make_container, broker):
    container = make_container(sys.modules[__name__], config={"rabbitmq": {"prefetch_count": 3}})
    assert broker.channel.prefetch == 3
    connection = broker.connection
    container.shutdown()
    assert connection.closed is True


def test_disabled_starts_nothing(make_container, broker):
    container = make_container(sys.modules[__name__], config={"rabbitmq": {"enabled": False}})
    assert broker.connection is None
    with pytest.raises(RuntimeError, match="disabled"):
        container.get(OrderEvents).order_created({"id": 5})


def test_publisher_without_consumers_connects_lazily(make_container, broker):
    container = make_container()

    @publisher
    class Lone:
        @publish(routing_key="solo")
        def send(self, message): ...

    registrar = container.get(RabbitRegistrar)
    assert broker.connection is None
    Lone(registrar).send({"id": 6})
    assert broker.connection is not None
    assert broker.channel.default_exchange.published[0][0] == "solo"


def test_consumer_requires_queue_name():
    with pytest.raises(ValueError, match="queue"):
        consumer("")


def test_publish_requires_routing():
    with pytest.raises(ValueError, match="routing_key"):
        publish(routing_key="")


def test_publisher_with_custom_init(make_container, broker):
    @publisher
    class Custom:
        def __init__(self, registrar: RabbitRegistrar):
            self._pico_rabbitmq = registrar
            self.ready = True

    container = make_container()
    instance = Custom(container.get(RabbitRegistrar))
    assert instance.ready is True


def test_concurrent_stop_is_safe(make_container, broker):
    import asyncio
    import threading

    container = make_container(sys.modules[__name__])
    registrar = container.get(RabbitRegistrar)
    # loop real corriendo: sin el, el test pasa en vacio (stop retorna en el guard)
    registrar._loop = asyncio.new_event_loop()
    registrar._thread = threading.Thread(target=registrar._loop.run_forever, daemon=True)
    registrar._thread.start()
    loop = registrar._loop

    errors = []

    def stop():
        try:
            registrar.stop()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=stop) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    registrar.stop()
    assert errors == []
    assert registrar._loop is None
    assert loop.is_closed()
