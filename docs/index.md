# pico-rabbitmq

RabbitMQ pub-sub on pico components: `@consumer` methods, declarative `@publisher` clients.

## Install

```bash
pip install pico-rabbitmq
```

## 30-second example

```python
from pico_ioc import component
from pico_rabbitmq import consumer, publisher, publish

@component
class Audit:
    @consumer("audit", exchange="events", routing_key="#")
    def on_event(self, message: dict):
        ...

@publisher
class Events:
    @publish(exchange="events", routing_key="orders.created")
    def order_created(self, message): ...
```

No wiring: the module connects at startup, declares what it needs, dispatches JSON bodies to your methods and closes with the container.
