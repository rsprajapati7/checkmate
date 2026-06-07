# ELA Pipeline
# Error Level Analysis — detects JPEG compression inconsistencies
# Steps:
#   1. Open image with Pillow
#   2. Re-save at 95% JPEG quality
#   3. Compute pixel difference (ImageChops.difference)
#   4. Normalize mean intensity to 0-100 score
#   5. Return score + ELA heatmap image (base64)
#
# Output: { "score": float, "heatmap": str }
