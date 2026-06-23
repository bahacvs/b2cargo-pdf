"""Perfetti Van Melle e-irsaliye bolge ayirma agenti (lokal MVP)."""

__version__ = "0.1.0"

from .parser import Document, parse_document
from .regions import RegionMap, normalize

__all__ = ["Document", "parse_document", "RegionMap", "normalize", "__version__"]
