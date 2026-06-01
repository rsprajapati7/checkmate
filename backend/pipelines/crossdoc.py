# Cross-Document NLP Pipeline
# Extracts text from all uploaded docs and cross-checks:
#   - PAN number consistency across docs
#   - GST number consistency
#   - Revenue / Net Profit / Asset / Liability values
#   - Document dates
#
# Output: { "score": float, "flags": list[dict] }
