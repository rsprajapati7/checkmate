"""Core ELA (Error Level Analysis) computation module.

Provides single-quality and multi-quality ELA for robust document
forgery detection on bank statements, cheques, and similar documents.
"""

import io
import warnings
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


# Formats where ELA is meaningful (double JPEG compression)
_JPEG_EXTENSIONS = {".jpg", ".jpeg", ".jfif", ".jpe"}


def load_image(image_path):
    """Load and validate an image, converting to RGB.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file is not a valid image or is truncated/corrupt.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        img = Image.open(image_path)
        # Force full decode to catch truncated files early
        img.load()
    except UnidentifiedImageError:
        raise ValueError(
            f"Cannot identify image file (corrupt or unsupported format): {image_path}"
        )
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"Image file is corrupt or truncated: {image_path} — {exc}")

    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _check_input_format(image_path):
    """Warn if the input is not a JPEG — ELA requires double JPEG compression."""
    suffix = Path(image_path).suffix.lower()
    if suffix not in _JPEG_EXTENSIONS:
        warnings.warn(
            f"Input file '{Path(image_path).name}' is not JPEG (detected: {suffix}). "
            f"ELA relies on double-JPEG-compression artifacts. Results on non-JPEG "
            f"inputs are unreliable and may cause false positives.",
            UserWarning,
            stacklevel=3,
        )


def preprocess_image(img, clahe_clip=2.0, clahe_grid=(8, 8), blur_sigma=0.8):
    """Apply contrast normalization and noise reduction to improve ELA stability.

    Preprocessing steps (in order):
    1. Convert RGB to YCrCb colour space (preserves luminance).
    2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) on Y channel.
    3. Apply light Gaussian blur to reduce sensor noise.
    4. Convert back to RGB.

    This reduces text-edge noise and sensor artifacts, improving signal-to-noise
    for document forensics. Recommended for text-heavy bank documents.

    Parameters
    ----------
    img : PIL.Image
        RGB image to preprocess.
    clahe_clip : float, optional
        CLAHE clip limit (default: 2.0). Controls contrast amplification.
        Range 1.0–4.0 typical. Higher = more contrast.
    clahe_grid : tuple of int, optional
        CLAHE grid size (default: (8, 8)). Larger grids apply more global
        contrast; smaller apply more local. (8, 8) is balanced.
    blur_sigma : float, optional
        Gaussian blur standard deviation in pixels (default: 0.8).
        0.0 = no blur. 1.0–2.0 typical for noise reduction.

    Returns
    -------
    PIL.Image
        Preprocessed RGB image.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Convert PIL Image to OpenCV (BGR) array
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # Convert BGR to YCrCb (preserve luminance)
    ycrcb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0]

    # Apply CLAHE on Y channel
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)
    y_clahe = clahe.apply(y_channel)
    ycrcb[:, :, 0] = y_clahe

    # Convert back to BGR
    img_bgr = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    # Apply light Gaussian blur if requested
    if blur_sigma > 0:
        kernel_size = int(4 * blur_sigma) | 1  # Ensure odd kernel size
        img_bgr = cv2.GaussianBlur(img_bgr, (kernel_size, kernel_size), blur_sigma)

    # Convert back to RGB PIL Image
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(img_rgb)


def compute_ela(image_path, quality=85, preprocess=None):
    """Compute Error Level Analysis map.

    Re-saves the image at a given JPEG quality and returns the
    pixel-wise absolute difference between original and recompressed
    version. Tampered regions typically show higher error.

    Parameters
    ----------
    image_path : str or Path
        Path to the input image (should be JPEG for meaningful results).
    quality : int, optional
        JPEG quality for recompression (default: 85). Lower values
        amplify the ELA signal but also increase baseline noise.
        Recommended range: 70–90.
    preprocess : dict, optional
        Preprocessing options. If None (default), no preprocessing is applied.
        Accepted keys:
        - 'enabled' (bool): Enable preprocessing (default: False).
        - 'clahe_clip' (float): CLAHE clip limit (default: 2.0).
        - 'clahe_grid' (tuple): CLAHE grid size (default: (8, 8)).
        - 'blur_sigma' (float): Gaussian blur sigma (default: 0.8).

    Returns
    -------
    numpy.ndarray
        2D float32 array of per-pixel mean absolute error (grayscale).
    """
    _check_input_format(image_path)

    original = load_image(image_path)
    
    # Apply preprocessing if requested
    if preprocess and preprocess.get('enabled', False):
        clahe_clip = preprocess.get('clahe_clip', 2.0)
        clahe_grid = preprocess.get('clahe_grid', (8, 8))
        blur_sigma = preprocess.get('blur_sigma', 0.8)
        original = preprocess_image(original, clahe_clip=clahe_clip, 
                                   clahe_grid=clahe_grid, blur_sigma=blur_sigma)
    
    original_np = np.array(original, dtype=np.float32)

    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    recompressed = Image.open(buffer)
    recompressed.load()  # Fully decode
    if recompressed.size != original.size:
        recompressed = recompressed.resize(original.size, Image.LANCZOS)
    recompressed_np = np.array(recompressed, dtype=np.float32)

    error = np.abs(original_np - recompressed_np)

    # Average across colour channels → single grayscale error map
    if error.ndim == 3:
        error = np.mean(error, axis=2)

    return error


def compute_ela_multiscale(image_path, qualities=(75, 85, 95), preprocess=None):
    """Compute ELA at multiple quality levels and fuse the results.

    Multi-quality ELA is more robust because:
    - High quality (95) captures fine structural differences.
    - Low quality (75) amplifies gross forgery artefacts.
    - Averaging reduces JPEG ringing false positives common in
      text-heavy bank documents.

    Parameters
    ----------
    image_path : str or Path
        Path to input image (should be JPEG).
    qualities : tuple of int, optional
        JPEG quality levels to sweep.
    preprocess : dict, optional
        Preprocessing options (same as compute_ela). If None, no preprocessing.

    Returns
    -------
    numpy.ndarray
        2D float32 fused error map (mean of normalised per-quality maps).
    """
    maps = []
    for q in qualities:
        emap = compute_ela(image_path, quality=q, preprocess=preprocess)
        # Normalise each map to [0, 1] so they contribute equally
        emax = emap.max()
        if emax > 0:
            maps.append(emap / emax)
        else:
            maps.append(emap)

    fused = np.mean(maps, axis=0)
    # Scale back to a reasonable pixel-difference range [0, 255]
    fused = fused * 255.0
    return fused
