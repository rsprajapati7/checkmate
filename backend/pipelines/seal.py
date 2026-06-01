# Seal Detection Pipeline
# Runs YOLOv8 on document image to find seal/stamp regions
# Crops detected seals → runs ELA on each crop
# Checks edge sharpness for copy-paste artifacts
#
# Output: { "score": float, "seals_found": int, "suspicious": int }
