"""Metadata forensics pipeline — full implementation."""
from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline, MetadataResult

__all__ = ["run_metadata_pipeline", "MetadataResult"]