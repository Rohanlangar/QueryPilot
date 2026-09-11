"""
QueryPilot — Visualization Suggester Tests
"""

import pytest
from app.core.viz_suggester import VizSuggester


def test_suggest_kpi_card():
    suggester = VizSuggester()
    columns = ["total_revenue"]
    rows = [{"total_revenue": 1450000}]
    result = suggester.suggest(columns, rows)
    assert result["chart_type"] == "kpi"
    assert result["y_axis"] == "total_revenue"
    assert result["config"]["value"] == 1450000


def test_suggest_time_series_line():
    suggester = VizSuggester()
    columns = ["order_date", "revenue"]
    rows = [
        {"order_date": "2026-01-01", "revenue": 12000},
        {"order_date": "2026-01-02", "revenue": 15000},
        {"order_date": "2026-01-03", "revenue": 18000},
    ]
    result = suggester.suggest(columns, rows)
    assert result["chart_type"] == "line"
    assert result["x_axis"] == "order_date"
    assert result["y_axis"] == "revenue"


def test_suggest_category_bar():
    suggester = VizSuggester()
    columns = ["department", "headcount"]
    rows = [
        {"department": "Engineering", "headcount": 55},
        {"department": "Sales", "headcount": 30},
        {"department": "Marketing", "headcount": 20},
    ]
    result = suggester.suggest(columns, rows)
    assert result["chart_type"] == "bar"
    assert result["x_axis"] == "department"
    assert result["y_axis"] == "headcount"


def test_suggest_pie_chart():
    suggester = VizSuggester()
    columns = ["traffic_source", "percentage"]
    rows = [
        {"traffic_source": "Organic", "percentage": 50},
        {"traffic_source": "Paid", "percentage": 30},
        {"traffic_source": "Referral", "percentage": 20},
    ]
    result = suggester.suggest(columns, rows)
    assert result["chart_type"] == "pie"
    assert result["x_axis"] == "traffic_source"
    assert result["y_axis"] == "percentage"


def test_suggest_geographic_map():
    suggester = VizSuggester()
    columns = ["country", "total_sales"]
    rows = [
        {"country": "USA", "total_sales": 100000},
        {"country": "Germany", "total_sales": 75000},
    ]
    result = suggester.suggest(columns, rows)
    assert result["chart_type"] == "map"
    assert result["x_axis"] == "country"
    assert result["y_axis"] == "total_sales"
