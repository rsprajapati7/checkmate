import os
import io
import cv2
import numpy as np
from PIL import Image

def generate_seal_dashboard(image_path: str, seal_regions: list, output_path: str) -> bool:
    """
    Generate a visual dashboard for detected seal regions with summary metrics at the top.
    
    Layout:
    [Metrics Header Card]
    ---------------------
    [Original Crop] | [Laplacian Edges] | [Crop ELA Heatmap] (Row 1)
    [Original Crop] | [Laplacian Edges] | [Crop ELA Heatmap] (Row 2)
    ...
    
    Saves the composite dashboard to output_path.
    Returns True if generated, False otherwise.
    """
    if not seal_regions:
        print("[Seal Visualize] No seal regions detected.")
        return False
        
    img = cv2.imread(image_path)
    if img is None:
        print(f"[Seal Visualize] Failed to load image: {image_path}")
        return False
        
    h, w = img.shape[:2]
    crop_size = 200
    panel_w = crop_size
    panel_h = crop_size + 30  # 30px header at the top of each crop panel
    
    # Pre-calculate metrics for the top header card
    total_seals = len(seal_regions)
    suspicious_count = 0
    crop_metrics = []
    
    for idx, box in enumerate(seal_regions):
        x1, y1, x2, y2 = box
        # Clip coordinates to image boundary
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            continue
            
        crop = img[y1:y2, x1:x2]
        crop_resized = cv2.resize(crop, (crop_size, crop_size))
        
        # Laplacian Edges
        gray = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = lap.var()
        lap_abs = np.abs(lap)
        lap_max = lap_abs.max()
        if lap_max > 0:
            lap_norm = (lap_abs / lap_max * 255).astype(np.uint8)
        else:
            lap_norm = np.zeros_like(gray, dtype=np.uint8)
        lap_color = cv2.applyColorMap(lap_norm, cv2.COLORMAP_JET)
        
        # Crop ELA Heatmap
        pil_crop = Image.fromarray(cv2.cvtColor(crop_resized, cv2.COLOR_BGR2RGB))
        buf = io.BytesIO()
        pil_crop.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        recomp_pil = Image.open(buf)
        orig_np = np.array(pil_crop, dtype=np.float32)
        recomp_np = np.array(recomp_pil, dtype=np.float32)
        ela_err = np.abs(orig_np - recomp_np)
        ela_mean = np.mean(ela_err, axis=2)
        ela_max = ela_mean.max()
        if ela_max > 0:
            ela_norm = (ela_mean / ela_max * 255).astype(np.uint8)
        else:
            ela_norm = np.zeros_like(gray, dtype=np.uint8)
        ela_color = cv2.applyColorMap(ela_norm, cv2.COLORMAP_JET)
        
        # Check if suspicious: requires high sharpness + ELA combined, or very high ELA alone
        is_susp = (lap_var > 1200 and ela_mean.mean() > 4.0) or (ela_mean.mean() > 6.0)
        if is_susp:
            suspicious_count += 1
            
        crop_metrics.append({
            "idx": idx,
            "crop": crop_resized,
            "lap_color": lap_color,
            "lap_var": lap_var,
            "ela_color": ela_color,
            "ela_mean": ela_mean.mean(),
            "is_suspicious": is_susp
        })
        
    # Calculate overall risk score
    if total_seals == 0:
        overall_score = 0.0
    else:
        susp_ratio = suspicious_count / total_seals
        overall_score = min(100.0, susp_ratio * 80.0 + (suspicious_count * 5.0))
        
    # Build Top Header Summary Panel
    header_h = 100
    header_w = panel_w * 3 + 20
    header = np.zeros((header_h, header_w, 3), dtype=np.uint8)
    header[:] = [59, 41, 30]  # Slate color (BGR for #1E293B)
    
    # Title
    cv2.putText(header, "SEAL FORENSICS DASHBOARD", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Subtitle (Filename)
    filename = os.path.basename(image_path)
    cv2.putText(header, f"Document: {filename}", (20, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1, cv2.LINE_AA)
    
    # Metrics columns
    # 1. Total Seals Detected
    cv2.putText(header, "SEALS DETECTED:", (20, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(header, f"{total_seals}", (150, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2, cv2.LINE_AA)
    
    # 2. Suspicious Seals Flagged
    cv2.putText(header, "SUSPICIOUS:", (200, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    susp_color = (80, 80, 239) if suspicious_count > 0 else (80, 239, 80)  # Red vs Green (BGR)
    cv2.putText(header, f"{suspicious_count}", (305, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.48, susp_color, 2, cv2.LINE_AA)
    
    # 3. Overall Stamp Risk Score
    cv2.putText(header, "OVERALL SCORE:", (360, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1, cv2.LINE_AA)
    score_color = (80, 80, 239) if overall_score >= 60 else ((80, 200, 239) if overall_score >= 30 else (80, 239, 80)) # Red, Amber, Green
    cv2.putText(header, f"{overall_score:.1f}/100", (485, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.48, score_color, 2, cv2.LINE_AA)
    
    # Border for header card
    cv2.rectangle(header, (0, 0), (header_w, header_h), (229, 231, 235), 1)
    
    # Build crop rows
    rows = []
    for m in crop_metrics:
        # Build individual panels
        def create_panel(image, title, is_alert=False):
            panel = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
            # Header color: Alert (Red) vs Info (Dark Blue)
            header_color = (15, 33, 98) if is_alert else (96, 52, 15)  # BGR
            cv2.rectangle(panel, (0, 0), (panel_w, 30), header_color, -1)
            cv2.putText(
                panel, title, (8, 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.35, (255, 255, 255), 1, cv2.LINE_AA
            )
            panel[30:, :] = image
            cv2.rectangle(panel, (0, 0), (panel_w, panel_h), (229, 231, 235), 1)
            return panel
            
        p1 = create_panel(m["crop"], f"Seal #{m['idx']+1} Original")
        p2 = create_panel(m["lap_color"], f"Edges (Var: {m['lap_var']:.0f})", is_alert=(m["lap_var"] > 800))
        p3 = create_panel(m["ela_color"], f"ELA (Mean: {m['ela_mean']:.1f})", is_alert=(m["ela_mean"] > 4.0))
        
        # Combine row side-by-side with 10px spacing
        row = np.zeros((panel_h, header_w, 3), dtype=np.uint8)
        row.fill(255)
        
        row[:, :panel_w] = p1
        row[:, panel_w + 10:panel_w * 2 + 10] = p2
        row[:, panel_w * 2 + 20:] = p3
        
        rows.append(row)
        
    if not rows:
        print("[Seal Visualize] No valid seal crops could be created.")
        return False
        
    # Combine Header + Rows vertically
    spacing = 15
    total_h = header_h + spacing + sum(r.shape[0] for r in rows) + spacing * (len(rows) - 1)
    
    dashboard = np.zeros((total_h, header_w, 3), dtype=np.uint8)
    dashboard.fill(255)
    
    # Place header
    dashboard[0:header_h, :] = header
    
    # Place rows
    current_y = header_h + spacing
    for row in rows:
        rh = row.shape[0]
        dashboard[current_y:current_y + rh, :] = row
        current_y += rh + spacing
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, dashboard)
    print(f"[Seal Visualize] Seal Dashboard with metrics saved successfully to {output_path}")
    return True
