# Getting Started

## Prerequisites

- Python >= 3.11
- pico-ioc >= 2.2.0 (pico-boot recommended for auto-discovery)
- aio-pika >= 9 (installed automatically)
- A reachable RabbitMQ broker

## Install

```bash
pip install pico-rabbitmq
```

## Key concepts

| Piece | What it does |
|---|---|
| `@consumer(queue, ...)` | Subscribes a component method to a queue; JSON body decoded to the `message` argument |
| `@publisher` + `@publish(...)` | Class of stubs whose methods publish their `message` argument as JSON |
| `RabbitRegistrar` | Owns the connection on a dedicated background loop; starts with the container, closes with it |
| `rabbitmq.url` | Broker URL (default `amqp://guest:guest@localhost/`) |

## Consuming

```python
@component
class OrderProjections:
    @consumer("orders-projection", exchange="events", routing_key="orders.*")
    async def on_order_event(self, message: dict):
        ...
```

- With `exchange` empty the queue only receives direct publishes (default exchange, routing key = queue name).
- With `exchange` set, the exchange is declared (`exchange_type`, default `topic`) and the queue bound with `routing_key`.
- Sync and async methods both work; each message resolves the component through the container.
- **Failure policy**: exceptions are logged and the message is rejected without requeue, so a poison message cannot spin the consumer. Attach a dead-letter exchange to the queue if you need to keep failures.
- `rabbitmq.prefetch_count` (default 10) bounds in-flight messages.

## Publishing

```python
@publisher
class OrderEvents:
    @publish(exchange="events", routing_key="orders.created")
    def order_created(self, message): ...

    @publish(routing_key="jobs")          # default exchange -> queue "jobs"
    async def enqueue_job(self, message): ...
```

Sync stubs block until the broker confirms (bounded by `rabbitmq.publish_timeout_seconds`); async stubs await the confirm. The connection is opened lazily on first publish if no consumer started it.

## Disabling

```yaml
rabbitmq:
  enabled: false
```

Consumers do not start and publish attempts raise `RuntimeError` — loud, because a silently dropped event is worse than a crash.
