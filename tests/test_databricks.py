"""Tests for databricks module — input validation and pure logic."""

from clawctl.databricks import _TABLE_RE, _is_valid_json


class TestTableNameValidation:
    """Ensure the table name regex prevents SQL injection."""

    def test_valid_names(self) -> None:
        for name in [
            "dev_catalog.openclaw_data.sessions_raw",
            "my_cat.my_schema.my_table",
            "catalog123.schema456.table789",
            "a.b.c",
        ]:
            assert _TABLE_RE.match(name), f"Should accept: {name}"

    def test_rejects_sql_injection(self) -> None:
        for bad in [
            "'; DROP TABLE sessions_raw; --",
            "dev_catalog.openclaw_data",          # only two parts
            "cat.schema.table; EXEC xp_cmdshell",
            "cat.sche ma.tbl",                    # space
            "",
            "cat.schema.table.extra",             # four parts
            "cat..table",                         # empty identifier
        ]:
            assert not _TABLE_RE.match(bad), f"Should reject: {bad!r}"


class TestIsValidJson:
    """Ensure _is_valid_json correctly filters JSONL lines."""

    def test_valid_objects(self) -> None:
        for s in [
            '{"session_id": "abc", "tokens": 100}',
            '{"a": 1, "b": [1, 2]}',
            "42",
            '"string"',
            "true",
            "[]",
        ]:
            assert _is_valid_json(s), f"Should be valid JSON: {s}"

    def test_invalid(self) -> None:
        for s in [
            "{bad json}",
            "",
            "undefined",
            "None",
            "{key: value}",   # unquoted key
        ]:
            assert not _is_valid_json(s), f"Should be invalid JSON: {s!r}"
