from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.generate_weekly_report import WeeklyReportData


def format_weekly_markdown(data: WeeklyReportData) -> str:
    sections: list[str] = []

    # Header
    sections.append("# Weekly Competitor Hiring Report")
    sections.append(f"**{data.start_date.strftime('%b %d')}–{data.end_date.strftime('%b %d, %Y')}**")

    # Headline Numbers
    stats = data.stats
    lines = [
        "",
        "## Headline Numbers",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total active | {stats.total_active_jobs} |",
        f"| New postings | +{stats.total_new} |",
        f"| Removed | -{stats.total_removed} |",
        f"| Net change | {stats.total_net_change:+d} |",
    ]
    wow_companies = [c for c in stats.companies if c.active_jobs_7d_ago is not None]
    if wow_companies:
        total_7d_ago = sum(c.active_jobs_7d_ago for c in wow_companies)
        wow_delta = stats.total_active_jobs - total_7d_ago
        lines.append(f"| vs last week | {wow_delta:+d} |")
    sections.append("\n".join(lines))

    # Strategic Signals
    if data.signals:
        lines = ["", "## Strategic Signals"]
        for s in data.signals:
            lines.append(f"- **[{s.severity}]** {s.signal}")
        sections.append("\n".join(lines))

    # Top Movers
    if data.movers:
        lines = [
            "",
            "## Top Movers",
            "| Company | Active | Change | Trend |",
            "|---------|--------|--------|-------|",
        ]
        for c in data.movers:
            annotation = "net growth" if c.net_change > 0 else "net reduction"
            if c.wow_delta is not None:
                change_str = f"{c.wow_delta:+d} WoW"
            else:
                change_str = f"{c.net_change:+d} net"
            lines.append(f"| {c.company_name} | {c.active_jobs} | {change_str} | {annotation} |")
        sections.append("\n".join(lines))

    # What's New
    if data.new_jobs:
        lines = ["", "## What's New"]
        for company_name, jobs in sorted(data.new_jobs.items()):
            lines.append(f"**{company_name}**")
            for title, location in jobs:
                loc_str = f" — {location}" if location else ""
                lines.append(f"- {title}{loc_str}")
            lines.append("")
        sections.append("\n".join(lines))

    # What Closed
    if data.removed_jobs:
        lines = ["", "## What Closed"]
        for company_name, titles in sorted(data.removed_jobs.items()):
            lines.append(f"**{company_name}**")
            for title in titles:
                lines.append(f"- {title}")
            lines.append("")
        sections.append("\n".join(lines))

    return "\n".join(sections)
