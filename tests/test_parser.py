import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.log_engine import LogEngine, FilterCriteria, FieldCondition


# ---------------------------------------------------------------------------
# parse_line
# ---------------------------------------------------------------------------

def test_parse_fortigate_log_line():
    engine = LogEngine()
    line = 'date=2023-10-12 time=10:00:00 devname="FG-100D" srcip=192.168.1.1 action=deny'
    expected = {
        "date": "2023-10-12",
        "time": "10:00:00",
        "devname": "FG-100D",
        "srcip": "192.168.1.1",
        "action": "deny",
    }
    assert engine.parse_line(line) == expected


def test_parse_empty_line():
    engine = LogEngine()
    assert engine.parse_line("") == {}


# ---------------------------------------------------------------------------
# parse_query
# ---------------------------------------------------------------------------

def test_parse_query_empty():
    engine = LogEngine()
    assert engine.parse_query("") == []
    assert engine.parse_query("   ") == []


def test_parse_query_free_text():
    engine = LogEngine()
    conds = engine.parse_query("critical")
    assert len(conds) == 1
    assert conds[0].field is None
    assert conds[0].operator == "contains"
    assert conds[0].value == "critical"
    assert conds[0].connector == "AND"


def test_parse_query_contains():
    engine = LogEngine()
    conds = engine.parse_query("level:warning")
    assert len(conds) == 1
    assert conds[0].field == "level"
    assert conds[0].operator == "contains"
    assert conds[0].value == "warning"


def test_parse_query_eq():
    engine = LogEngine()
    conds = engine.parse_query("level==high")
    assert len(conds) == 1
    assert conds[0].field == "level"
    assert conds[0].operator == "eq"
    assert conds[0].value == "high"


def test_parse_query_neq():
    engine = LogEngine()
    conds = engine.parse_query("action!=pass")
    assert len(conds) == 1
    assert conds[0].field == "action"
    assert conds[0].operator == "neq"
    assert conds[0].value == "pass"


def test_parse_query_and():
    engine = LogEngine()
    conds = engine.parse_query("level:error AND action:deny")
    assert len(conds) == 2
    assert conds[0].field == "level"
    assert conds[1].field == "action"
    assert conds[1].connector == "AND"


def test_parse_query_or():
    engine = LogEngine()
    conds = engine.parse_query("level:error OR level:warning")
    assert len(conds) == 2
    assert conds[0].value == "error"
    assert conds[1].value == "warning"
    assert conds[1].connector == "OR"


def test_parse_query_three_conditions():
    engine = LogEngine()
    conds = engine.parse_query("level:error AND action:deny OR srcip:10.0")
    assert len(conds) == 3
    assert conds[1].connector == "AND"
    assert conds[2].connector == "OR"


def test_parse_query_case_insensitive_operators():
    engine = LogEngine()
    conds = engine.parse_query("level:error and action:deny")
    assert len(conds) == 2
    assert conds[1].connector == "AND"


def test_parse_query_field_lowercased():
    engine = LogEngine()
    conds = engine.parse_query("LEVEL:critical")
    assert conds[0].field == "level"
    assert conds[0].value == "critical"


# ---------------------------------------------------------------------------
# apply_filter — no conditions
# ---------------------------------------------------------------------------

def _engine_with_logs(logs):
    engine = LogEngine()
    engine.all_logs = logs
    engine.filtered_logs = []
    return engine


def _criteria(query="", date_start=None, date_end=None):
    engine = LogEngine()
    conditions = engine.parse_query(query)
    return FilterCriteria(conditions=conditions, date_start=date_start, date_end=date_end)


LOGS = [
    {"level": "critical", "action": "deny",  "srcip": "192.168.1.1", "dstport": "443"},
    {"level": "warning",  "action": "allow", "srcip": "10.0.0.5",    "dstport": "80"},
    {"level": "info",     "action": "pass",  "srcip": "10.0.0.6",    "dstport": "443"},
    {"level": "high",     "action": "block", "srcip": "172.16.0.1",  "dstport": "8080"},
    {"action": "deny",    "srcip": "1.2.3.4"},
]


def test_no_conditions_returns_all():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria(""))
    assert len(engine.filtered_logs) == len(LOGS)


# ---------------------------------------------------------------------------
# apply_filter — contains (:)
# ---------------------------------------------------------------------------

def test_filter_contains_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:critical"))
    assert len(engine.filtered_logs) == 1
    assert engine.filtered_logs[0]["level"] == "critical"


def test_filter_contains_substring():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("srcip:10.0"))
    assert len(engine.filtered_logs) == 2


def test_filter_contains_no_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:emergency"))
    assert engine.filtered_logs == []


# ---------------------------------------------------------------------------
# apply_filter — exact (==)
# ---------------------------------------------------------------------------

def test_filter_eq_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level==high"))
    assert len(engine.filtered_logs) == 1
    assert engine.filtered_logs[0]["level"] == "high"


def test_filter_eq_no_partial_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level==crit"))
    assert engine.filtered_logs == []


def test_filter_eq_absent_field_no_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level==deny"))
    assert engine.filtered_logs == []


# ---------------------------------------------------------------------------
# apply_filter — not equal (!=) — including absent field fix
# ---------------------------------------------------------------------------

def test_filter_neq_excludes_value():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("action!=deny"))
    results = [l["action"] for l in engine.filtered_logs]
    assert "deny" not in results


def test_filter_neq_absent_field_excluded():
    logs = [
        {"level": "info",  "action": "pass"},
        {"action": "pass"},
    ]
    engine = _engine_with_logs(logs)
    engine.apply_filter(_criteria("level!=info"))
    assert len(engine.filtered_logs) == 0


def test_filter_neq_absent_field_not_counted():
    logs = [
        {"level": "critical", "srcip": "1.1.1.1"},
        {"srcip": "2.2.2.2"},
    ]
    engine = _engine_with_logs(logs)
    engine.apply_filter(_criteria("level!=critical"))
    assert len(engine.filtered_logs) == 0


# ---------------------------------------------------------------------------
# apply_filter — AND / OR connectors
# ---------------------------------------------------------------------------

def test_filter_and_both_must_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:critical AND action:deny"))
    assert len(engine.filtered_logs) == 1


def test_filter_and_one_missing():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:critical AND action:allow"))
    assert engine.filtered_logs == []


def test_filter_or_either_matches():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:critical OR level:warning"))
    assert len(engine.filtered_logs) == 2


def test_filter_or_neither_matches():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:emergency OR level:debug"))
    assert engine.filtered_logs == []


def test_filter_left_to_right_evaluation():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("level:critical AND action:deny OR level:warning"))
    results = {l["level"] for l in engine.filtered_logs}
    assert results == {"critical", "warning"}


# ---------------------------------------------------------------------------
# apply_filter — free text
# ---------------------------------------------------------------------------

def test_filter_free_text_matches_any_field():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("172.16"))
    assert len(engine.filtered_logs) == 1
    assert engine.filtered_logs[0]["srcip"] == "172.16.0.1"


def test_filter_free_text_no_match():
    engine = _engine_with_logs(LOGS)
    engine.apply_filter(_criteria("nonexistent"))
    assert engine.filtered_logs == []


# ---------------------------------------------------------------------------
# apply_filter — date range
# ---------------------------------------------------------------------------

DATE_LOGS = [
    {"date": "2024-01-01", "time": "08:00:00", "level": "info"},
    {"date": "2024-01-02", "time": "12:00:00", "level": "warning"},
    {"date": "2024-01-03", "time": "18:00:00", "level": "critical"},
]


def test_filter_date_start_excludes_earlier():
    engine = _engine_with_logs(DATE_LOGS)
    engine.apply_filter(FilterCriteria(
        conditions=[],
        date_start=datetime(2024, 1, 2, 0, 0, 0),
        date_end=None,
    ))
    assert len(engine.filtered_logs) == 2
    assert engine.filtered_logs[0]["level"] == "warning"


def test_filter_date_end_excludes_later():
    engine = _engine_with_logs(DATE_LOGS)
    engine.apply_filter(FilterCriteria(
        conditions=[],
        date_start=None,
        date_end=datetime(2024, 1, 2, 23, 59, 59),
    ))
    assert len(engine.filtered_logs) == 2


def test_filter_date_range():
    engine = _engine_with_logs(DATE_LOGS)
    engine.apply_filter(FilterCriteria(
        conditions=[],
        date_start=datetime(2024, 1, 2, 0, 0, 0),
        date_end=datetime(2024, 1, 2, 23, 59, 59),
    ))
    assert len(engine.filtered_logs) == 1
    assert engine.filtered_logs[0]["level"] == "warning"


def test_filter_date_excludes_logs_without_date():
    logs = [
        {"date": "2024-01-01", "time": "08:00:00", "level": "info"},
        {"level": "warning"},
    ]
    engine = _engine_with_logs(logs)
    engine.apply_filter(FilterCriteria(
        conditions=[],
        date_start=datetime(2024, 1, 1, 0, 0, 0),
        date_end=None,
    ))
    assert len(engine.filtered_logs) == 1
