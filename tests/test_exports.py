"""The public API is exactly what ``__all__`` declares (stability contract)."""

import pico_rabbitmq


def test_public_api_is_declared_and_importable():
    assert set(pico_rabbitmq.__all__) == {"RabbitRegistrar", "RabbitSettings", "consumer", "publish", "publisher"}
    for name in pico_rabbitmq.__all__:
        assert getattr(pico_rabbitmq, name) is not None
