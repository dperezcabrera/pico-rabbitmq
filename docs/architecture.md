# Architecture

```
@consumer(queue, exchange=, routing_key=)     @publisher + @publish stubs
        |                                             |
   marks method meta                    generated impl -> registrar.publish()
        |                                             |
RabbitRegistrar (@component) -------------------------+
   @configure: discover consumers -> connect_robust -> declare + consume
   @cleanup:  close connection, stop loop
        |
dedicated asyncio loop in a daemon thread ("pico-rabbitmq")
   per message: container.aget(cls) -> method(json.loads(body))
```

## Design decisions

- **Dedicated loop in a daemon thread**: aio-pika is async, but pico apps are
  not uniformly so. Owning a private loop means consumers and publishers work
  identically in sync scripts, FastAPI apps and workers — no lifespan wiring,
  no event-loop entanglement with the host app.
- **Marker + registrar discovery** (pico-celery's idiom): decorators only
  attach metadata; one component scans the locator at startup. Declarations
  (queues, exchanges, bindings) happen exactly once, at connect time.
- **Container resolution per message**: scope semantics stay the container's
  — prototype components get a fresh instance per message.
- **Reject-without-requeue on failure**: a deterministically failing message
  requeued forever is a hot loop. Failures are logged with traceback and
  dropped; keeping them is an explicit queue-level decision (dead-letter
  exchange), not a hidden default.
- **Generated publisher stubs** (pico-httpx's idiom): calling the method IS
  the publish. Sync stubs block on broker confirm (bounded by
  `publish_timeout_seconds`); async stubs await it. Publishing connects
  lazily if no consumer already did.
- **JSON-only bodies**: `application/json` of the `message` argument covers
  the ecosystem's common case; other formats use aio-pika directly rather
  than growing a serialization DSL here.
