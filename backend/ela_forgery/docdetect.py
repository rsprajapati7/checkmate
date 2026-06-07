"""Document detection and classification module for ELA forgery pipeline.

Provides functions to identify the document boundaries, generate text/edge masks,
and classify images into DOCUMENT or PHOTO types to support adaptive scoring.
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image

def _load_numpy_image(image_input):
    """Utility to load PIL/path input into RGB numpy array."""
    if isinstance(image_input, (str, Path)):
        img = Image.open(image_input).convert("RGB")
        return np.array(img)
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("RGB")
        return np.array(img)
    elif isinstance(image_input, np.ndarray):
        if image_input.ndim == 3 and image_input.shape[2] == 3:
            return image_input
        elif image_input.ndim == 2:
            return cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
    raise ValueError("Unsupported image input format. Must be file path, PIL Image, or numpy array.")

def detect_document_region(image_input):
    """Detect the boundary contour of a document against background.

    Parameters
    ----------
    image_input : str, Path, PIL.Image, or numpy.ndarray
        The input image.

    Returns
    -------
    numpy.ndarray
        2D binary mask (uint8) of the same size as input, where 255 = document, 0 = background.
    """
    np_img = _load_numpy_image(image_input)
    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape

    # Apply Gaussian blur and Otsu's thresholding to find light page against dark background
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Perform morphological operations to merge document parts
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(gray, dtype=np.uint8)

    if contours:
        # Get largest contour by area
        largest_cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_cnt)
        # If the contour covers at least 15% of the total image, we treat it as the document
        if area > (h * w * 0.15):
            cv2.drawContours(mask, [largest_cnt], -1, 255, -1)
            # Fill any internal holes in the document mask
            contour_mask = np.zeros_like(gray, dtype=np.uint8)
            cv2.drawContours(contour_mask, [largest_cnt], -1, 255, -1)
            return contour_mask

    # Fallback: whole image is document
    return np.ones_like(gray, dtype=np.uint8) * 255

def generate_text_mask(image_input, doc_mask=None):
    """Generate a binary mask of high-contrast text edges.

    Text edges naturally produce ELA compression artifacts (ringing noise),
    which can be masked out during analysis to prevent false positives.

    Parameters
    ----------
    image_input : str, Path, PIL.Image, or numpy.ndarray
        The input image.
    doc_mask : numpy.ndarray, optional
        Document boundary mask. If provided, edge detection is limited to this region.

    Returns
    -------
    numpy.ndarray
        2D binary mask (uint8) where 255 = text/edge region, 0 = uniform region.
    """
    np_img = _load_numpy_image(image_input)
    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

    if doc_mask is None:
        doc_mask = np.ones_like(gray, dtype=np.uint8) * 255

    # Blur slightly to reduce sensor noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Detect high-contrast edges (canny thresholds tuned for print/text)
    edges = cv2.Canny(blurred, 60, 180)

    # Restrict to document region
    edges = cv2.bitwise_and(edges, edges, mask=doc_mask)

    # Dilate edges to create a protective buffer around the ringing noise zones
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    text_mask = cv2.dilate(edges, kernel, iterations=1)

    return text_mask

def classify_document_type(image_input, doc_mask=None):
    """Classify the image content type as 'DOCUMENT' (text-heavy) or 'PHOTO' (natural/textured).

    Parameters
    ----------
    image_input : str, Path, PIL.Image, or numpy.ndarray
        The input image.
    doc_mask : numpy.ndarray, optional
        Document boundary mask.

    Returns
    -------
    str
        'DOCUMENT' or 'PHOTO'
    """
    np_img = _load_numpy_image(image_input)
    gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

    if doc_mask is None:
        doc_mask = np.ones_like(gray, dtype=np.uint8) * 255

    doc_pixels = doc_mask > 0
    if not np.any(doc_pixels):
        return "PHOTO"

    # Compute adaptive threshold to extract fine stroke components (ignores lighting/shadow gradients)
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15
    )
    
    # Restrict to document region
    adaptive_masked = cv2.bitwise_and(adaptive, adaptive, mask=doc_mask)
    
    # Calculate the ratio of stroke pixels within the document area
    active_ratio = np.mean(adaptive_masked[doc_pixels] > 0)

    # Documents have high uniform background area, so strokes/edges occupy a small percentage (< 15%).
    # Photos have organic textures causing high edge/contrast density (> 15%).
    if active_ratio < 0.15:
        return "DOCUMENT"
    return "PHOTO"
