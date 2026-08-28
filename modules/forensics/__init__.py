"""Forensics module — owns §3 (`forensics`) and §4 (`metadata`)."""

from .analyzer import analyze
from .metadata import extract_metadata

__all__ = ["analyze", "extract_metadata"]
