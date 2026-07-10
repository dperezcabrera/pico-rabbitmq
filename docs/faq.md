# FAQ

## When pico-celery and when pico-rabbitmq?

pico-celery is for tasks: one consumer per job, results, retries. pico-rabbitmq is for events: fan-out to any number of interested consumers, topic routing. They share a broker happily.

## Why are failed messages dropped instead of requeued?

Requeueing a message that deterministically fails creates an infinite hot loop. Dropping (with a logged traceback) is the safe default; declare a dead-letter exchange on the queue when you need to inspect or replay failures.

## Does it block my event loop?

No. The module runs its own loop in a daemon thread. Sync publish stubs block only the calling thread, bounded by `publish_timeout_seconds`; async stubs await without blocking.

## What is on the wire?

`application/json` bodies — `json.dumps` of the stub's `message` argument. If you need another format or per-message headers, publish through aio-pika directly; declarative stubs deliberately cover the common case only.

## How do I test my consumers?

Call the method directly with a dict — it is a plain component method. The queue plumbing is pico-rabbitmq's job, tested here.
