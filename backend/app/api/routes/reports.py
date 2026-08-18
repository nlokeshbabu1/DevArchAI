"""
Report Routes
"""


from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.schemas import AnalysisReport

router = APIRouter()

# In-memory report store (use database/S3 in production)
reports_store: dict[str, AnalysisReport] = {}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get analysis report by ID."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    return reports_store[report_id]


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, format: str | None = "json"):
    """Download analysis report."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    report = reports_store[report_id]

    if format == "json":
        return JSONResponse(
            content=report.model_dump(mode="json"),
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.json"'},
        )
    elif format == "pdf":
        # PDF generation would go here
        raise HTTPException(status_code=501, detail="PDF export not yet implemented")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
