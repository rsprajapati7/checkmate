"""Statistical analysis of ELA error maps for forgery detection.

Provides document-aware risk scoring, connected components anomaly detection,
and statistical reporting optimized for both natural images and text documents.

Scoring components (100 points total):
  - Spatial Clustering (ELA-based):     20 pts
  - Local Contrast (ELA-based):         15 pts
  - Global Outliers (ELA-based):        10 pts
  - Uniformity / CV (ELA-based):         5 pts
  - JPEG Ghost Score (compression):     20 pts
  - Noise Inconsistency (sensor):       15 pts
  - Grid Mismatch (structure):          15 pts
"""

import cv2
import numpy as np

from ghost import compute_jpeg_ghost, ghost_block_variance


# ---------------------------------------------------------------------------
# ELA-based sub-scores
# ---------------------------------------------------------------------------

def _block_means(error_map, block_size=32, doc_mask=None, text_mask=None):
    """Divide the error map into blocks and return per-block mean errors.

    Masks out background pixels and text edges to isolate uniform regions.
    """
    h, w = error_map.shape
    bh = h // block_size
    bw = w // block_size

    if bh < 2 or bw < 2:
        return None

    # Work on a copy to apply masks
    masked_error = error_map.copy().astype(np.float32)

    # Set background and text edge pixels to NaN
    if doc_mask is not None:
        masked_error[doc_mask == 0] = np.nan
    if text_mask is not None:
        masked_error[text_mask > 0] = np.nan

    grid = np.zeros((bh, bw), dtype=np.float32)

    for r in range(bh):
        for c in range(bw):
            block = masked_error[r*block_size:(r+1)*block_size, c*block_size:(c+1)*block_size]
            nan_ratio = np.isnan(block).mean()
            if nan_ratio > 0.5:
                # If a block is more than 50% masked (text edge or background), set to 0.0 to ignore
                grid[r, c] = 0.0
            else:
                grid[r, c] = np.nanmean(block)

    # Handle any remaining NaNs
    grid[np.isnan(grid)] = 0.0
    return grid

def _spatial_cluster_score(error_map, doc_mask=None, text_mask=None, doc_type='DOCUMENT'):
    """Measure the spatial clustering of high ELA values.

    Forgeries are typically highly clustered, whereas noise is scattered.
    Returns a score out of 20.0 and the maximum cluster area.
    """
    # Smooth out high-frequency noise
    blurred = cv2.GaussianBlur(error_map, (9, 9), 0)

    # For documents, we use a fixed high threshold of 55.0.
    # This avoids the "statistical self-sabotage" where a forged region inflates the IQR
    # of the whole document, raising the adaptive threshold and masking itself.
    # 55.0 is calibrated to ignore authentic text/stamp boundaries (< 45.0) but detect spliced elements (> 60.0).
    if doc_type == 'DOCUMENT':
        threshold = 55.0
    else:
        if doc_mask is not None:
            valid_pixels = blurred[doc_mask > 0]
        else:
            valid_pixels = blurred

        if len(valid_pixels) == 0:
            return 0.0, 0

        q1 = np.percentile(valid_pixels, 25)
        q3 = np.percentile(valid_pixels, 75)
        iqr = q3 - q1
        threshold = max(15.0, q3 + 3.0 * iqr)

    # Binarize high ELA pixels
    binary = (blurred > threshold).astype(np.uint8) * 255
    if doc_mask is not None:
        binary = cv2.bitwise_and(binary, binary, mask=doc_mask)

    # Apply text edge mask to binarized map for documents
    if text_mask is not None and doc_type == 'DOCUMENT':
        binary[text_mask > 0] = 0

    # Find connected components
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    max_cluster_area = 0
    for i in range(1, num_labels):  # Skip background label 0
        area = stats[i, cv2.CC_STAT_AREA]
        if area > max_cluster_area:
            max_cluster_area = area

    # Score scaling: a cluster of 1000px or larger is highly indicative of tampering.
    # Max 20.0 (reduced from 35.0 to make room for new signals)
    if max_cluster_area >= 100:
        cluster_score = min(20.0, np.sqrt(max_cluster_area / 1000.0) * 20.0)
    else:
        cluster_score = 0.0

    return round(cluster_score, 1), int(max_cluster_area)

def _local_contrast_score(grid):
    """Measure local ELA contrast by comparing each block to its neighbors.

    Forgeries show high local contrast against neighbors. Uniform print shows low local contrast.
    Returns a score out of 15.0.
    """
    if grid is None or grid.size < 9:
        return 0.0

    bh, bw = grid.shape
    local_anomalies = []

    for r in range(1, bh - 1):
        for c in range(1, bw - 1):
            center = grid[r, c]
            # Extract 3x3 neighborhood
            neighborhood = grid[r-1:r+2, c-1:c+2]
            neighbors = np.delete(neighborhood.flatten(), 4)  # remove center pixel

            n_mean = np.mean(neighbors)
            # Use floor std of 2.0 to prevent near-zero division from inflating small noise
            n_std = max(2.0, np.std(neighbors))

            diff = center - n_mean
            # Only count contrast differences that have an absolute magnitude > 5.0
            if diff > 5.0:
                local_anomalies.append(diff / n_std)

    if len(local_anomalies) == 0:
        return 0.0

    # Use the 95th percentile of local anomalies to avoid single pixel outlier dominance
    max_anomaly = np.percentile(local_anomalies, 95) if len(local_anomalies) > 5 else np.max(local_anomalies)

    # Score scaling: 3.0+ standard deviations from neighbors gives max score (15.0)
    contrast_score = min(15.0, max_anomaly * 5.0)

    # Scale contrast score by the 90th percentile of the ELA block means.
    p90_val = np.percentile(grid, 90) if grid.size > 0 else 0.0
    if p90_val < 30.0:
        contrast_score *= (p90_val / 30.0)

    return round(contrast_score, 1)


# ---------------------------------------------------------------------------
# New independent signal sub-scores
# ---------------------------------------------------------------------------

def _ghost_score(image_path, doc_mask=None, block_size=32):
    """Score based on JPEG ghost detection.

    Sweeps quality levels and measures the variance of best-quality
    across blocks. High variance = different regions have different
    compression histories = splicing evidence.

    Returns a score out of 20.0.
    """
    try:
        best_quality_map, _ = compute_jpeg_ghost(image_path)
        std_val, _ = ghost_block_variance(best_quality_map, image_path, block_size, doc_mask)
    except Exception:
        return 0.0

    # A std of 8+ quality levels across blocks is strong splicing evidence.
    # Threshold raised to 5.0 to avoid false positives on natural photos and document font-size variations.
    # Scale: std<5 → 0pts, std=5 → 8pts, std=8+ → 20pts
    if std_val < 5.0:
        return 0.0
    return round(min(20.0, ((std_val - 5.0) / 4.0) * 20.0), 1)


def _noise_inconsistency_score(image_path, doc_mask=None, text_mask=None, block_size=32):
    """Detect noise level inconsistencies across image blocks.

    Spliced regions from a different camera/source will have a
    measurably different noise floor than the surrounding area.

    Returns a score out of 15.0.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0

    # Estimate noise using Laplacian (high-pass filter)
    laplacian = cv2.Laplacian(img, cv2.CV_64F)

    h, w = laplacian.shape
    bh, bw = h // block_size, w // block_size

    if bh < 3 or bw < 3:
        return 0.0

    noise_grid = np.zeros((bh, bw), dtype=np.float64)

    for r in range(bh):
        for c in range(bw):
            block = laplacian[r * block_size:(r + 1) * block_size,
                              c * block_size:(c + 1) * block_size]

            # Get mask blocks
            if doc_mask is not None:
                mask_block = doc_mask[r * block_size:(r + 1) * block_size,
                                      c * block_size:(c + 1) * block_size]
            else:
                mask_block = None

            if text_mask is not None:
                t_block = text_mask[r * block_size:(r + 1) * block_size,
                                    c * block_size:(c + 1) * block_size]
            else:
                t_block = None

            # Filter pixels
            if mask_block is not None:
                if t_block is not None:
                    valid_pixels = block[(mask_block > 0) & (t_block == 0)]
                else:
                    valid_pixels = block[mask_block > 0]
            else:
                if t_block is not None:
                    valid_pixels = block[t_block == 0]
                else:
                    valid_pixels = block.ravel()

            if len(valid_pixels) > 0:
                noise_grid[r, c] = np.std(valid_pixels)
            else:
                noise_grid[r, c] = 0.0

    # Only use non-zero blocks
    active = noise_grid[noise_grid > 0]
    if len(active) < 4:
        return 0.0

    median_noise = np.median(active)
    if median_noise < 1e-6:
        return 0.0

    deviations = np.abs(active - median_noise) / median_noise
    max_deviation = np.percentile(deviations, 95)

    # Natural photos inherently show ~30-60% noise variation across blocks
    # (sky vs foliage vs shadow). Only flag deviations above 100% as suspicious.
    if max_deviation < 1.0:
        return 0.0
    
    score = (max_deviation - 1.0) * 15.0
    
    # Scale down for extremely clean digital renders (where median_noise is very low).
    # If median_noise is low, the variance is driven by macro layout (dividers, grids)
    # rather than actual camera sensor noise.
    scale = max(0.0, min(1.0, (median_noise - 2.0) / 4.0))
    return round(min(15.0, score * scale), 1)


def _grid_mismatch_score(image_path, doc_mask=None):
    """Detect JPEG 8x8 block grid misalignment.

    Authentic JPEG regions show strong artifacts at grid boundaries
    (every 8 pixels). Spliced regions show artifacts at shifted positions.

    Returns a score out of 15.0.
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0

    img_f = img.astype(np.float64)
    h, w = img_f.shape

    if h < 16 or w < 16:
        return 0.0

    # Compute horizontal and vertical differences
    hdiff = np.abs(np.diff(img_f, axis=1))  # horizontal edges
    vdiff = np.abs(np.diff(img_f, axis=0))  # vertical edges

    # Measure artifact strength at each possible grid offset (0-7)
    h_scores = np.zeros(8)
    v_scores = np.zeros(8)

    for offset in range(8):
        h_cols = np.arange(offset, w - 1, 8)
        v_rows = np.arange(offset, h - 1, 8)

        if len(h_cols) > 0:
            h_scores[offset] = np.mean(hdiff[:, h_cols])
        if len(v_rows) > 0:
            v_scores[offset] = np.mean(vdiff[v_rows, :])

    # Combined grid strength profile
    combined = h_scores + v_scores
    primary = np.argmax(combined)
    primary_strength = combined[primary]

    if primary_strength < 1e-8:
        return 0.0

    # Remove primary and check for secondary peaks
    remaining = np.delete(combined, primary)
    secondary_strength = np.max(remaining)

    # If the secondary peak is close to primary, we check for a competing grid.
    # If ratio is > 0.97, the profile is flat (no grid structure, just random text/texture edges).
    # If ratio is < 0.85, one grid is clearly dominant (authentic).
    ratio = secondary_strength / primary_strength
    if 0.85 < ratio <= 0.97:
        # Peak mismatch is around ratio = 0.91-0.93. We scale based on proximity to 0.91
        val = 1.0 - abs(ratio - 0.91) / 0.06
        return round(max(0.0, min(15.0, val * 15.0)), 1)
    return 0.0


# ---------------------------------------------------------------------------
# Composite risk score
# ---------------------------------------------------------------------------

def _compute_ela_score(error_map, block_size, doc_mask, text_mask, doc_type):
    """Internal: compute the ELA-only portion of the risk score (0-50 pts)."""
    # For natural photos, skip text-edge masking to avoid masking real textures
    actual_text_mask = text_mask if doc_type == 'DOCUMENT' else None

    grid = _block_means(error_map, block_size, doc_mask, actual_text_mask)

    if grid is None:
        return round(float(min(50.0, np.mean(error_map) * 5)), 1)

    flat = grid.ravel()
    valid_blocks = flat[flat > 0]

    if len(valid_blocks) == 0:
        return 0.0

    # 1. Spatial Clustering Score (0-20 points)
    cluster_score, _ = _spatial_cluster_score(error_map, doc_mask, actual_text_mask, doc_type)

    # 2. Local Contrast Score (0-15 points)
    contrast_score = _local_contrast_score(grid)

    # 3. Global Outliers (0-10 points)
    q1 = np.percentile(valid_blocks, 25)
    q3 = np.percentile(valid_blocks, 75)
    iqr = q3 - q1 + 1e-8
    outlier_fence = q3 + 1.5 * iqr
    outlier_ratio = np.mean(valid_blocks > outlier_fence)
    outlier_score = min(10.0, outlier_ratio * 75.0)

    # 4. Uniformity / Coefficient of Variation (0-5 points)
    mean_val = np.mean(valid_blocks)
    cv = np.std(valid_blocks) / (mean_val + 1e-8) if mean_val > 0 else 0
    uniformity_score = min(5.0, cv * 2.7)

    return round(cluster_score + contrast_score + outlier_score + uniformity_score, 1)


def risk_score(error_map, block_size=32, doc_mask=None, text_mask=None,
               doc_type='DOCUMENT', image_path=None):
    """Compute a 0-100 risk score using ELA + compression + noise + grid signals.

    Uses dual-mode analysis: computes both masked (document-aware) and raw
    (unmasked) ELA scores, takes the maximum, then adds independent signals
    from JPEG ghost detection, noise inconsistency, and grid mismatch analysis.

    Parameters
    ----------
    error_map : numpy.ndarray
        2D float32 error map.
    block_size : int, optional
        Size of analysis tiles.
    doc_mask : numpy.ndarray, optional
        Document boundary mask.
    text_mask : numpy.ndarray, optional
        Text/edge mask to suppress edge artifacts in 'DOCUMENT' mode.
    doc_type : str, optional
        Either 'DOCUMENT' or 'PHOTO'.
    image_path : str or None, optional
        Path to original image file. Required for ghost/noise/grid analysis.
        If None, only ELA-based scoring is used (legacy mode).

    Returns
    -------
    float
        Risk score in range [0, 100].
    """
    # --- Phase A: Dual-mode ELA analysis ---
    # Run document-masked ELA score
    doc_ela_score = _compute_ela_score(error_map, block_size, doc_mask, text_mask, doc_type)

    # Run raw (unmasked) ELA score — catches anomalies suppressed by text masking
    raw_ela_score = _compute_ela_score(error_map, block_size, doc_mask=None, text_mask=None, doc_type='PHOTO')

    # For documents, we only take the raw ELA score if there is a significant large-area ELA cluster
    # within the document page. Otherwise, the raw ELA is just triggering on normal authentic text edges.
    if doc_type == 'DOCUMENT':
        # Measure adaptive unmasked cluster area within the document page
        _, raw_max_area = _spatial_cluster_score(error_map, doc_mask, None, 'PHOTO')
        if raw_max_area < 1000:
            ela_score = doc_ela_score
        else:
            ela_score = max(doc_ela_score, raw_ela_score)
    else:
        ela_score = max(doc_ela_score, raw_ela_score)

    # --- Phase B-D: Independent signals (require image_path) ---
    ghost_pts = 0.0
    noise_pts = 0.0
    grid_pts = 0.0

    if image_path is not None:
        # Phase B: JPEG Ghost score (0-20 pts)
        ghost_pts = _ghost_score(image_path, doc_mask, block_size)

        # Phase C: Noise inconsistency score (0-15 pts)
        actual_text_mask = text_mask if doc_type == 'DOCUMENT' else None
        noise_pts = _noise_inconsistency_score(image_path, doc_mask, actual_text_mask, block_size)

        # Phase D: Grid mismatch score (0-15 pts)
        grid_pts = _grid_mismatch_score(image_path, doc_mask)

    raw_score = ela_score + ghost_pts + noise_pts + grid_pts
    return round(min(100.0, max(0.0, raw_score)), 1)


def find_anomalous_regions(error_map, threshold=None, min_area=50, doc_mask=None):
    """Detect the number of connected components of high-error pixels.

    Parameters
    ----------
    error_map : numpy.ndarray
        2D float32 ELA error map.
    threshold : float or None, optional
        Manual threshold.
    min_area : int, optional
        Minimum pixel area for components.
    doc_mask : numpy.ndarray, optional
        Document boundary mask.

    Returns
    -------
    int
        Number of anomalous regions.
    """
    # Smooth out noise
    ksize = max(3, min(error_map.shape) // 60) | 1
    blurred = cv2.GaussianBlur(error_map, (ksize, ksize), 0)

    if threshold is None:
        if doc_mask is not None:
            valid_pixels = blurred[doc_mask > 0]
        else:
            valid_pixels = blurred

        if len(valid_pixels) == 0:
            return 0

        q3 = float(np.percentile(valid_pixels, 75))
        iqr = q3 - float(np.percentile(valid_pixels, 25))
        threshold = max(4.0, q3 + 2.5 * iqr)

    binary = (blurred > threshold).astype(np.uint8) * 255
    if doc_mask is not None:
        binary = cv2.bitwise_and(binary, binary, mask=doc_mask)

    # Morphological close
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)

    region_count = 0
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            region_count += 1

    return region_count

def error_stats(error_map):
    """Compute descriptive statistics of the error map."""
    return {
        "mean_error": round(float(np.mean(error_map)), 2),
        "std_error": round(float(np.std(error_map)), 2),
        "max_error": round(float(np.max(error_map)), 2),
        "p95_error": round(float(np.percentile(error_map, 95)), 2),
        "p99_error": round(float(np.percentile(error_map, 99)), 2),
        "iqr_error": round(
            float(np.percentile(error_map, 75) - np.percentile(error_map, 25)), 2
        ),
    }

def classify_risk(score):
    """Convert risk score to human-readable label and explanation."""
    if score < 15:
        return ("LOW", "No significant signs of tampering detected.")
    elif score < 35:
        return ("MODERATE", "Minor anomalies detected — review if critical.")
    elif score < 60:
        return ("HIGH", "Significant localized anomalies found — likely tampered.")
    else:
        return ("CRITICAL", "Extremely high probability of document manipulation.")
