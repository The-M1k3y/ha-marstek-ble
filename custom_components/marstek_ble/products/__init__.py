"""Enabled product runtime registry and product-specific definitions."""

# Jupiter remains deliberately outside this runtime registry until its parser and
# Home Assistant surfaces are migrated. It is still available from
# ``custom_components.marstek_ble.products.jupiter`` for declarative scaffolding.
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
    "RUNTIME_PRODUCTS",
    "VENUS_PROFILE",
    "VENUS_RUNTIME",
    "VenusData",
    "VenusPackets",
    "runtime_for_id",
    "runtime_for_name",
]
