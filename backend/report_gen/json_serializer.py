"""JSON report serializer."""
import json
import os
from datetime import datetime


def serialize_report(job_id: str, data: dict, output_dir: str) -> str:
    """Write the full pipeline result as a JSON file. Returns file path."""
    path = os.path.join(output_dir, f"{job_id}_report.json")
    data["generated_at"] = datetime.utcnow().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return path
