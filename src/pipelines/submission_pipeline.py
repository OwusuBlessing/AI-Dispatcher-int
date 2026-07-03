"""Full pipeline: extraction + matching + submission artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from configs.settings import PROJECT_ROOT, get_settings
from src.domain.schemas import MatchingResult, ResolvedDriverProfile
from src.pipelines.extraction_pipeline import ExtractionPipeline
from src.pipelines.matching_pipeline import MatchingPipeline
from src.services.load_normalizer import LoadNormalizationReport
from src.services.submission_formatter import format_submission_document, generate_readme


@dataclass(frozen=True)
class SubmissionResult:
    """Paths and in-memory results from a submission run."""

    driver: ResolvedDriverProfile
    load_report: LoadNormalizationReport
    matching: MatchingResult
    output_dir: Path
    submission_path: Path
    readme_path: Path
    profile_json_path: Path
    audit_json_path: Path
    top_loads_json_path: Path


class SubmissionPipeline:
    """Orchestrate end-to-end extraction, matching, and deliverable generation."""

    def __init__(
        self,
        *,
        extraction: ExtractionPipeline | None = None,
        matching: MatchingPipeline | None = None,
    ) -> None:
        if extraction is None:
            extraction = ExtractionPipeline()
        self.extraction = extraction
        self.matching = matching or MatchingPipeline()

    def run(
        self,
        conversation_path: Path | str,
        loads_path: Path | str,
        *,
        output_dir: Path | str | None = None,
        readme_path: Path | str | None = None,
        top_n: int = 3,
    ) -> SubmissionResult:
        """Run extraction + matching and write submission artifacts."""
        conversation_path = Path(conversation_path)
        loads_path = Path(loads_path)
        settings = get_settings()
        out_dir = Path(output_dir) if output_dir else settings.output_dir
        readme_out = Path(readme_path) if readme_path else PROJECT_ROOT / "README.md"

        if not conversation_path.exists():
            raise FileNotFoundError(f"Conversation file not found: {conversation_path}")
        if not loads_path.exists():
            raise FileNotFoundError(f"Loads file not found: {loads_path}")

        transcript = conversation_path.read_text(encoding="utf-8")
        driver = self.extraction.run(transcript)
        load_report, matching = self.matching.run_from_files(
            driver,
            loads_path,
            top_n=top_n,
        )

        out_dir.mkdir(parents=True, exist_ok=True)

        profile_json_path = out_dir / "resolved_driver_profile.json"
        audit_json_path = out_dir / "load_audit.json"
        top_loads_json_path = out_dir / "top_loads.json"
        submission_path = out_dir / "submission.md"

        profile_json_path.write_text(
            driver.model_dump_json(indent=2),
            encoding="utf-8",
        )
        audit_json_path.write_text(
            json.dumps(
                [audit.model_dump(mode="json") for audit in matching.audits],
                indent=2,
            ),
            encoding="utf-8",
        )
        top_loads_json_path.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in matching.top_loads],
                indent=2,
            ),
            encoding="utf-8",
        )
        submission_path.write_text(
            format_submission_document(driver, matching),
            encoding="utf-8",
        )
        readme_out.write_text(generate_readme(), encoding="utf-8")

        return SubmissionResult(
            driver=driver,
            load_report=load_report,
            matching=matching,
            output_dir=out_dir,
            submission_path=submission_path,
            readme_path=readme_out,
            profile_json_path=profile_json_path,
            audit_json_path=audit_json_path,
            top_loads_json_path=top_loads_json_path,
        )
