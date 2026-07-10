"""Marker decorators for the two sides of RabbitMQ messaging.

Consumer side: ``@consumer`` on a component method subscribes it to a
queue; the method receives the JSON-decoded message body.

Publisher side: ``@publisher`` on a class of ``@publish`` stubs turns it
into an injectable component whose methods send their ``message``
argument as a JSON body (same generated-implementation idiom as
pico-httpx clients).
"""

import functools
import inspect

from pico_ioc import component

CONSUMER_META = "_pico_rabbitmq_consumer_meta"
PUBLISH_META = "_pico_rabbitmq_publish_meta"
PUBLISHER_META = "_pico_rabbitmq_publisher_meta"


def consumer(queue: str, *, exchange: str = "", routing_key: str = "", exchange_type: str = "topic"):
    """Subscribe a component method to ``queue``.

    With ``exchange`` empty the queue receives messages published to the
    default exchange under its own name. Otherwise the exchange is
    declared (``exchange_type``) and the queue bound with ``routing_key``.
    """
    if not queue:
        raise ValueError("@consumer requires a queue name")

    def dec(fn):
        setattr(
            fn,
            CONSUMER_META,
            {"queue": queue, "exchange": exchange, "routing_key": routing_key, "exchange_type": exchange_type},
        )
        return fn

    return dec


def publisher(cls):
    """Turn a class of ``@publish`` stubs into an injectable component."""
    setattr(cls, PUBLISHER_META, True)
    if "__init__" not in cls.__dict__:

        def __init__(self, registrar):
            self._pico_rabbitmq = registrar

        from .registrar import RabbitRegistrar

        __init__.__annotations__ = {"registrar": RabbitRegistrar}
        cls.__init__ = __init__
    return component(cls)


def publish(*, exchange: str = "", routing_key: str):
    """Generate a publishing implementation for a stub method.

    The stub's ``message`` argument (any JSON-serializable value) is the
    body. Sync stubs block until the broker confirms; async stubs await it.
    """
    if not routing_key and not exchange:
        raise ValueError("@publish requires a routing_key (or an exchange)")

    def dec(fn):
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_impl(self, message):
                import asyncio

                future = self._pico_rabbitmq.publish(exchange, routing_key, message)
                return await asyncio.wrap_future(future)

            setattr(async_impl, PUBLISH_META, {"exchange": exchange, "routing_key": routing_key})
            return async_impl

        @functools.wraps(fn)
        def sync_impl(self, message):
            future = self._pico_rabbitmq.publish(exchange, routing_key, message)
            return future.result(timeout=self._pico_rabbitmq.publish_timeout)

        setattr(sync_impl, PUBLISH_META, {"exchange": exchange, "routing_key": routing_key})
        return sync_impl

    return dec
