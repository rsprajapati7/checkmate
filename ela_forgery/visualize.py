"""Visualisation utilities for ELA forgery detection.

Generates heatmap overlays that are safe for bank-document analysis, highlighting
detected document boundaries and drawing bounding boxes around anomalous regions.
"""

import cv2
import numpy as np
from PIL import Image

# Minimum error range (in pixel difference) below which the heatmap
# is treated as "all clean" — prevents NORM_MINMAX from stretching
# tiny noise into alarming false-colour patches.
_MIN_MEANINGFUL_RANGE = 8.0

def generate_ela_heatmap(original_path, error_map, alpha=0.6, threshold=None, doc_mask=None):
    """Overlay a colour-mapped ELA heatmap on the original image.

    Parameters
    ----------
    original_path : str
        Path to the original image.
    error_map : numpy.ndarray
        2D float32 ELA error map.
    alpha : float, optional
        Blend factor for the heatmap overlay (default: 0.6).
    threshold : float or None, optional
        If given, suppress error below this value in the heatmap.
    doc_mask : numpy.ndarray or None, optional
        If given, dim background regions and outline document boundary.

    Returns
    -------
    numpy.ndarray
        RGB uint8 image with heatmap overlay.
    """
    original_pil = Image.open(original_path).convert("RGB")
    original = np.array(original_pil)[:, :, ::-1]  # RGB → BGR for OpenCV

    h, w = original.shape[:2]

    error_resized = cv2.resize(
        error_map.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR
    )

    # --- Apply threshold mask if requested ---
    if threshold is not None:
        mask = error_resized > threshold
        display = error_resized.copy()
        display[~mask] = 0
    else:
        mask = None
        display = error_resized.copy()

    # --- Safe normalisation: guard against amplifying negligible noise ---
    err_max = float(display.max())
    err_min = float(display.min())
    err_range = err_max - err_min

    if err_range < _MIN_MEANINGFUL_RANGE:
        display_norm = np.zeros_like(display, dtype=np.uint8)
    else:
        display_norm = np.clip(
            ((display - err_min) / err_range) * 255, 0, 255
        ).astype(np.uint8)

    heatmap = cv2.applyColorMap(display_norm, cv2.COLORMAP_JET)

    # Dim the heatmap in below-threshold regions so the original shows through
    if mask is not None:
        dim_factor = 0.15
        heatmap = heatmap.astype(np.float32)
        heatmap[~mask] *= dim_factor
        heatmap = np.clip(heatmap, 0, 255).astype(np.uint8)

    overlay = cv2.addWeighted(heatmap, alpha, original, 1.0 - alpha, 0)

    # --- Handle document mask: dim background and draw boundary ---
    if doc_mask is not None:
        doc_mask_resized = cv2.resize(doc_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        bg_mask = doc_mask_resized == 0

        # Dim everything outside the document
        overlay[bg_mask] = (overlay[bg_mask].astype(np.float32) * 0.4).astype(np.uint8)

        # Draw green contour around the document boundary
        contours, _ = cv2.findContours(doc_mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)

    # --- Draw red bounding boxes around anomalous regions (>= 100px) ---
    if threshold is not None:
        ksize = max(3, min(error_resized.shape) // 60) | 1
        blurred = cv2.GaussianBlur(error_resized, (ksize, ksize), 0)
        binary = (blurred > threshold).astype(np.uint8) * 255

        if doc_mask is not None:
            binary = cv2.bitwise_and(binary, binary, mask=doc_mask_resized)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= 100:  # Only box significant size anomalies
                x_b, y_b, w_b, h_b = (
                    stats[i, cv2.CC_STAT_LEFT],
                    stats[i, cv2.CC_STAT_TOP],
                    stats[i, cv2.CC_STAT_WIDTH],
                    stats[i, cv2.CC_STAT_HEIGHT]
                )
                # Draw red box
                cv2.rectangle(overlay, (x_b, y_b), (x_b + w_b, y_b + h_b), (0, 0, 255), 2)
                # Text label
                cv2.putText(
                    overlay,
                    f"Anomaly: {area}px",
                    (x_b, max(15, y_b - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 0, 255),
                    1,
                    cv2.LINE_AA
                )

    # --- Add colour-bar legend ---
    overlay = _add_colourbar(overlay, err_min, err_max, err_range)

    return overlay[:, :, ::-1]  # BGR → RGB

def _add_colourbar(image, err_min, err_max, err_range, bar_width=20, padding=10):
    """Add a vertical colourbar legend on the right side of the image."""
    h, w = image.shape[:2]

    # Create the gradient bar
    bar_h = h - 2 * padding
    if bar_h < 20:
        return image

    gradient = np.linspace(255, 0, bar_h, dtype=np.uint8).reshape(-1, 1)
    gradient = np.repeat(gradient, bar_width, axis=1)
    bar_colour = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)

    # Create a strip with padding
    strip = np.zeros((h, bar_width + 2 * padding + 60, 3), dtype=np.uint8)
    strip[padding : padding + bar_h, padding : padding + bar_width] = bar_colour

    # Add labels
    if err_range >= _MIN_MEANINGFUL_RANGE:
        cv2.putText(
            strip,
            f"{err_max:.0f}",
            (padding + bar_width + 4, padding + 14),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )
        cv2.putText(
            strip,
            f"{err_min:.0f}",
            (padding + bar_width + 4, padding + bar_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1,
        )
    else:
        cv2.putText(
            strip,
            "CLEAN",
            (padding, padding + bar_h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0),
            1,
        )

    # Concatenate colourbar to the right
    combined = np.concatenate([image, strip], axis=1)
    return combined
