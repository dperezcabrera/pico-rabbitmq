Read and follow ./AGENTS.md for project conventions.

## Pico Ecosystem Context

pico-rabbitmq — RabbitMQ pub-sub over aio-pika: @consumer methods and @publisher/@publish declarative clients. Auto-discovered via the `pico_boot.modules` entry point. See it wired with the whole ecosystem in the flagship use case (pico-boot docs).

## Key Reminders

- pico-ioc dependency: `>= 2.2.0`; aio-pika `>= 9`
- **NEVER change `version_scheme`** in pyproject.toml. It MUST remain `"post-release"`.
- requires-python >= 3.11
- Commit messages: one line only
