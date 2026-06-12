"""JPEG Ghost Detection module for ELA forgery pipeline.

Detects compression history mismatches by sweeping JPEG quality levels
and identifying regions that minimize at different quality factors than
the background — revealing "ghosts" of the original compression.
"""

import io
import numpy as np
from PIL import Image
from pathlib import Path


def compute_jpeg_ghost(image_path, quality_range=range(60, 100, 5)):
    """Sweep quality levels and find where each pixel's error minimizes.

    In an untampered single-save JPEG, all pixels minimize at the same
    quality. In a spliced image, the pasted region minimizes at a
    *different* quality — the one it was originally saved at.

    Parameters
    ----------
    image_path : str or Path
        Path to input JPEG image.
    quality_range : range, optional
        Quality levels to sweep. Default step=5 (8 steps) instead of step=3
        (14 steps) for a ~40% speedup with no meaningful accuracy loss.
        Compression artifacts are detectable at 5-step resolution.

    Returns
    -------
    best_quality_map : numpy.ndarray
        2D float32 map — per-pixel quality level that minimizes error.
    best_error_map : numpy.ndarray
        2D float32 map — the minimum error achieved at each pixel.
    """
    original = Image.open(str(image_path)).convert("RGB")

    # Downscale to 50% before sweep — block-level compression artifacts are
    # scale-invariant and this halves the per-iteration compute cost.
    orig_w, orig_h = original.size
    scale_w, scale_h = orig_w // 2 or orig_w, orig_h // 2 or orig_h
    small = original.resize((scale_w, scale_h), Image.LANCZOS)

    small_np = np.array(small, dtype=np.float32)
    h, w = small_np.shape[:2]
    best_quality = np.zeros((h, w), dtype=np.float32)
    best_error = np.full((h, w), np.inf, dtype=np.float32)

    for q in quality_range:
        buf = io.BytesIO()
        small.save(buf, format="JPEG", quality=q)
        buf.seek(0)
        recomp = Image.open(buf)
        recomp.load()
        recomp_np = np.array(recomp, dtype=np.float32)

        if recomp_np.shape != small_np.shape:
            continue

        error = np.mean(np.abs(small_np - recomp_np), axis=2)

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

    # Downscale mask to match the downscaled quality map
    map_h, map_w = best_quality_map.shape
    img_resized = cv2.resize(img, (map_w, map_h), interpolation=cv2.INTER_AREA)

    quality_grid = np.zeros((bh, bw), dtype=np.float32)

    for r in range(bh):
        for c in range(bw):
            block = best_quality_map[r * block_size:(r + 1) * block_size,
                                     c * block_size:(c + 1) * block_size]
            orig_block = img_resized[r * block_size:(r + 1) * block_size,
                                     c * block_size:(c + 1) * block_size]

            # Skip flat blocks (background) which do not contain edge textures
            if np.std(orig_block) < 3.0:
                continue

            if doc_mask is not None:
                # Resize mask block to match downscaled map
                mask_block = doc_mask[r * block_size:(r + 1) * block_size,
                                      c * block_size:(c + 1) * block_size]
                # Resize mask to match quality map size
                if mask_block.shape != block.shape:
                    mask_block = cv2.resize(mask_block, (block.shape[1], block.shape[0]),
                                            interpolation=cv2.INTER_NEAREST)
                valid = block[mask_block > 0]
            else:
                valid = block.ravel()

            if len(valid) > 0:
                quality_grid[r, c] = np.mean(valid)

    # Only consider non-zero blocks
    active = quality_grid[quality_grid > 0]
    if len(active) < 4:
        return 0.0, quality_grid

    return float(np.std(active)), quality_grid
