import json
def serialize_report(report_data: dict) -> str:
    return json.dumps(report_data)
