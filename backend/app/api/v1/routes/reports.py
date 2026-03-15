"""Report routes."""


from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.report import (
    ReportListResponse,
    ReportResponse,
    ReportSummary,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports for the current user."""
    offset = (page - 1) * page_size

    # Get reports joined with scans to filter by user
    query = (
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    reports = result.scalars().all()

    # Get total count
    count_query = (
        select(func.count(Report.id))
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.user_id == current_user.id)
    )
    total = await db.scalar(count_query)

    return ReportListResponse(
        reports=[ReportResponse.model_validate(report) for report in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    format: str = Query(default="json", regex="^(json|csv|pdf|xlsx)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a report in JSON, CSV, PDF, or Excel format."""
    # Get report
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Get findings
    findings_result = await db.execute(
        select(Finding).where(Finding.scan_id == report.scan_id)
    )
    findings = findings_result.scalars().all()

    if format == "json":
        # Build complete JSON report
        report_data = {
            "report": {
                "id": report.id,
                "scan_id": report.scan_id,
                "repository_name": report.repository_name,
                "repository_url": report.repository_url,
                "commit_hash": report.commit_hash,
                "created_at": report.created_at.isoformat(),
                "overall_score": report.overall_score,
                "category_scores": report.category_scores,
                "executive_summary": report.executive_summary,
                "risk_analysis": report.risk_analysis,
                "prioritized_recommendations": report.prioritized_recommendations,
                "summary": {
                    "total_findings": report.total_findings,
                    "critical": report.critical_count,
                    "high": report.high_count,
                    "medium": report.medium_count,
                    "low": report.low_count,
                    "info": report.info_count,
                },
                "files_analyzed": report.files_analyzed,
            },
            "findings": [
                {
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.value,
                    "category": f.category.value,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "ai_explanation": f.ai_explanation,
                    "impact_analysis": f.impact_analysis,
                }
                for f in findings
            ],
        }

        return JSONResponse(
            content=report_data,
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.json"'
            },
        )

    elif format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Rule ID",
            "Rule Name",
            "Severity",
            "Category",
            "Description",
            "Recommendation",
            "File Path",
            "Line Number",
        ])

        # Rows
        for finding in findings:
            writer.writerow([
                finding.rule_id,
                finding.rule_name,
                finding.severity.value,
                finding.category.value,
                finding.description,
                finding.recommendation,
                finding.file_path or "",
                finding.line_number or "",
            ])

        return JSONResponse(
            content={"csv": output.getvalue()},
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.csv"'
            },
        )

    elif format == "xlsx":
        # Excel export using openpyxl
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        wb = Workbook()
        
        # Summary Sheet
        ws_summary = wb.active
        ws_summary.title = "Summary"
        
        # Styles
        header_font = Font(bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        title_font = Font(bold=True, size=14)
        cell_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        
        # Summary data
        ws_summary["A1"] = "DevArchAI Security Report"
        ws_summary["A1"].font = Font(bold=True, size=16)
        ws_summary["A2"] = f"Repository: {report.repository_name}"
        ws_summary["A3"] = f"Scan Date: {report.created_at.strftime('%Y-%m-%d %H:%M')}"
        ws_summary["A4"] = f"Overall Score: {report.overall_score}/100"
        
        # Findings summary
        ws_summary["A6"] = "Findings Summary"
        ws_summary["A6"].font = title_font
        ws_summary["A7"] = "Critical"
        ws_summary["B7"] = report.critical_count
        ws_summary["A8"] = "High"
        ws_summary["B8"] = report.high_count
        ws_summary["A9"] = "Medium"
        ws_summary["B9"] = report.medium_count
        ws_summary["A10"] = "Low"
        ws_summary["B10"] = report.low_count
        ws_summary["A11"] = "Info"
        ws_summary["B11"] = report.info_count
        ws_summary["A12"] = "Total"
        ws_summary["B12"] = report.total_findings
        ws_summary["B12"].font = Font(bold=True)
        
        # Findings Sheet
        ws_findings = wb.create_sheet(title="Findings")
        
        # Headers
        headers = ["Severity", "Rule ID", "Rule Name", "Category", "Description", "File", "Line"]
        for col, header in enumerate(headers, 1):
            cell = ws_findings.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = cell_alignment
        
        # Data rows
        severity_colors = {
            "critical": "FF4444",
            "high": "FF8C42",
            "medium": "FFD93D",
            "low": "6BCB77",
            "info": "4D96FF",
        }
        
        for row_idx, finding in enumerate(findings, 2):
            ws_findings.cell(row=row_idx, column=1, value=finding.severity.value.upper())
            ws_findings.cell(row=row_idx, column=2, value=finding.rule_id)
            ws_findings.cell(row=row_idx, column=3, value=finding.rule_name)
            ws_findings.cell(row=row_idx, column=4, value=finding.category.value)
            ws_findings.cell(row=row_idx, column=5, value=finding.description)
            ws_findings.cell(row=row_idx, column=6, value=finding.file_path or "")
            ws_findings.cell(row=row_idx, column=7, value=finding.line_number or "")
            
            # Color code severity
            severity_cell = ws_findings.cell(row=row_idx, column=1)
            severity_fill = PatternFill(
                start_color=severity_colors.get(finding.severity.value, "CCCCCC"),
                end_color=severity_colors.get(finding.severity.value, "CCCCCC"),
                fill_type="solid"
            )
            severity_cell.fill = severity_fill
            severity_cell.font = Font(bold=True, color="FFFFFF")
        
        # Adjust column widths
        for col in ws_findings.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws_findings.column_dimensions[column].width = adjusted_width
        
        # Save to buffer
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.xlsx"'
            },
        )

    elif format == "pdf":
        # PDF export using reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#4F46E5'),
            spaceAfter=12,
            alignment=TA_CENTER,
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1F2937'),
            spaceAfter=10,
            spaceBefore=12,
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
        )

        # Title
        elements.append(Paragraph("DevArchAI Security Report", title_style))
        elements.append(Spacer(1, 0.2*inch))

        # Report info
        elements.append(Paragraph(f"<b>Repository:</b> {report.repository_name}", normal_style))
        elements.append(Paragraph(f"<b>Scan Date:</b> {report.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Paragraph(f"<b>Overall Score:</b> {report.overall_score}/100", normal_style))
        elements.append(Spacer(1, 0.3*inch))

        # Executive Summary
        if report.executive_summary:
            elements.append(Paragraph("Executive Summary", heading_style))
            elements.append(Paragraph(report.executive_summary, normal_style))
            elements.append(Spacer(1, 0.3*inch))

        # Findings Summary Table
        elements.append(Paragraph("Findings Summary", heading_style))
        summary_data = [
            ["Severity", "Count"],
            ["Critical", str(report.critical_count)],
            ["High", str(report.high_count)],
            ["Medium", str(report.medium_count)],
            ["Low", str(report.low_count)],
            ["Info", str(report.info_count)],
            ["<b>Total</b>", f"<b>{report.total_findings}</b>"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#FF444420'), colors.HexColor('#FF8C4220'), colors.HexColor('#FFD93D20'), colors.HexColor('#6BCB7720'), colors.HexColor('#4D96FF20')]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))

        # Findings Detail
        elements.append(Paragraph("Detailed Findings", heading_style))
        
        for idx, finding in enumerate(findings[:20], 1):  # Limit to 20 findings for PDF
            severity_color = {
                "critical": "#FF4444",
                "high": "#FF8C42",
                "medium": "#FFD93D",
                "low": "#6BCB77",
                "info": "#4D96FF",
            }.get(finding.severity.value, "#CCCCCC")
            
            finding_html = f"""
            <para style="margin-bottom: 8">
                <b>{idx}. {finding.rule_name}</b><br/>
                <font color="{severity_color}"><b>{finding.severity.value.upper()}</b></font> | 
                <b>{finding.rule_id}</b> | 
                {finding.category.value}<br/>
                {finding.description}<br/>
                <b>Recommendation:</b> {finding.recommendation}<br/>
                <b>File:</b> {finding.file_path or 'N/A'}{f' (Line {finding.line_number})' if finding.line_number else ''}
            </para>
            """
            elements.append(Paragraph(finding_html, normal_style))
            elements.append(Spacer(1, 0.15*inch))
            
            if idx % 5 == 0:
                elements.append(PageBreak())

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'
            },
        )


@router.get("/{report_id}/summary", response_model=ReportSummary)
async def get_report_summary(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a brief summary of a report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportSummary(
        id=report.id,
        scan_id=report.scan_id,
        repository_name=report.repository_name,
        overall_score=report.overall_score,
        total_findings=report.total_findings,
        critical_count=report.critical_count,
        high_count=report.high_count,
        created_at=report.created_at,
    )


@router.delete("/{report_id}", response_model=MessageResponse)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Report.id == report_id, Scan.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.delete(report)
    await db.commit()

    return MessageResponse(message="Report deleted successfully")


@router.get("/scan/{scan_id}/latest", response_model=ReportResponse)
async def get_latest_report_for_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest report for a scan."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .where(Scan.id == scan_id, Scan.user_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found for this scan",
        )

    return report
