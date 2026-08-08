"""Product-specific data, packet, entity, and runtime definitions."""

from .jupiter import JUPITER_PROFILE, JupiterData, JupiterPackets
from .venus import VENUS_PROFILE, VenusData, VenusPackets
from .venus_runtime import VENUS_RUNTIME

RUNTIME_PRODUCTS = (VENUS_RUNTIME,)


def runtime_for_id(product_id: str):
    """Return an enabled runtime product by stable product ID."""

    return next(
        (
            runtime
            for runtime in RUNTIME_PRODUCTS
            if runtime.product_id == product_id
        ),
        None,
    )


def runtime_for_name(local_name: str | None):
    """Return an enabled runtime product matching a Bluetooth local name."""

    return next(
        (
            runtime
            for runtime in RUNTIME_PRODUCTS
            if runtime.matches_name(local_name)
        ),
        None,
    )


__all__ = [
    "JUPITER_PROFILE",
    "RUNTIME_PRODUCTS",
    "VENUS_PROFILE",
    "VENUS_RUNTIME",
    "JupiterData",
    "JupiterPackets",
    "VenusData",
    "VenusPackets",
    "runtime_for_id",
    "runtime_for_name",
]
