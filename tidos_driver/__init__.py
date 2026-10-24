"""TIDOS weak-model driver: code owns the loop, models do bounded steps (see driver.py)."""
from .driver import Driver, DriverResult, detect_language

__all__ = ["Driver", "DriverResult", "detect_language"]
__version__ = "0.1.0"
