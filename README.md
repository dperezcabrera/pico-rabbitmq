# pico-rabbitmq

[![PyPI](https://img.shields.io/pypi/v/pico-rabbitmq.svg)](https://pypi.org/project/pico-rabbitmq/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/dperezcabrera/pico-rabbitmq)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![CI (tox matrix)](https://github.com/dperezcabrera/pico-rabbitmq/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/dperezcabrera/pico-rabbitmq/branch/main/graph/badge.svg)](https://codecov.io/gh/dperezcabrera/pico-rabbitmq)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=dperezcabrera_pico-rabbitmq&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=dperezcabrera_pico-rabbitmq)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=dperezcabrera_pico-rabbitmq&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=dperezcabrera_pico-rabbitmq)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=dperezcabrera_pico-rabbitmq&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=dperezcabrera_pico-rabbitmq)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pico-rabbitmq)](https://pypi.org/project/pico-rabbitmq/)
[![Docs](https://img.shields.io/badge/Docs-pico--rabbitmq-blue?style=flat&logo=readthedocs&logoColor=white)](https://dperezcabrera.github.io/pico-rabbitmq/)
[![Interactive Lab](https://img.shields.io/badge/Learn-online-green?style=flat&logo=python&logoColor=white)](https://dperezcabrera.github.io/pico-learn/)

RabbitMQ pub-sub for the [pico ecosystem](https://github.com/dperezcabrera/pico-ioc): `@consumer` methods and declarative `@publisher` clients over aio-pika. Covers what pico-celery does not: events, fan-out, topic routing.

## Installation

```bash
pip install pico-rabbitmq
```

## Quick start

```yaml
rabbitmq:
  url: amqp://guest:guest@rabbit.internal/
```

Consume — a component method per queue, JSON body decoded for you:

```python
from pico_ioc import component
from pico_rabbitmq import consumer

@component
class OrderProjections:
    @consumer("orders-projection", exchange="events", routing_key="orders.*")
    async def on_order_event(self, message: dict):
        ...
```

Publish — stubs, like a pico-httpx client:

```python
from pico_rabbitmq import publisher, publish

@publisher
class OrderEvents:
    @publish(exchange="events", routing_key="orders.created")
    def order_created(self, message): ...
```

Semantics:

- Consumers and publishers run on a dedicated background loop — works in sync scripts, FastAPI apps and workers alike, no lifespan wiring.
- Each message resolves its component through the container (prototype scope = fresh instance per message).
- Ack on success; on exception the message is logged and rejected **without requeue** (configure a dead-letter exchange to keep failures).
- Sync publish stubs block until the broker confirms; async stubs await it.
- Queues and named exchanges are declared durable; the connection closes on container shutdown.

## Documentation

Full documentation: https://dperezcabrera.github.io/pico-rabbitmq/

## License

MIT
