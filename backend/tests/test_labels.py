"""Every code the API can return has a display label (see app/labels.py)."""
import re

from app import config, labels

# Schema columns whose label group has a different name.
GROUP_FOR_COLUMN = {"type": "institution_type", "basis": "relation_basis", "status": "relation_status"}


def test_every_value_allowed_by_the_schema_has_a_label():
    schema = config.SCHEMA_PATH.read_text(encoding="utf-8")
    checks = re.findall(r"CHECK\s*\(\s*(\w+)\s+IN\s*\(([^)]*)\)", schema)
    assert len(checks) >= 15  # the pattern still finds the constraints
    for column, values in checks:
        allowed = re.findall(r"'([^']*)'", values)
        if not allowed:  # numeric checks such as approximate IN (0,1)
            continue
        group = labels.LABELS[GROUP_FOR_COLUMN.get(column, column)]
        missing = [v for v in allowed if v not in group]
        assert not missing, f"{column}: no label for {missing}"


def test_date_values_in_the_database_have_labels(conn):
    for field, sql in (("date_kind", "SELECT DISTINCT kind FROM record_date"),
                       ("origin", "SELECT DISTINCT origin FROM record_date")):
        for (value,) in conn.execute(sql):
            assert value in labels.LABELS[field], (field, value)


def test_unknown_codes_fall_back_to_the_code():
    assert labels.label("resource_type", "zine") == "zine"
    assert labels.label("resource_type", None) is None
