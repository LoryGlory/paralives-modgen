"""Paralives mod generator — parse, manipulate, and emit .setting files."""

from .parser import parse, ParseError, FieldList
from .serializer import serialize
from .guid import new_guid

__all__ = ["parse", "serialize", "new_guid", "ParseError", "FieldList"]
__version__ = "0.2.0"
