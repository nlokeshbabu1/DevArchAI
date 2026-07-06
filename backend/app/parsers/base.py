"""
Base Parser Interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ParsedFile:
    """Represents a parsed file with its content and metadata."""

    file_path: str
    file_type: str
    raw_content: str
    parsed_data: dict[str, Any]
    line_count: int
    parse_errors: list[str]


class BaseParser(ABC):
    """Abstract base class for all file parsers."""

    def __init__(self):
        self.supported_extensions: list[str] = []

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass

    @abstractmethod
    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse the file content and return structured data."""
        pass

    @abstractmethod
    def extract_resources(self, parsed_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract relevant resources from parsed data for rule evaluation."""
        pass


class ParserRegistry:
    """Registry for file parsers."""

    def __init__(self):
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser) -> None:
        """Register a parser."""
        self._parsers.append(parser)

    def get_parser(self, file_path: Path) -> BaseParser | None:
        """Get appropriate parser for a file."""
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def parse_file(self, file_path: Path, content: str) -> ParsedFile | None:
        """Parse a file using the appropriate parser."""
        parser = self.get_parser(file_path)
        if parser:
            return parser.parse(file_path, content)
        return None
