"""NLP cross-document consistency pipeline."""
from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline, NLPResult

__all__ = ["run_nlp_pipeline", "NLPResult"]