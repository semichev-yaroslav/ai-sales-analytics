from __future__ import annotations

from pathlib import Path

import orjson
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ai_sales_analytics.analytics.models import DailyAnalyticsReport


class ReportWriter:
    def __init__(self, reports_root: Path):
        self.reports_root = reports_root
        self.reports_root.mkdir(parents=True, exist_ok=True)

        template_dir = Path(__file__).resolve().parent.parent / "templates"
        self.jinja = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def prepare_daily_dir(self, report_date: str) -> Path:
        path = self.reports_root / report_date
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, report: DailyAnalyticsReport, daily_dir: Path) -> Path:
        path = daily_dir / "analytics.json"
        path.write_bytes(orjson.dumps(report.model_dump(), option=orjson.OPT_INDENT_2))
        return path

    def write_html(self, report: DailyAnalyticsReport, daily_dir: Path) -> Path:
        template = self.jinja.get_template("daily_report.html")
        html = template.render(report=report.model_dump())
        path = daily_dir / "report.html"
        path.write_text(html, encoding="utf-8")
        return path
