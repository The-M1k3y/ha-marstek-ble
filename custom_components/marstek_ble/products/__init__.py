"""Product-specific data, packet, and entity definitions."""

from .jupiter import JUPITER_PROFILE, JupiterData, JupiterPackets
from .venus import VENUS_PROFILE, VenusData, VenusPackets

__all__ = [
    "JUPITER_PROFILE",
    "VENUS_PROFILE",
    "JupiterData",
    "JupiterPackets",
    "VenusData",
    "VenusPackets",
]
