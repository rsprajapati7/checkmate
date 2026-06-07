from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import upload, analyze, status, report

app = FastAPI(title="CheckMate Forensic API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(status.router)
app.include_router(report.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "checkmate"}
