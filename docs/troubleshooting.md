# Troubleshooting

## My consumer never receives messages

- Is the component's module registered (pico-boot discovery or explicit
  `init(modules=[...])`)?
- With `exchange` set, check the `routing_key` pattern actually matches what
  publishers send (`orders.*` matches one segment, `#` matches all).
- With `exchange` empty, the queue only receives publishes routed to its own
  name through the default exchange.
- `rabbitmq.enabled: false` silently disables everything.

## Messages disappear when my handler raises

By design: logged and rejected without requeue. Declare the queue with a
dead-letter exchange if you need to keep and inspect failures.

## Publish raises RuntimeError: pico-rabbitmq is disabled

`rabbitmq.enabled` is false in this environment. That is loud on purpose — a
silently dropped event is worse than a crash.

## Sync publish blocks too long / times out

The stub waits for broker confirm, bounded by
`rabbitmq.publish_timeout_seconds` (default 10). Check broker reachability;
raise the timeout only if your broker is genuinely slow to confirm.

## Consumers stopped after container.shutdown()

That is the lifecycle: the connection closes and the loop stops with the
container. Keep the container alive for as long as you consume.

## Too many unacked messages pile up

Lower `rabbitmq.prefetch_count` (default 10) — it bounds in-flight messages
per channel.
