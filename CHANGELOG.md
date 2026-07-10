# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-07-10

### Fixed

- `stop()` claims the loop and thread atomically under the registrar lock, so concurrent stops (ASGI lifespan plus a manual `container.shutdown()`) cannot interleave. The connection close is also bounded by `publish_timeout_seconds` with a warning instead of hanging shutdown forever.

## [0.1.0] - 2026-07-10

### Added

- `@consumer(queue, exchange=, routing_key=, exchange_type=)` marker for component methods (sync and async); JSON bodies decoded before dispatch.
- `@publisher` / `@publish` declarative publishing clients (sync stubs block on confirm, async stubs await).
- `RabbitRegistrar`: dedicated background asyncio loop owning the robust connection; ack-on-success, reject-without-requeue on failure; durable declarations; connection closed on container shutdown.
- Settings under the `rabbitmq` prefix: `url`, `enabled`, `prefetch_count`, `publish_timeout_seconds` (zero-config).
- Auto-discovery via the `pico_boot.modules` entry point.
