# Metadata Pipeline
# Extracts PDF metadata and flags anomalies:
#   - CreationDate > ModDate → flag (+40)
#   - Producer="Scanner" but Creator has Photoshop/Illustrator → flag (+50)
#   - Missing metadata → flag (+20)
#   - Blank Author field → flag (+10)
#
# Output: { "score": float, "flags": list[dict] }
