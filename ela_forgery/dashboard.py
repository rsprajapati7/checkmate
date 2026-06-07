"""Diagnostic dashboard generator for ELA forgery detection pipeline.

Compiles comparison dashboards containing original image, edge masks,
heatmaps, and summary forensic report cards.
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from ela import compute_ela_multiscale, compute_ela
from docdetect import detect_document_region, generate_text_mask, classify_document_type
from analyze import risk_score, find_anomalous_regions, error_stats, classify_risk
from visualize import generate_ela_heatmap


def draw_report_card(width, height, name, score, label, explanation, doc_type, active_ratio, stats, regions):
    """Draw a beautiful dark-slate report card panel."""
    # Dark slate background BGR
    card = np.zeros((height, width, 3), dtype=np.uint8)
    card[:] = (35, 30, 26)  # Deep slate gray/blue

    # Title
    cv2.putText(card, "CHECKMATE FORENSICS", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 180, 80), 2, cv2.LINE_AA)
    cv2.putText(card, "ELA Analysis Report", (30, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.line(card, (30, 95), (width - 30, 95), (70, 70, 70), 1)

    # File Info
    cv2.putText(card, "DOCUMENT SUMMARY", (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 220, 120), 1, cv2.LINE_AA)
    cv2.putText(card, f"File: {name}", (30, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(card, f"Format: JPEG", (30, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(card, f"Doc Type: {doc_type}", (30, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(card, f"Stroke Density: {active_ratio*100:.2f}%", (30, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)

    cv2.line(card, (30, 260), (width - 30, 260), (70, 70, 70), 1)

    # Forensic Scores
    cv2.putText(card, "FORENSIC METRICS", (30, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 220, 120), 1, cv2.LINE_AA)
    cv2.putText(card, f"Mean ELA Error: {stats['mean_error']}", (30, 325), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(card, f"Max ELA Error:  {stats['max_error']}", (30, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(card, f"IQR ELA Error:  {stats['iqr_error']}", (30, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(card, f"Anomalous Tiles: {regions}", (30, 415), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

    cv2.line(card, (30, 440), (width - 30, 440), (70, 70, 70), 1)

    # Verdict Panel
    # BGR colors for risk levels
    risk_colors = {
        "LOW": (80, 220, 80),        # Green
        "MODERATE": (80, 220, 220),   # Yellow/Cyan
        "HIGH": (80, 80, 240),        # Red
        "CRITICAL": (240, 80, 240),    # Purple
    }
    v_color = risk_colors.get(label, (200, 200, 200))

    cv2.rectangle(card, (30, 465), (width - 30, 585), (45, 40, 35), -1)
    cv2.rectangle(card, (30, 465), (width - 30, 585), (70, 70, 70), 1)

    cv2.putText(card, f"RISK SCORE: {score:.1f}/100", (45, 495), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(card, f"VERDICT: {label}", (45, 525), cv2.FONT_HERSHEY_SIMPLEX, 0.55, v_color, 2, cv2.LINE_AA)

    # Wrap explanation text
    words = explanation.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 35:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))

    y_offset = 550
    for line in lines[:2]:
        cv2.putText(card, line, (45, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 170, 170), 1, cv2.LINE_AA)
        y_offset += 18

    # Forensic Advisory/Disclaimer Block
    cv2.rectangle(card, (30, 605), (width - 30, 775), (25, 30, 40), -1)
    cv2.rectangle(card, (30, 605), (width - 30, 775), (50, 70, 120), 1)
    cv2.putText(card, "FORENSIC ADVISORY", (45, 630), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 180, 240), 1, cv2.LINE_AA)
    
    advisory_text = (
        "ELA is calibrated to detect compression history mismatch (digital splicing). "
        "Tiny text edits re-saved globally share the background grid structure, resulting "
        "in near-identical ELA signatures. Cross-examine using OCR, layout font consistency, "
        "and metadata analyzers."
    )
    awords = advisory_text.split()
    alines = []
    acurr = []
    for w in awords:
        acurr.append(w)
        if len(" ".join(acurr)) > 42:
            acurr.pop()
            alines.append(" ".join(acurr))
            acurr = [w]
    alines.append(" ".join(acurr))
    
    ay_offset = 655
    for line in alines[:6]:
        cv2.putText(card, line, (45, ay_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 180, 180), 1, cv2.LINE_AA)
        ay_offset += 15

    return card


def build_dashboard(image_path, output_path, use_multiscale=True, quality=85, preprocess=None):
    """Generate and save the 4-panel diagnostic dashboard.

    Parameters
    ----------
    image_path : str or Path
        Path to input image.
    output_path : str or Path
        Path where the dashboard PNG should be saved.
    use_multiscale : bool, optional
        Whether to sweep multiple JPEG qualities.
    quality : int, optional
        Quality value to use if not multiscale.
    preprocess : dict, optional
        Preprocessing options to pass to ELA computation.
    """
    img_path_str = str(Path(image_path).resolve())
    name = Path(image_path).name

    # Load raw image
    img = Image.open(img_path_str).convert("RGB")
    np_img = np.array(img)[:, :, ::-1]  # RGB -> BGR

    # Compute ELA
    if use_multiscale:
        error_map = compute_ela_multiscale(img_path_str, preprocess=preprocess)
    else:
        error_map = compute_ela(img_path_str, quality=quality, preprocess=preprocess)

    # Document segmentation and masking
    doc_mask = detect_document_region(img_path_str)
    text_mask = generate_text_mask(img_path_str, doc_mask)
    doc_type = classify_document_type(img_path_str, doc_mask)

    score = risk_score(error_map, doc_mask=doc_mask, text_mask=text_mask, doc_type=doc_type, image_path=img_path_str)
    regions = find_anomalous_regions(error_map, doc_mask=doc_mask)
    stats = error_stats(error_map)
    label, explanation = classify_risk(score)

    # Stroke ratio
    gray = cv2.cvtColor(np_img, cv2.COLOR_BGR2GRAY)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15)
    adaptive_masked = cv2.bitwise_and(adaptive, adaptive, mask=doc_mask)
    active_ratio = np.mean(adaptive_masked[doc_mask > 0] > 0) if np.any(doc_mask > 0) else 0.0

    # Panel 1: Original with doc boundary contour
    panel_orig = np_img.copy()
    contours, _ = cv2.findContours(doc_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        cv2.drawContours(panel_orig, contours, -1, (0, 255, 0), 3)
    cv2.putText(panel_orig, "1. Input & Doc Boundary", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    # Panel 2: Text Edge Mask
    panel_mask = cv2.cvtColor(text_mask, cv2.COLOR_GRAY2BGR)
    cv2.putText(panel_mask, "2. Suppressed Text Edges", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    # Panel 3: ELA Heatmap
    mask_threshold = stats["mean_error"] + 2.0 * stats["std_error"]
    heatmap = generate_ela_heatmap(img_path_str, error_map, threshold=mask_threshold, doc_mask=doc_mask)
    panel_heatmap = heatmap[:, :, ::-1].copy()  # RGB -> BGR
    # Crop colorbar if it was added (we want to match the panel size)
    panel_heatmap = panel_heatmap[:, :np_img.shape[1]]
    cv2.putText(panel_heatmap, "3. Masked ELA Heatmap", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

    # Resize panels to fit horizontal strip: 400 width x 800 height each
    p_w, p_h = 400, 800
    p1 = cv2.resize(panel_orig, (p_w, p_h))
    p2 = cv2.resize(panel_mask, (p_w, p_h))
    p3 = cv2.resize(panel_heatmap, (p_w, p_h))
    p4 = draw_report_card(p_w, p_h, name, score, label, explanation, doc_type, active_ratio, stats, regions)

    # Combine horizontally
    dashboard = np.concatenate([p1, p2, p3, p4], axis=1)
    cv2.imwrite(str(Path(output_path).resolve()), dashboard)
