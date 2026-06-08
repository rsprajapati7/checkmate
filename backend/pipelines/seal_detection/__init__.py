"""Seal detection pipeline — YOLOv8n-based stamp/seal localization."""
from backend.pipelines.seal_detection.scorer import run_seal_pipeline, SealResult
from backend.pipelines.seal_detection.visualize import generate_seal_dashboard

__all__ = ["run_seal_pipeline", "SealResult", "generate_seal_dashboard"]