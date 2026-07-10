"""Settings for pico-rabbitmq (prefix ``rabbitmq``, zero-config)."""

from dataclasses import dataclass

from pico_ioc import configured


@configured(target="self", prefix="rabbitmq", mapping="tree")
@dataclass
class RabbitSettings:
    """``enabled: false`` disables consumers and publishers entirely."""

    url: str = "amqp://guest:guest@localhost/"
    enabled: bool = True
    prefetch_count: int = 10
    publish_timeout_seconds: float = 10.0
