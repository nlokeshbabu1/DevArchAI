"""File loader utility for parsing infrastructure files."""

from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger
from app.parsers.base import ParsedFile, ParserRegistry
from app.parsers.cicd import CICDParser
from app.parsers.dockerfile import DockerfileParser
from app.parsers.kubernetes import KubernetesParser
from app.parsers.terraform import TerraformParser

logger = get_logger(__name__)


class FileLoader:
    """Utility for loading and parsing infrastructure files."""

    def __init__(self):
        self.parser_registry = self._setup_parsers()

    def _setup_parsers(self) -> ParserRegistry:
        """Initialize and register all parsers."""
        registry = ParserRegistry()
        registry.register(TerraformParser())
        registry.register(KubernetesParser())
        registry.register(DockerfileParser())
        registry.register(CICDParser())
        return registry

    def load_file(self, file_path: Path) -> Optional[ParsedFile]:
        """
        Load and parse a single file.

        Args:
            file_path: Path to the file

        Returns:
            ParsedFile or None if parsing failed
        """
        try:
            if not file_path.exists():
                logger.warning("File does not exist", path=str(file_path))
                return None

            if not file_path.is_file():
                logger.warning("Path is not a file", path=str(file_path))
                return None

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Get appropriate parser
            parser = self.parser_registry.get_parser(file_path)
            if not parser:
                logger.debug("No parser available for file", path=str(file_path))
                return None

            # Parse the file
            parsed = parser.parse(file_path, content)

            logger.debug(
                "File parsed successfully",
                path=str(file_path),
                file_type=parsed.file_type,
                line_count=parsed.line_count,
            )

            return parsed

        except UnicodeDecodeError as e:
            logger.warning(
                "Failed to decode file (not UTF-8)",
                path=str(file_path),
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to parse file",
                path=str(file_path),
                error=str(e),
            )
            return None

    def load_directory(
        self,
        directory: Path,
        file_types: Optional[list[str]] = None,
        max_depth: int = 10,
    ) -> list[ParsedFile]:
        """
        Load and parse all supported files in a directory.

        Args:
            directory: Directory to scan
            file_types: Optional filter for specific file types
            max_depth: Maximum directory depth to scan

        Returns:
            List of parsed files
        """
        parsed_files = []

        if not directory.exists() or not directory.is_dir():
            logger.warning("Directory does not exist", path=str(directory))
            return parsed_files

        logger.info("Scanning directory for files", path=str(directory))

        # Calculate max depth
        base_depth = len(directory.parts)

        for file_path in directory.rglob("*"):
            # Check depth
            current_depth = len(file_path.parts) - base_depth
            if current_depth > max_depth:
                continue

            if not file_path.is_file():
                continue

            # Parse the file
            parsed = self.load_file(file_path)
            if parsed:
                # Filter by file type if specified
                if file_types and parsed.file_type not in file_types:
                    continue

                parsed_files.append(parsed)

        logger.info(
            "Directory scan complete",
            path=str(directory),
            files_found=len(parsed_files),
        )

        return parsed_files

    def load_files(
        self,
        paths: list[Path],
    ) -> list[ParsedFile]:
        """
        Load and parse multiple files.

        Args:
            paths: List of file paths

        Returns:
            List of parsed files
        """
        parsed_files = []

        for path in paths:
            parsed = self.load_file(path)
            if parsed:
                parsed_files.append(parsed)

        return parsed_files

    def get_file_type(self, file_path: Path) -> Optional[str]:
        """
        Get the file type for a given path.

        Args:
            file_path: Path to the file

        Returns:
            File type string or None
        """
        parser = self.parser_registry.get_parser(file_path)
        if parser:
            # Get file type from parser class name
            class_name = parser.__class__.__name__
            return class_name.replace("Parser", "").lower()
        return None

    def extract_resources(self, parsed_files: list[ParsedFile]) -> list[dict[str, Any]]:
        """
        Extract resources from parsed files for rule evaluation.

        Args:
            parsed_files: List of parsed files

        Returns:
            List of resource dictionaries
        """
        all_resources = []

        for parsed_file in parsed_files:
            parser = self.parser_registry.get_parser(Path(parsed_file.file_path))
            if parser:
                resources = parser.extract_resources(parsed_file.parsed_data)

                # Add file metadata to each resource
                for resource in resources:
                    resource["file_path"] = parsed_file.file_path
                    resource["file_type"] = parsed_file.file_type

                all_resources.extend(resources)

        logger.debug(
            "Resources extracted",
            files_count=len(parsed_files),
            resources_count=len(all_resources),
        )

        return all_resources

    def get_supported_file_types(self) -> list[str]:
        """Get list of supported file types."""
        return ["terraform", "kubernetes", "dockerfile", "cicd"]

    def count_by_type(self, parsed_files: list[ParsedFile]) -> dict[str, int]:
        """Count parsed files by type."""
        counts: dict[str, int] = {}
        for parsed_file in parsed_files:
            file_type = parsed_file.file_type
            counts[file_type] = counts.get(file_type, 0) + 1
        return counts
