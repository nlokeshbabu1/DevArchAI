"""Production-grade PDF and Excel generators for DevArchAI reports."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import settings

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN_X = 0.55 * inch
PAGE_MARGIN_TOP = 0.65 * inch
PAGE_MARGIN_BOTTOM = 0.75 * inch
CONTENT_WIDTH = PAGE_WIDTH - (PAGE_MARGIN_X * 2)

PALETTE = {
    "ink": colors.HexColor("#0F172A"),
    "text": colors.HexColor("#1E293B"),
    "muted": colors.HexColor("#64748B"),
    "border": colors.HexColor("#CBD5E1"),
    "panel": colors.HexColor("#F8FAFC"),
    "panel_alt": colors.HexColor("#F1F5F9"),
    "brand": colors.HexColor("#0F4C81"),
    "brand_soft": colors.HexColor("#E8F1FA"),
    "critical": colors.HexColor("#B42318"),
    "critical_soft": colors.HexColor("#FEE4E2"),
    "high": colors.HexColor("#C2410C"),
    "high_soft": colors.HexColor("#FFEDD5"),
    "medium": colors.HexColor("#CA8A04"),
    "medium_soft": colors.HexColor("#FEF3C7"),
    "low": colors.HexColor("#15803D"),
    "low_soft": colors.HexColor("#DCFCE7"),
    "info": colors.HexColor("#475569"),
    "info_soft": colors.HexColor("#E2E8F0"),
}

EXAMPLE_SCAN_DATA: dict[str, Any] = {
    "user_id": "2e9ef9ab-96d8-44f5-9a39-efdd33b091ef",
    "scan_id": "a3ac1eb4-5d74-4e34-8c18-b0c2ee70e408",
    "project_name": "acme/payments-platform",
    "repository_name": "acme/payments-platform",
    "repository_url": "https://github.com/acme/payments-platform",
    "generated_at": "2026-05-02T08:30:00+00:00",
    "overall_score": 71.4,
    "category_scores": {
        "security": 62,
        "reliability": 78,
        "scalability": 74,
        "cost": 81,
        "observability": 69,
    },
    "executive_summary": (
        "The repository has a workable operational baseline, but several security "
        "controls and deployment safeguards need remediation before broad rollout."
    ),
    "risk_analysis": (
        "Critical public exposure and weak container runtime controls create the "
        "highest deployment risk. CI enforcement gaps increase regression risk."
    ),
    "prioritized_recommendations": [
        "Restrict public network exposure in Terraform security groups and load balancers.",
        "Add a non-root container user and tighten Kubernetes security contexts.",
        "Enforce dependency and IaC scanning in CI before merge.",
        "Pin mutable image and action versions to approved digests or tags.",
    ],
    "summary": {
        "total_findings": 6,
        "critical": 1,
        "high": 2,
        "medium": 2,
        "low": 1,
        "info": 0,
    },
    "findings": [
        {
            "id": "F-001",
            "rule_id": "TF-017",
            "rule_name": "Terraform security group allows unrestricted ingress",
            "severity": "critical",
            "category": "security",
            "description": "An ingress rule allows 0.0.0.0/0 access to a sensitive service port.",
            "recommendation": "Restrict ingress CIDRs and expose the service only through approved networks.",
            "impact": "Attackers can directly reach the workload from the public internet.",
            "file_path": "infrastructure/terraform/network.tf",
            "line_number": 42,
        },
        {
            "id": "F-002",
            "rule_id": "DOCKER-004",
            "rule_name": "Container runs as root",
            "severity": "high",
            "category": "security",
            "description": "The container image does not switch to a non-root user.",
            "recommendation": "Create and use a least-privilege runtime user in the Dockerfile.",
            "impact": "Runtime escape or compromise has a larger blast radius.",
            "file_path": "Dockerfile",
            "line_number": 19,
        },
        {
            "id": "F-003",
            "rule_id": "CICD-011",
            "rule_name": "CI pipeline missing security scan gate",
            "severity": "high",
            "category": "reliability",
            "description": "The pipeline builds and deploys without dependency or IaC security checks.",
            "recommendation": "Add blocking security scan stages before merge and deployment.",
            "impact": "High-risk changes can reach production without policy enforcement.",
            "file_path": ".github/workflows/deploy.yml",
            "line_number": 11,
        },
    ],
}


def generate_pdf_report(scan_data: dict[str, Any]) -> str:
    """Generate the DevArchAI PDF report locally and return the file path."""
    report_data = _normalize_report_data(scan_data)
    output_path = _build_local_report_path(report_data)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=PAGE_MARGIN_X,
        rightMargin=PAGE_MARGIN_X,
        topMargin=PAGE_MARGIN_TOP,
        bottomMargin=PAGE_MARGIN_BOTTOM,
        title="DevArchAI Scan Report",
        author="DevArchAI",
    )
    styles = _build_styles()

    story: list[Any] = []
    story.extend(_build_cover_page(report_data, styles))
    story.append(PageBreak())
    story.extend(_build_executive_summary_section(report_data, styles))
    story.extend(_build_score_breakdown_section(report_data, styles))
    story.append(PageBreak())
    story.extend(_build_findings_section(report_data, styles))
    story.extend(_build_top_critical_issues_section(report_data, styles))
    story.extend(_build_infrastructure_insights_section(report_data, styles))
    story.extend(_build_recommendations_section(report_data, styles))

    footer_timestamp = report_data["generated_at_display"]

    def _draw_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(PALETTE["border"])
        canvas.line(doc.leftMargin, 28, PAGE_WIDTH - doc.rightMargin, 28)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(PALETTE["muted"])
        canvas.drawString(doc.leftMargin, 16, f"Generated by DevArchAI | {footer_timestamp}")
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 16, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return str(output_path)


def generate_excel_report(scan_data: dict[str, Any]) -> bytes:
    """Generate an Excel workbook with summary and tabular findings."""
    report_data = _normalize_report_data(scan_data)
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    findings_sheet = workbook.create_sheet("Findings")

    header_fill = PatternFill(start_color="0F4C81", end_color="0F4C81", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    wrap_alignment = Alignment(vertical="top", wrap_text=True)

    summary_rows = [
        ("Project", report_data["project_name"]),
        ("Repository URL", report_data["repository_url"]),
        ("Scan ID", report_data["scan_id"]),
        ("Generated", report_data["generated_at_display"]),
        ("Overall Score", report_data["overall_score_display"]),
        ("Status", report_data["status"]),
        ("Executive Summary", report_data["executive_summary"]),
        ("Risk Analysis", report_data["risk_analysis"]),
    ]
    summary_rows.extend(
        (label, value)
        for label, value in [
            ("Total Issues", report_data["summary"]["total_findings"]),
            ("Critical", report_data["summary"]["critical"]),
            ("High", report_data["summary"]["high"]),
            ("Medium", report_data["summary"]["medium"]),
            ("Low", report_data["summary"]["low"]),
            ("Info", report_data["summary"]["info"]),
        ]
    )

    for row_index, (label, value) in enumerate(summary_rows, start=1):
        summary_sheet.cell(row=row_index, column=1, value=label).font = Font(bold=True)
        summary_sheet.cell(row=row_index, column=2, value=_truncate_excel_value(value))
        summary_sheet.cell(row=row_index, column=2).alignment = wrap_alignment

    headers = [
        "ID",
        "Severity",
        "Title",
        "Category",
        "File Path",
        "Description",
        "Recommendation",
        "Impact",
    ]
    for column, header in enumerate(headers, start=1):
        cell = findings_sheet.cell(row=1, column=column, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = wrap_alignment

    for row_index, finding in enumerate(report_data["findings"], start=2):
        findings_sheet.cell(row=row_index, column=1, value=_truncate_excel_value(finding["id"]))
        findings_sheet.cell(row=row_index, column=2, value=_truncate_excel_value(finding["severity_label"]))
        findings_sheet.cell(row=row_index, column=3, value=_truncate_excel_value(finding["title"]))
        findings_sheet.cell(row=row_index, column=4, value=_truncate_excel_value(finding["category_label"]))
        findings_sheet.cell(row=row_index, column=5, value=_truncate_excel_value(finding["file_path"]))
        findings_sheet.cell(row=row_index, column=6, value=_truncate_excel_value(finding["description"]))
        findings_sheet.cell(row=row_index, column=7, value=_truncate_excel_value(finding["recommendation"]))
        findings_sheet.cell(row=row_index, column=8, value=_truncate_excel_value(finding["impact"]))
        for column in range(1, 9):
            findings_sheet.cell(row=row_index, column=column).alignment = wrap_alignment

    for sheet in (summary_sheet, findings_sheet):
        for column_cells in sheet.columns:
            column_letter = column_cells[0].column_letter
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 14), 48)

    from io import BytesIO

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _build_cover_page(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    metadata_table = Table(
        [
            [_kv("Project", report_data["project_name"], styles), _kv("Date", report_data["date_display"], styles)],
            [_kv("Repository URL", _wrap_path(report_data["repository_url"]), styles), _kv("Scan ID", report_data["scan_id"], styles)],
            [_kv("Status", report_data["status"], styles), _kv("Generated At", report_data["generated_at_display"], styles)],
        ],
        colWidths=[CONTENT_WIDTH * 0.60, CONTENT_WIDTH * 0.40],
    )
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["panel"]),
                ("BOX", (0, 0), (-1, -1), 0.75, PALETTE["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, PALETTE["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    score_card = Table(
        [
            [Paragraph("Overall Score", styles["CardLabel"])],
            [Paragraph(report_data["overall_score_display"], styles["ScoreValue"])],
            [Paragraph(report_data["status"], styles["StatusBadge"])],
        ],
        colWidths=[CONTENT_WIDTH * 0.30],
    )
    score_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), report_data["status_soft_color"]),
                ("BOX", (0, 0), (-1, -1), 1, report_data["status_color"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )

    hero_table = Table(
        [[metadata_table, score_card]],
        colWidths=[CONTENT_WIDTH * 0.68, CONTENT_WIDTH * 0.32],
    )
    hero_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        Spacer(1, 0.45 * inch),
        Paragraph("DevArchAI Scan Report", styles["ReportTitle"]),
        Paragraph("Enterprise DevOps and security posture assessment", styles["Subtitle"]),
        Spacer(1, 0.25 * inch),
        hero_table,
        Spacer(1, 0.28 * inch),
        _build_summary_metrics_table(report_data, styles),
        Spacer(1, 0.24 * inch),
        _build_cover_overview_panel(report_data, styles),
    ]


def _build_executive_summary_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    story = [_section_heading("Executive Summary", styles)]
    story.append(Paragraph(escape(report_data["executive_summary"]), styles["Body"]))
    story.append(Spacer(1, 0.14 * inch))
    story.append(_build_summary_metrics_table(report_data, styles))
    story.append(Spacer(1, 0.18 * inch))
    story.append(_subsection_heading("Key Risks", styles))
    story.extend(_build_bullets(report_data["key_risks"], styles))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_subsection_heading("Recommendations Summary", styles))
    story.extend(_build_bullets(report_data["recommendations_summary"], styles))
    story.append(Spacer(1, 0.1 * inch))
    return story


def _build_score_breakdown_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    data: list[list[Any]] = [
        [
            Paragraph("Category", styles["TableHeader"]),
            Paragraph("Score", styles["TableHeader"]),
            Paragraph("Assessment", styles["TableHeader"]),
        ]
    ]

    for category in report_data["score_breakdown"]:
        data.append(
            [
                Paragraph(category["label"], styles["TableCell"]),
                Paragraph(category["score_display"], styles["TableCellStrong"]),
                Paragraph(category["assessment"], styles["TableCell"]),
            ]
        )

    table = Table(data, colWidths=[CONTENT_WIDTH * 0.42, CONTENT_WIDTH * 0.18, CONTENT_WIDTH * 0.40])
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["brand"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, PALETTE["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row_index, category in enumerate(report_data["score_breakdown"], start=1):
        table_style.extend(
            [
                ("BACKGROUND", (0, row_index), (-1, row_index), category["soft_color"]),
                ("TEXTCOLOR", (1, row_index), (1, row_index), category["color"]),
            ]
        )
    table.setStyle(TableStyle(table_style))

    story = [_section_heading("Security Score Breakdown", styles)]
    story.append(Paragraph("Overall posture is scored out of 100 across the core operating dimensions below.", styles["Body"]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(table)
    if report_data.get("observability_score_display"):
        story.append(Spacer(1, 0.1 * inch))
        story.append(
            Paragraph(
                f"Operational observability score: {report_data['observability_score_display']}.",
                styles["SmallMuted"],
            )
        )
    story.append(Spacer(1, 0.14 * inch))
    return story


def _build_findings_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    story = [_section_heading("Findings Table", styles)]
    findings = report_data["findings"]
    if not findings:
        story.append(_build_empty_panel("No findings were detected for this scan.", styles))
        story.append(Spacer(1, 0.14 * inch))
        return story

    table_data: list[list[Any]] = [
        [
            Paragraph("ID", styles["TableHeader"]),
            Paragraph("Severity", styles["TableHeader"]),
            Paragraph("Title", styles["TableHeader"]),
            Paragraph("File Path", styles["TableHeader"]),
            Paragraph("Description", styles["TableHeader"]),
            Paragraph("Fix Recommendation", styles["TableHeader"]),
        ]
    ]
    table_style_commands: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), PALETTE["brand"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, PALETTE["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALETTE["panel"]]),
    ]

    for row_index, finding in enumerate(findings, start=1):
        table_data.append(
            [
                Paragraph(escape(finding["id"]), styles["FindingCell"]),
                Paragraph(escape(finding["severity_label"]), styles["FindingCell"]),
                Paragraph(escape(_truncate_text(finding["title"], 90)), styles["FindingCell"]),
                Paragraph(escape(_wrap_path(_truncate_text(finding["location"], 110))), styles["FindingCell"]),
                Paragraph(escape(_truncate_text(finding["description"], 220)), styles["FindingCell"]),
                Paragraph(escape(_truncate_text(finding["recommendation"], 220)), styles["FindingCell"]),
            ]
        )
        table_style_commands.extend(
            [
                ("BACKGROUND", (1, row_index), (1, row_index), finding["severity_soft_color"]),
                ("TEXTCOLOR", (1, row_index), (1, row_index), finding["severity_color"]),
            ]
        )

    table = LongTable(
        table_data,
        colWidths=[CONTENT_WIDTH * 0.09, CONTENT_WIDTH * 0.11, CONTENT_WIDTH * 0.18, CONTENT_WIDTH * 0.17, CONTENT_WIDTH * 0.22, CONTENT_WIDTH * 0.23],
        repeatRows=1,
    )
    table.setStyle(TableStyle(table_style_commands))
    story.append(table)
    story.append(Spacer(1, 0.16 * inch))
    return story


def _build_top_critical_issues_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    story = [_section_heading("Top Critical Issues", styles)]
    issues = report_data["top_critical_issues"]
    if not issues:
        story.append(_build_empty_panel("No critical issues were identified in this scan.", styles))
        story.append(Spacer(1, 0.12 * inch))
        return story

    for issue in issues:
        issue_table = Table(
            [
                [Paragraph(escape(issue["title"]), styles["IssueTitle"])],
                [
                    Paragraph(
                        f"<b>Impact:</b> {escape(issue['impact'])}<br/><br/>"
                        f"<b>Suggested fix:</b> {escape(issue['recommendation'])}<br/><br/>"
                        f"<b>Location:</b> {escape(_wrap_path(issue['location']))}",
                        styles["Body"],
                    )
                ],
            ],
            colWidths=[CONTENT_WIDTH],
        )
        issue_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), issue["severity_color"]),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.75, issue["severity_color"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(issue_table)
        story.append(Spacer(1, 0.12 * inch))
    return story


def _build_infrastructure_insights_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    story = [_section_heading("Infrastructure Insights", styles)]
    for insight in report_data["infrastructure_insights"]:
        story.append(_subsection_heading(insight["label"], styles))
        story.append(Paragraph(escape(insight["summary"]), styles["Body"]))
        story.extend(_build_bullets(insight["items"], styles))
        story.append(Spacer(1, 0.08 * inch))
    return story


def _build_recommendations_section(report_data: dict[str, Any], styles: StyleSheet1) -> list[Any]:
    story = [_section_heading("Recommendations", styles)]
    recommendations = report_data["prioritized_actions"]
    if not recommendations:
        story.append(_build_empty_panel("No additional recommendations were generated for this scan.", styles))
        return story

    table_data: list[list[Any]] = [
        [
            Paragraph("Priority", styles["TableHeader"]),
            Paragraph("Actionable Step", styles["TableHeader"]),
        ]
    ]
    for item in recommendations:
        table_data.append(
            [
                Paragraph(escape(item["priority"]), styles["FindingCell"]),
                Paragraph(escape(item["action"]), styles["FindingCell"]),
            ]
        )

    table = Table(table_data, colWidths=[CONTENT_WIDTH * 0.20, CONTENT_WIDTH * 0.80], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE["brand"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, PALETTE["border"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALETTE["panel"]]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    return story


def _normalize_report_data(scan_data: dict[str, Any]) -> dict[str, Any]:
    generated_at = _coerce_datetime(scan_data.get("generated_at"))
    repository_url = str(scan_data.get("repository_url") or "Repository URL not provided")
    repository_name = str(
        scan_data.get("project_name")
        or scan_data.get("repository_name")
        or _derive_repository_name(repository_url)
        or "Unknown Project"
    )
    user_id = str(scan_data.get("user_id") or "anonymous")
    scan_id = str(scan_data.get("scan_id") or scan_data.get("report_id") or "unknown-scan")
    findings = _normalize_findings(scan_data.get("findings") or [])
    summary = _normalize_summary(scan_data.get("summary"), findings)
    overall_score = _coerce_score(scan_data.get("overall_score"))
    status = _determine_status(overall_score, summary)
    status_color, status_soft_color = _status_colors(status)
    category_scores = _normalize_category_scores(scan_data.get("category_scores") or {})
    recommendations = _normalize_recommendations(scan_data.get("prioritized_recommendations"), findings)
    risk_analysis = _clean_sentence(
        scan_data.get("risk_analysis")
        or _default_risk_analysis(summary)
    )

    return {
        "user_id": user_id,
        "scan_id": scan_id,
        "project_name": repository_name,
        "repository_name": repository_name,
        "repository_url": repository_url,
        "generated_at": generated_at,
        "generated_at_display": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "date_display": generated_at.strftime("%B %d, %Y"),
        "overall_score": overall_score,
        "overall_score_display": f"{overall_score:.1f}/100",
        "status": status,
        "status_color": status_color,
        "status_soft_color": status_soft_color,
        "executive_summary": _clean_sentence(
            scan_data.get("executive_summary")
            or _default_executive_summary(repository_name, summary)
        ),
        "risk_analysis": risk_analysis,
        "summary": summary,
        "findings": findings,
        "recommendations_summary": recommendations,
        "score_breakdown": _build_score_breakdown(category_scores),
        "observability_score_display": (
            f"{category_scores['observability']:.1f}/100"
            if category_scores["observability"] is not None
            else None
        ),
        "key_risks": _build_key_risks(findings, risk_analysis),
        "top_critical_issues": _build_top_critical_issues(findings),
        "infrastructure_insights": _build_infrastructure_insights(findings),
        "prioritized_actions": _build_prioritized_actions(recommendations, findings),
    }


def _normalize_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, start=1):
        severity = _normalize_severity(finding.get("severity"))
        severity_color, severity_soft_color = _severity_colors(severity)
        title = str(
            finding.get("title")
            or finding.get("rule_name")
            or finding.get("summary")
            or finding.get("rule_id")
            or f"Finding {index}"
        )
        file_path = str(finding.get("file_path") or "N/A")
        line_number = finding.get("line_number")
        location = file_path if not line_number else f"{file_path}:{line_number}"
        category = _normalize_category(finding.get("category"))
        normalized.append(
            {
                "id": str(finding.get("id") or finding.get("rule_id") or f"F-{index:03d}"),
                "rule_id": str(finding.get("rule_id") or ""),
                "severity": severity,
                "severity_label": severity.title(),
                "severity_color": severity_color,
                "severity_soft_color": severity_soft_color,
                "title": _clean_sentence(title),
                "category": category,
                "category_label": category.replace("_", " ").title(),
                "description": _clean_sentence(
                    finding.get("description")
                    or finding.get("summary")
                    or "No description provided."
                ),
                "recommendation": _clean_sentence(
                    finding.get("recommendation")
                    or "Review the affected configuration and apply the recommended remediation."
                ),
                "impact": _clean_sentence(
                    finding.get("impact")
                    or finding.get("risk")
                    or finding.get("description")
                    or "Operational impact was not provided."
                ),
                "file_path": file_path,
                "line_number": line_number,
                "location": location,
            }
        )
    normalized.sort(key=lambda item: (_severity_rank(item["severity"]), item["title"]))
    return normalized


def _normalize_summary(summary: Any, findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for finding in findings:
        counts[finding["severity"]] += 1

    if isinstance(summary, dict):
        for key in counts:
            if key in summary:
                counts[key] = _coerce_int(summary.get(key))
        total = summary.get("total_findings", summary.get("total_issues"))
        counts["total_findings"] = _coerce_int(total) if total is not None else sum(counts.values())
    else:
        counts["total_findings"] = sum(counts.values())
    return counts


def _normalize_category_scores(category_scores: Any) -> dict[str, float | None]:
    values: dict[str, float] = {}
    if isinstance(category_scores, dict):
        for key, value in category_scores.items():
            values[str(key).strip().lower().replace(" ", "_")] = _coerce_score(value)
    elif isinstance(category_scores, list):
        for entry in category_scores:
            if isinstance(entry, dict) and entry.get("category") is not None:
                values[str(entry["category"]).strip().lower().replace(" ", "_")] = _coerce_score(entry.get("score"))

    performance_score = values.get("performance")
    if performance_score is None:
        performance_candidates = [values.get("scalability"), values.get("observability")]
        performance_candidates = [value for value in performance_candidates if value is not None]
        performance_score = mean(performance_candidates) if performance_candidates else None

    return {
        "security": values.get("security", 0.0),
        "reliability": values.get("reliability", 0.0),
        "performance": performance_score if performance_score is not None else 0.0,
        "cost_optimization": values.get("cost_optimization", values.get("cost", 0.0)),
        "observability": values.get("observability"),
    }


def _normalize_recommendations(recommendations: Any, findings: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    if isinstance(recommendations, list):
        items = [str(item).strip() for item in recommendations if str(item).strip()]
    if not items:
        for finding in findings:
            recommendation = finding["recommendation"]
            if recommendation not in items:
                items.append(recommendation)
            if len(items) == 5:
                break
    if not items:
        items.append("No immediate remediation actions were identified.")
    return items[:5]


def _build_score_breakdown(category_scores: dict[str, float | None]) -> list[dict[str, Any]]:
    categories = [
        ("Security", category_scores["security"]),
        ("Reliability", category_scores["reliability"]),
        ("Performance", category_scores["performance"]),
        ("Cost Optimization", category_scores["cost_optimization"]),
    ]
    breakdown: list[dict[str, Any]] = []
    for label, score in categories:
        score_value = _coerce_score(score)
        color, soft_color = _score_colors(score_value)
        breakdown.append(
            {
                "label": label,
                "score": score_value,
                "score_display": f"{score_value:.1f}/100",
                "assessment": _score_assessment(score_value),
                "color": color,
                "soft_color": soft_color,
            }
        )
    return breakdown


def _build_key_risks(findings: list[dict[str, Any]], risk_analysis: str) -> list[str]:
    risks: list[str] = []
    for finding in findings:
        risk = f"{finding['title']}: {finding['impact']}"
        if risk not in risks:
            risks.append(_truncate_text(risk, 190))
        if len(risks) == 4:
            break
    if not risks:
        risks.append(_truncate_text(risk_analysis, 190))
    return risks


def _build_top_critical_issues(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [finding for finding in findings if finding["severity"] == "critical"][:5]
    if not selected:
        selected = [finding for finding in findings if finding["severity"] == "high"][:3]
    return selected


def _build_infrastructure_insights(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [
        ("Terraform Issues", _is_terraform_finding),
        ("CI/CD Issues", _is_cicd_finding),
        ("Docker/Kubernetes Issues", _is_container_finding),
    ]
    insights: list[dict[str, Any]] = []
    for label, matcher in groups:
        matches = [finding for finding in findings if matcher(finding)]
        if matches:
            items = [
                _truncate_text(f"{finding['title']} ({finding['severity_label']}) - {finding['location']}", 150)
                for finding in matches[:3]
            ]
            summary = f"{len(matches)} issue(s) detected in this area."
        else:
            items = ["No material issues were detected in this area."]
            summary = "No findings were recorded for this segment of the stack."
        insights.append({"label": label, "summary": summary, "items": items})
    return insights


def _build_prioritized_actions(recommendations: list[str], findings: list[dict[str, Any]]) -> list[dict[str, str]]:
    priorities = ["Immediate", "Next", "Planned", "Planned", "Backlog"]
    actions = [{"priority": priorities[index], "action": recommendation} for index, recommendation in enumerate(recommendations[:5])]
    if actions:
        return actions

    if not findings:
        return []

    return [
        {
            "priority": "Immediate",
            "action": findings[0]["recommendation"],
        }
    ]


def _build_cover_overview_panel(report_data: dict[str, Any], styles: StyleSheet1) -> Table:
    data = [
        [Paragraph("Report Overview", styles["PanelHeading"])],
        [Paragraph(escape(report_data["risk_analysis"]), styles["Body"])],
    ]
    panel = Table(data, colWidths=[CONTENT_WIDTH])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE["brand_soft"]),
                ("TEXTCOLOR", (0, 0), (-1, 0), PALETTE["brand"]),
                ("BACKGROUND", (0, 1), (-1, 1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.75, PALETTE["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return panel


def _build_summary_metrics_table(report_data: dict[str, Any], styles: StyleSheet1) -> Table:
    summary = report_data["summary"]
    data = [
        [
            Paragraph("Total Issues", styles["MetricLabel"]),
            Paragraph("Critical", styles["MetricLabel"]),
            Paragraph("High", styles["MetricLabel"]),
            Paragraph("Medium", styles["MetricLabel"]),
            Paragraph("Low", styles["MetricLabel"]),
        ],
        [
            Paragraph(str(summary["total_findings"]), styles["MetricValue"]),
            Paragraph(str(summary["critical"]), styles["MetricValueCritical"]),
            Paragraph(str(summary["high"]), styles["MetricValueHigh"]),
            Paragraph(str(summary["medium"]), styles["MetricValueMedium"]),
            Paragraph(str(summary["low"]), styles["MetricValueLow"]),
        ],
    ]
    table = Table(data, colWidths=[CONTENT_WIDTH / 5.0] * 5)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PALETTE["panel_alt"]),
                ("BACKGROUND", (0, 1), (0, 1), colors.white),
                ("BACKGROUND", (1, 1), (1, 1), PALETTE["critical_soft"]),
                ("BACKGROUND", (2, 1), (2, 1), PALETTE["high_soft"]),
                ("BACKGROUND", (3, 1), (3, 1), PALETTE["medium_soft"]),
                ("BACKGROUND", (4, 1), (4, 1), PALETTE["low_soft"]),
                ("BOX", (0, 0), (-1, -1), 0.75, PALETTE["border"]),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, PALETTE["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _build_bullets(items: list[str], styles: StyleSheet1) -> list[Any]:
    return [Paragraph(f"- {escape(item)}", styles["ReportBullet"]) for item in items]


def _build_empty_panel(message: str, styles: StyleSheet1) -> Table:
    panel = Table([[Paragraph(escape(message), styles["Body"])]], colWidths=[CONTENT_WIDTH])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALETTE["panel"]),
                ("BOX", (0, 0), (-1, -1), 0.75, PALETTE["border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return panel


def _build_styles() -> StyleSheet1:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=PALETTE["ink"],
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "Subtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=PALETTE["muted"],
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=PALETTE["ink"],
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            "SubsectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=PALETTE["brand"],
            spaceBefore=4,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.2,
            textColor=PALETTE["text"],
        )
    )
    styles.add(
        ParagraphStyle(
            "ReportBullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=11.6,
            leftIndent=8,
            textColor=PALETTE["text"],
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallMuted",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.2,
            textColor=PALETTE["muted"],
        )
    )
    styles.add(
        ParagraphStyle(
            "CardLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=PALETTE["muted"],
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "ScoreValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            textColor=PALETTE["ink"],
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "StatusBadge",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=10,
            textColor=PALETTE["muted"],
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=PALETTE["ink"],
            alignment=1,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValueCritical",
            parent=styles["MetricValue"],
            textColor=PALETTE["critical"],
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValueHigh",
            parent=styles["MetricValue"],
            textColor=PALETTE["high"],
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValueMedium",
            parent=styles["MetricValue"],
            textColor=PALETTE["medium"],
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValueLow",
            parent=styles["MetricValue"],
            textColor=PALETTE["low"],
        )
    )
    styles.add(
        ParagraphStyle(
            "PanelHeading",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=12.4,
            textColor=PALETTE["brand"],
        )
    )
    styles.add(
        ParagraphStyle(
            "Label",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=10,
            textColor=PALETTE["muted"],
        )
    )
    styles.add(
        ParagraphStyle(
            "Value",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=11.5,
            textColor=PALETTE["text"],
        )
    )
    styles.add(
        ParagraphStyle(
            "TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.1,
            leading=10,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.6,
            textColor=PALETTE["text"],
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCellStrong",
            parent=styles["TableCell"],
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            "FindingCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.3,
            leading=8.8,
            textColor=PALETTE["text"],
        )
    )
    styles.add(
        ParagraphStyle(
            "IssueTitle",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10.2,
            leading=12.5,
            textColor=colors.white,
        )
    )
    return styles


def _section_heading(text: str, styles: StyleSheet1) -> Paragraph:
    return Paragraph(escape(text), styles["SectionHeading"])


def _subsection_heading(text: str, styles: StyleSheet1) -> Paragraph:
    return Paragraph(escape(text), styles["SubsectionHeading"])


def _kv(label: str, value: str, styles: StyleSheet1) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b><br/>{escape(value)}", styles["Value"])


def _build_local_report_path(report_data: dict[str, Any]) -> Path:
    safe_user = _safe_path_segment(report_data["user_id"])
    safe_scan = _safe_path_segment(report_data["scan_id"])
    return Path(settings.TEMP_DIR) / "reports" / safe_user / safe_scan / "report.pdf"


def _safe_path_segment(value: str) -> str:
    sanitized = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in str(value))
    return sanitized.strip("-") or "unknown"


def _derive_repository_name(repository_url: str) -> str:
    clean_url = repository_url.rstrip("/")
    parts = clean_url.split("/")
    if len(parts) >= 2:
        return "/".join(parts[-2:]).replace(".git", "")
    return clean_url.replace(".git", "")


def _default_executive_summary(repository_name: str, summary: dict[str, int]) -> str:
    return (
        f"{repository_name} completed with {summary['total_findings']} finding(s): "
        f"{summary['critical']} critical, {summary['high']} high, "
        f"{summary['medium']} medium, and {summary['low']} low."
    )


def _default_risk_analysis(summary: dict[str, int]) -> str:
    if summary["critical"] > 0:
        return "Critical issues were detected. Remediate those items before production deployment."
    if summary["high"] > 0:
        return "High-risk issues remain. Prioritize remediation before broad rollout."
    if summary["medium"] > 0:
        return "No blocking issues were found, but medium-risk findings should be scheduled for remediation."
    return "No material risk signals were detected in this scan."


def _determine_status(overall_score: float, summary: dict[str, int]) -> str:
    if summary["critical"] > 0 or overall_score < 50:
        return "Critical"
    if summary["high"] > 0 or overall_score < 80:
        return "Needs Attention"
    return "Secure"


def _status_colors(status: str) -> tuple[Any, Any]:
    if status == "Critical":
        return PALETTE["critical"], PALETTE["critical_soft"]
    if status == "Needs Attention":
        return PALETTE["high"], PALETTE["high_soft"]
    return PALETTE["low"], PALETTE["low_soft"]


def _score_assessment(score: float) -> str:
    if score >= 90:
        return "Strong"
    if score >= 75:
        return "Stable"
    if score >= 60:
        return "Watch"
    return "At Risk"


def _score_colors(score: float) -> tuple[Any, Any]:
    if score >= 90:
        return PALETTE["low"], PALETTE["low_soft"]
    if score >= 75:
        return PALETTE["brand"], PALETTE["brand_soft"]
    if score >= 60:
        return PALETTE["medium"], PALETTE["medium_soft"]
    return PALETTE["critical"], PALETTE["critical_soft"]


def _severity_colors(severity: str) -> tuple[Any, Any]:
    mapping = {
        "critical": (PALETTE["critical"], PALETTE["critical_soft"]),
        "high": (PALETTE["high"], PALETTE["high_soft"]),
        "medium": (PALETTE["medium"], PALETTE["medium_soft"]),
        "low": (PALETTE["low"], PALETTE["low_soft"]),
        "info": (PALETTE["info"], PALETTE["info_soft"]),
    }
    return mapping[severity]


def _normalize_severity(value: Any) -> str:
    normalized = str(value or "info").strip().lower()
    return normalized if normalized in {"critical", "high", "medium", "low", "info"} else "info"


def _normalize_category(value: Any) -> str:
    normalized = str(value or "general").strip().lower().replace(" ", "_")
    return normalized or "general"


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(severity, 5)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        candidate = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def _coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(score, 100.0))


def _coerce_int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _truncate_text(value: str, max_length: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _clean_sentence(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text or "Not provided."


def _wrap_path(value: str) -> str:
    return str(value or "").replace("/", "/ ").replace("_", "_ ")


def _is_terraform_finding(finding: dict[str, Any]) -> bool:
    path = finding["file_path"].lower()
    title = finding["title"].lower()
    return path.endswith((".tf", ".tfvars")) or "terraform" in path or "terraform" in title


def _is_cicd_finding(finding: dict[str, Any]) -> bool:
    path = finding["file_path"].lower()
    title = finding["title"].lower()
    indicators = [".github/workflows", ".gitlab-ci", "jenkinsfile", ".circleci", "azure-pipelines", "pipeline", "cicd", "ci/cd"]
    return any(indicator in path or indicator in title for indicator in indicators)


def _is_container_finding(finding: dict[str, Any]) -> bool:
    path = finding["file_path"].lower()
    title = finding["title"].lower()
    indicators = ["dockerfile", "kubernetes", "k8s", "helm", "deployment.yaml", "service.yaml", "container"]
    return any(indicator in path or indicator in title for indicator in indicators)


def _truncate_excel_value(value: Any) -> str:
    text = str(value or "")
    return text[:32767]
