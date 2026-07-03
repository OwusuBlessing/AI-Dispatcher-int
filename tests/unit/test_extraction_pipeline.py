"""Extraction pipeline unit tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.domain.schemas import (
    ConversationEvidence,
    DriverProfile,
    DriverRequiredFields,
    FieldValue,
    ResolvedDriverProfile,
    ResolvedLocation,
)
from src.pipelines.extraction_pipeline import ExtractionPipeline
from src.services.geocoder import GeocoderService
from src.utils.cache import JsonFileCache


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def pipeline(mock_llm, tmp_path: Path):
    provider = MagicMock()
    provider.geocode.return_value = ResolvedLocation(
        city="Dallas",
        state="TX",
        country="USA",
        lat=32.7767,
        lon=-96.7970,
    )
    geocoder = GeocoderService(
        provider=provider,
        cache=JsonFileCache(tmp_path / "geocode.json"),
    )
    return ExtractionPipeline(llm=mock_llm, geocoder=geocoder)


def test_run_executes_stages_in_order(pipeline, mock_llm):
    evidence = ConversationEvidence()
    profile = DriverProfile(
        required_fields=DriverRequiredFields(
            current_location=FieldValue(value="Dallas, TX", confidence=1.0),
        )
    )
    pipeline.organizer.run = MagicMock(return_value=evidence)
    pipeline.extractor.extract = MagicMock(return_value=profile)

    result = pipeline.run("Driver: I'm in Dallas.")

    pipeline.organizer.run.assert_called_once()
    pipeline.extractor.extract.assert_called_once_with(evidence)
    assert isinstance(result, ResolvedDriverProfile)
    assert result.current_location is not None
    assert result.profile.required_fields.current_latitude is not None


def test_run_rejects_empty_transcript(pipeline):
    with pytest.raises(ValueError, match="transcript must not be empty"):
        pipeline.run("   ")
