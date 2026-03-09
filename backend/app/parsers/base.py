"""
Base Parser Interface
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ParsedFile:
    """Represents a parsed file with its content and metadata."""
    
    file_path: str
    file_type: str
    raw_content: str
    parsed_data: Dict[str, Any]
    line_count: int
    parse_errors: List[str]


class BaseParser(ABC):
    """Abstract base class for all file parsers."""
    
    def __init__(self):
        self.supported_extensions: List[str] = []
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    def parse(self, file_path: Path, content: str) -> ParsedFile:
        """Parse the file content and return structured data."""
        pass
    
    @abstractmethod
    def extract_resources(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract relevant resources from parsed data for rule evaluation."""
        pass


class ParserRegistry:
    """Registry for file parsers."""
    
    def __init__(self):
        self._parsers: List[BaseParser] = []
    
    def register(self, parser: BaseParser) -> None:
        """Register a parser."""
        self._parsers.append(parser)
    
    def get_parser(self, file_path: Path) -> Optional[BaseParser]:
        """Get appropriate parser for a file."""
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        return None
    
    def parse_file(self, file_path: Path, content: str) -> Optional[ParsedFile]:
        """Parse a file using the appropriate parser."""
        parser = self.get_parser(file_path)
        if parser:
            return parser.parse(file_path, content)
        return None
