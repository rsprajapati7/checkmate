# Pipeline orchestration module.
#
# The actual orchestration is handled by backend.workers.pipeline_worker.run_pipeline,
# which runs all 4 forensic pipelines in a defined sequence with full DB tracking.
#
# This module intentionally does not re-implement the orchestration to avoid
# divergence. Import from the worker directly:
#
#   from backend.workers.pipeline_worker import run_pipeline
#
# For the CLI synchronous scan path, import individual pipelines:
#   from backend.pipelines.ela_forgery.runner import run_ela_pipeline
#   from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline
#   from backend.pipelines.seal_detection.scorer import run_seal_pipeline
#   from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline


def run_all_pipelines(*args, **kwargs):
    raise NotImplementedError(
        "Use backend.workers.pipeline_worker.run_pipeline for the full async pipeline, "
        "or import individual pipeline scorers directly."
    )
