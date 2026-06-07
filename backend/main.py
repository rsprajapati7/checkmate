# FastAPI Application Entry Point
# Routes:
#   GET  /health   → health check
#   POST /analyze  → upload document → run 4 pipelines → return results
#
# CORS enabled for frontend access.
# File upload → save → ingestion → parallel pipelines → fusion → response
