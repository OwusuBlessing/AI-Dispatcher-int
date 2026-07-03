"""AI Dispatcher — main entry point."""

from src.pipelines.submission_pipeline import SubmissionPipeline


def main() -> None:
    """Run the full submission pipeline."""
    pipeline = SubmissionPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
