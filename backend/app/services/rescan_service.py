"""Re-scan service for verifying fixes."""

import structlog

from app.models.ai_suggestion import SuggestionStatus
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus

logger = structlog.get_logger(__name__)


class RescanService:
    """Service for re-scanning repositories after fixes are applied."""

    def __init__(self, db_session):
        self.db = db_session

    async def trigger_rescan(self, scan: Scan) -> dict:
        """
        Trigger a re-scan of the repository.

        Args:
            scan: The scan object to re-scan

        Returns:
            Dict with re-scan status and task ID
        """
        try:
            # Update scan status to pending
            scan.status = ScanStatus.PENDING
            scan.progress = 0
            await self.db.commit()

            # In production, this would trigger a Celery task
            # For now, return mock data
            return {
                "success": True,
                "message": "Re-scan initiated successfully",
                "scan_id": str(scan.id),
                "task_id": f"rescan-{scan.id}",
            }
        except Exception as e:
            logger.error(f"Re-scan trigger failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to trigger re-scan",
            }

    async def compare_findings(
        self,
        old_scan: Scan,
        new_scan: Scan,
    ) -> dict:
        """
        Compare findings between old and new scans.

        Args:
            old_scan: Original scan with issues
            new_scan: New scan after fixes

        Returns:
            Dict with comparison results
        """
        try:
            old_findings = old_scan.findings
            new_findings = new_scan.findings

            # Create sets of finding signatures for comparison
            old_signatures = {
                self._create_finding_signature(f) for f in old_findings
            }
            new_signatures = {
                self._create_finding_signature(f) for f in new_findings
            }

            # Find resolved and new issues
            resolved_signatures = old_signatures - new_signatures
            new_issue_signatures = new_signatures - old_signatures
            persistent_signatures = old_signatures & new_signatures

            return {
                "success": True,
                "total_old_findings": len(old_findings),
                "total_new_findings": len(new_findings),
                "resolved_count": len(resolved_signatures),
                "new_issues_count": len(new_issue_signatures),
                "persistent_count": len(persistent_signatures),
                "resolved_signatures": list(resolved_signatures),
                "new_issue_signatures": list(new_issue_signatures),
            }
        except Exception as e:
            logger.error(f"Finding comparison failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to compare findings",
            }

    def _create_finding_signature(self, finding: Finding) -> str:
        """Create a unique signature for a finding."""
        return f"{finding.rule_id}:{finding.file_path}:{finding.line_number}:{finding.severity.value}"

    async def update_suggestion_statuses(
        self,
        scan: Scan,
        resolved_signatures: list,
    ) -> dict:
        """
        Update AI suggestion statuses based on re-scan results.

        Args:
            scan: The new scan object
            resolved_signatures: List of resolved finding signatures

        Returns:
            Dict with update results
        """
        try:
            updated_count = 0

            for finding in scan.findings:
                signature = self._create_finding_signature(finding)
                
                if signature in resolved_signatures:
                    # Update associated suggestions to FIXED
                    for suggestion in finding.ai_suggestions:
                        if suggestion.status == SuggestionStatus.IN_PROGRESS:
                            suggestion.status = SuggestionStatus.FIXED
                            updated_count += 1

            await self.db.commit()

            return {
                "success": True,
                "updated_count": updated_count,
                "message": f"Updated {updated_count} suggestion(s) to FIXED",
            }
        except Exception as e:
            logger.error(f"Status update failed: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update suggestion statuses",
            }

    async def process_rescan_results(
        self,
        old_scan_id: str,
        new_scan_id: str,
        suggestion_id: str,
    ) -> dict:
        """
        Process re-scan results and update suggestion status.

        Args:
            old_scan_id: Original scan ID
            new_scan_id: New scan ID after fix
            suggestion_id: The suggestion being verified

        Returns:
            Dict with processing results
        """
        try:
            # Load scans
            from sqlalchemy import select
            from app.models.scan import Scan
            
            old_scan_result = await self.db.execute(
                select(Scan).where(Scan.id == old_scan_id)
            )
            old_scan = old_scan_result.scalar_one_or_none()
            
            new_scan_result = await self.db.execute(
                select(Scan).where(Scan.id == new_scan_id)
            )
            new_scan = new_scan_result.scalar_one_or_none()

            if not old_scan or not new_scan:
                return {
                    "success": False,
                    "error": "Scan not found",
                }

            # Compare findings
            comparison = await self.compare_findings(old_scan, new_scan)
            
            if not comparison["success"]:
                return comparison

            # Update suggestion statuses
            update_result = await self.update_suggestion_statuses(
                new_scan,
                comparison["resolved_signatures"],
            )

            logger.info(
                "Re-scan processed",
                extra={
                    "old_scan": old_scan_id,
                    "new_scan": new_scan_id,
                    "suggestion": suggestion_id,
                    "resolved": comparison["resolved_count"],
                    "new_issues": comparison["new_issues_count"],
                },
            )

            return {
                "success": True,
                "comparison": comparison,
                "update_result": update_result,
                "message": "Re-scan processed successfully",
            }
        except Exception as e:
            logger.error(f"Re-scan processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process re-scan results",
            }


def get_rescan_service(db_session):
    """Get the re-scan service."""
    return RescanService(db_session)
