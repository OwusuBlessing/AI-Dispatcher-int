"""Load reader and normalizer unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from configs.load_config import EquipmentAliasConfig, LoadsIngestConfig
from src.domain.enums import RuleCheckStatus
from src.domain.schemas import Load
from src.rules.missing_data_rule import evaluate_missing_data
from src.services.load_normalizer import (
    load_and_normalize_loads,
    normalize_city_name,
    normalize_trailer,
)
from src.services.load_reader import read_load_rows

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOADS_FILE = PROJECT_ROOT / "data/raw/loads.xlsx"


@pytest.fixture
def sample_config() -> LoadsIngestConfig:
    return LoadsIngestConfig.from_yaml()


@pytest.fixture
def sample_equipment() -> EquipmentAliasConfig:
    return EquipmentAliasConfig.from_yaml()


@pytest.fixture
def sample_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "loads.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Loads"
    sheet.append(
        [
            "Load ID",
            "Origin",
            "Origin Lat",
            "Origin Lon",
            "Destination",
            "Dest Lat",
            "Dest Lon",
            "Trailer",
            "Weight",
            "Price ($)",
        ]
    )
    sheet.append(
        [
            "L01",
            "Houston",
            29.7604,
            -95.3698,
            "Laredo",
            27.5306,
            -99.4803,
            "Hotshot",
            11500,
            1600,
        ]
    )
    sheet.append(
        [
            "L02",
            "Austin",
            30.2672,
            -97.7431,
            "MISSING",
            None,
            None,
            "Van",
            42000,
            900,
        ]
    )
    workbook.save(path)
    return path


def test_normalize_trailer_maps_known_types(sample_equipment):
    assert normalize_trailer("Van", equipment_config=sample_equipment) == "van"
    assert normalize_trailer("Gooseneck", equipment_config=sample_equipment) == "gooseneck"


def test_normalize_trailer_rejects_unknown_type(sample_equipment):
    with pytest.raises(ValueError, match="unsupported trailer type"):
        normalize_trailer("Stepdeck", equipment_config=sample_equipment)


def test_normalize_city_name_handles_missing_marker(sample_config):
    assert normalize_city_name("MISSING", loads_config=sample_config) == ""
    assert (
        normalize_city_name("  corpus christi ", loads_config=sample_config)
        == "Corpus Christi"
    )


def test_read_and_normalize_sample_workbook(
    sample_workbook: Path,
    sample_config: LoadsIngestConfig,
    sample_equipment: EquipmentAliasConfig,
):
    rows, header_map = read_load_rows(sample_workbook, config=sample_config)
    assert len(rows) == 2
    assert "origin_city" in header_map

    report = load_and_normalize_loads(
        sample_workbook,
        loads_config=sample_config,
        equipment_config=sample_equipment,
    )
    assert len(report.loads) == 2
    assert report.loads[0].load_id == "L01"
    assert report.loads[0].trailer == "hotshot"
    assert report.loads[0].origin_state is None
    assert report.loads[0].origin_latitude == pytest.approx(29.7604)
    assert report.loads[1].destination_city == ""
    assert any("missing destination" in warning for warning in report.warnings)


def test_parses_city_and_state_from_single_location_column(sample_config, sample_equipment):
    raw_row = {
        "_source_row": 2,
        "_header_map": {
            "load_id": "Load ID",
            "origin_city": "Origin",
            "trailer": "Trailer",
            "price": "Price ($)",
        },
        "Load ID": "L99",
        "Origin": "Dallas, TX",
        "Trailer": "Van",
        "Price ($)": 1000,
    }
    from src.services.load_normalizer import normalize_load_row

    load = normalize_load_row(
        raw_row,
        header_map=raw_row["_header_map"],
        loads_config=sample_config,
        equipment_config=sample_equipment,
    )

    assert load.origin_city == "Dallas"
    assert load.origin_state == "TX"


def test_supports_alternate_column_headers(tmp_path: Path, sample_equipment: EquipmentAliasConfig):
    config = LoadsIngestConfig(
        sheet_name="Sheet1",
        column_aliases={
            "load_id": ("ID",),
            "origin_city": ("Pickup City",),
            "destination_city": ("Drop City",),
            "trailer": ("Equipment",),
            "price": ("Rate",),
        },
    )
    path = tmp_path / "custom.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(["ID", "Pickup City", "Drop City", "Equipment", "Rate"])
    sheet.append(["X1", "Dallas, TX", "Houston, TX", "Van", 1200])
    workbook.save(path)

    report = load_and_normalize_loads(
        path,
        loads_config=config,
        equipment_config=sample_equipment,
    )

    assert len(report.loads) == 1
    assert report.loads[0].load_id == "X1"
    assert report.loads[0].origin_city == "Dallas"
    assert report.loads[0].origin_state == "TX"


@pytest.mark.skipif(not LOADS_FILE.exists(), reason="assignment loads file missing")
def test_assignment_loads_file_normalizes_all_rows():
    report = load_and_normalize_loads(LOADS_FILE)

    assert len(report.loads) == 8
    assert len(report.skipped_rows) == 0
    trailers = {load.trailer for load in report.loads}
    assert trailers == {"van", "hotshot", "gooseneck", "flatbed"}
    missing_dest = [load for load in report.loads if not load.destination_city]
    assert len(missing_dest) == 1
    missing_price = [load for load in report.loads if load.price is None]
    assert len(missing_price) == 1


def test_missing_data_rule_fails_when_destination_blank():
    load = Load(
        load_id="L99",
        origin_city="Dallas",
        destination_city="",
        trailer="van",
        price=1000.0,
    )

    result = evaluate_missing_data(load)

    assert result.status == RuleCheckStatus.FAIL
    assert "destination" in (result.reason or "")


def test_missing_data_rule_fails_when_price_missing():
    load = Load(
        load_id="L06",
        origin_city="Shreveport",
        destination_city="Atlanta",
        trailer="van",
        price=None,
    )

    result = evaluate_missing_data(load)

    assert result.status == RuleCheckStatus.FAIL
    assert "price" in (result.reason or "")


def test_missing_data_rule_passes_for_complete_load():
    load = Load(
        load_id="L01",
        origin_city="Houston",
        destination_city="Laredo",
        trailer="hotshot",
        price=1600.0,
    )

    result = evaluate_missing_data(load)

    assert result.status == RuleCheckStatus.PASS
