"""ScannerExecutionRecord model — persists per-scanner execution metadata per scan."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ScannerExecutionRecord(Base):
    """Tracks execution state and metadata for each scanner in a scan."""

    __tablename__ = "scanner_execution_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    scan_id = Column(PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)

    scanner_name = Column(String(100), nullable=False)
    scanner_id = Column(String(50), nullable=False)
    version = Column(String(50), nullable=True)

    status = Column(String(30), nullable=False, default="DISCOVERED")
    applicable = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, nullable=False, default=True)

    execution_start = Column(DateTime(timezone=True), nullable=True)
    execution_end = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    files_scanned = Column(Integer, nullable=True)
    rules_executed = Column(Integer, nullable=True)
    findings_count = Column(Integer, nullable=True, default=0)

    skipped_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan = relationship("Scan", back_populates="scanner_executions")

    def __repr__(self) -> str:
        return (
            f"<ScannerExecutionRecord(id={self.id}, scanner_id={self.scanner_id}, "
            f"status={self.status})>"
        )
