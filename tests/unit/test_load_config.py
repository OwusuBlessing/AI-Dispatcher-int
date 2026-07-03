"""Load ingest config unit tests."""

from configs.load_config import LoadsIngestConfig


def test_resolve_header_map_is_case_insensitive():
    config = LoadsIngestConfig(
        column_aliases={
            "load_id": ("Load ID",),
            "origin_city": ("Origin",),
        }
    )

    header_map = config.resolve_header_map(["load id", "ORIGIN", "Extra"])

    assert header_map["load_id"] == "load id"
    assert header_map["origin_city"] == "ORIGIN"


def test_require_mapped_fields_raises_for_missing_required_columns():
    config = LoadsIngestConfig(
        column_aliases={
            "load_id": ("Load ID",),
        }
    )

    try:
        config.require_mapped_fields(config.resolve_header_map(["Load ID"]))
        raised = False
    except ValueError as exc:
        raised = True
        assert "origin_city" in str(exc)

    assert raised
