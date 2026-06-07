"""JPEG Ghost Detection module for ELA forgery pipeline.

Detects compression history mismatches by sweeping JPEG quality levels
and identifying regions that minimize at different quality factors than
the background — revealing "ghosts" of the original compression.
"""

import io
import numpy as np
from PIL import Image
from pathlib import Path


def compute_jpeg_ghost(image_path, quality_range=range(60, 100, 3)):
    """Sweep quality levels and find where each pixel's error minimizes.

    In an untampered single-save JPEG, all pixels minimize at the same
    quality. In a spliced image, the pasted region minimizes at a
    *different* quality — the one it was originally saved at.

    Parameters
    ----------
    image_path : str or Path
        Path to input JPEG image.
    quality_range : range, optional
        Quality levels to sweep. Coarser steps (3-5) are faster;
        finer steps (1-2) are more precise.

    Returns
    -------
    best_quality_map : numpy.ndarray
        2D float32 map — per-pixel quality level that minimizes error.
    best_error_map : numpy.ndarray
        2D float32 map — the minimum error achieved at each pixel.
    """
    original = Image.open(str(image_path)).convert("RGB")
    original_np = np.array(original, dtype=np.float32)

    h, w = original_np.shape[:2]
    best_quality = np.zeros((h, w), dtype=np.float32)
    best_error = np.full((h, w), np.inf, dtype=np.float32)

    for q in quality_range:
        buf = io.BytesIO()
        original.save(buf, format="JPEG", quality=q)
        buf.seek(0)
        recomp = Image.open(buf)
        recomp.load()
        recomp_np = np.array(recomp, dtype=np.float32)

        # Ensure size match (shouldn't differ but be safe)
        if recomp_np.shape != original_np.shape:
            continue

        # Per-pixel mean absolute error across RGB channels
        error = np.mean(np.abs(original_np - recomp_np), axis=2)

        improved = error < best_error
        best_error[improved] = error[improved]
        best_quality[improved] = float(q)

    return best_quality, best_error


def ghost_block_variance(best_quality_map, image_path, block_size=32, doc_mask=None):
    """Compute the variance of best-quality values across blocks.

    A high variance means different regions of the image were originally
    saved at different quality levels — strong evidence of splicing.

    Parameters
    ----------
    best_quality_map : numpy.ndarray
        Output of compute_jpeg_ghost.
    image_path : str or Path
        Path to original input image.
    block_size : int
        Tile size for block analysis.
    doc_mask : numpy.ndarray, optional
        Document boundary mask.

    Returns
    -------
    float
        Standard deviation of per-block best-quality means.
    numpy.ndarray
        Grid of per-block mean best-quality values.
    """
    import cv2
    h, w = best_quality_map.shape
    bh = h // block_size
    bw = w // block_size

    if bh < 2 or bw < 2:
        return 0.0, None

    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0, None

    quality_grid = np.zeros((bh, bw), dtype=np.float32)

    for r in range(bh):
        for c in range(bw):
            block = best_quality_map[r * block_size:(r + 1) * block_size,
                                     c * block_size:(c + 1) * block_size]
            orig_block = img[r * block_size:(r + 1) * block_size,
                             c * block_size:(c + 1) * block_size]

            # Skip flat blocks (background) which do not contain edge textures
            if np.std(orig_block) < 3.0:
                continue

            if doc_mask is not None:
                mask_block = doc_mask[r * block_size:(r + 1) * block_size,
                                      c * block_size:(c + 1) * block_size]
                valid = block[mask_block > 0]
            else:
                valid = block.ravel()

            if len(valid) > 0:
                quality_grid[r, c] = np.mean(valid)
            else:
                quality_grid[r, c] = 0.0

    # Only consider non-zero blocks
    active = quality_grid[quality_grid > 0]
    if len(active) < 4:
        return 0.0, quality_grid

    return float(np.std(active)), quality_grid
