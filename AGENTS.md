# pico-rabbitmq

RabbitMQ pub-sub over aio-pika: @consumer methods and @publisher/@publish declarative clients.

## Commands

```bash
pip install -e ".[dev]"
pytest tests/ -v
pytest --cov=pico_rabbitmq --cov-report=term-missing tests/
mkdocs serve -f mkdocs.yml
```

## Project Structure

```
src/pico_rabbitmq/
  __init__.py       # Public API
  decorators.py     # @consumer marker; @publisher class + @publish stub->impl
  registrar.py      # RabbitRegistrar: daemon-thread loop, connect/declare/consume/publish
  config.py         # RabbitSettings (prefix "rabbitmq")
```

## Key Concepts

- Dedicated asyncio loop in a daemon thread: works in sync scripts, FastAPI and workers without lifespan wiring.
- Ack on success; on exception log + reject WITHOUT requeue (DLX to keep failures) — poison messages never spin.
- Sync publish stubs block on broker confirm (publish_timeout_seconds); async stubs await. Lazy connect for publisher-only apps.
- JSON-only bodies by design.
- `rabbitmq.enabled: false` -> consumers off and publish raises (loud, never silent).

## Boundaries

- Complements pico-celery (tasks); this module is events/fan-out/topic routing
- No per-message headers/serialization DSL
- Do not modify `_version.py`
