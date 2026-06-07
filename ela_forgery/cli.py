#!/usr/bin/env python3
"""Command-line interface for the ELA Forgery Detection Pipeline.

Designed for bank document verification workflows — cheques, statements,
KYC forms, and similar text-heavy financial documents.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from ela import compute_ela, compute_ela_multiscale
from analyze import (
    risk_score,
    find_anomalous_regions,
    error_stats,
    classify_risk,
)
from docdetect import (
    detect_document_region,
    generate_text_mask,
    classify_document_type,
)
from visualize import generate_ela_heatmap
from dashboard import build_dashboard


def _format_verdict(label):
    """Return a coloured verdict string for terminal output."""
    colours = {
        "LOW": "\033[92m",       # Green
        "MODERATE": "\033[93m",  # Yellow
        "HIGH": "\033[91m",      # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    reset = "\033[0m"
    colour = colours.get(label, "")
    return f"{colour}{label}{reset}"


def main():
    parser = argparse.ArgumentParser(
        description="ELA Forgery Detection Pipeline — Bank Document Analyser",
        epilog="Example: python cli.py cheque.jpg --multiscale --mask",
    )
    parser.add_argument("input", type=str, help="Path to input image")
    parser.add_argument(
        "--quality",
        type=int,
        default=85,
        help="JPEG quality for recompression (default: 85, range: 70-95)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output heatmap path (default: <input>_ela.png)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Error threshold for anomaly detection (default: adaptive IQR-based)",
    )
    parser.add_argument(
        "--mask",
        action="store_true",
        help="Suppress low-level noise in heatmap (recommended for text-heavy docs)",
    )
    parser.add_argument(
        "--multiscale",
        action="store_true",
        help="Use multi-quality ELA sweep (q75+q85+q95) for more robust detection",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Skip document region detection and text edge masking (raw image analysis)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON only (useful for piping into other systems)",
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Enable preprocessing (CLAHE + Gaussian blur) to reduce text noise",
    )
    parser.add_argument(
        "--clahe-clip",
        type=float,
        default=2.0,
        help="CLAHE clip limit for contrast (default: 2.0, range: 1.0–4.0)",
    )
    parser.add_argument(
        "--clahe-grid",
        type=int,
        default=8,
        help="CLAHE grid size (default: 8, creates 8x8 tiles)",
    )
    parser.add_argument(
        "--blur-sigma",
        type=float,
        default=0.8,
        help="Gaussian blur sigma in pixels (default: 0.8, 0.0 disables blur)",
    )
    parser.add_argument(
        "--dashboard",
        type=str,
        default=None,
        help="Output path for the 4-panel diagnostic dashboard (e.g. dashboard.png)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file without prompting",
    )

    args = parser.parse_args()

    # --- Validate input ---
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found — {args.input}", file=sys.stderr)
        sys.exit(1)

    if not input_path.is_file():
        print(f"Error: not a file — {args.input}", file=sys.stderr)
        sys.exit(1)

    # --- Resolve output path ---
    if args.output is None:
        output_path = input_path.with_name(f"{input_path.stem}_ela.png")
    else:
        output_path = Path(args.output)

    if output_path.exists() and not args.force:
        print(
            f"Warning: output file '{output_path}' already exists. "
            f"Use --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.dashboard:
        dash_path = Path(args.dashboard)
        if dash_path.exists() and not args.force:
            print(
                f"Warning: dashboard file '{dash_path}' already exists. "
                f"Use --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)

    # --- Compute ELA ---
    try:
        # Prepare preprocessing options
        preprocess_opts = None
        if args.preprocess:
            preprocess_opts = {
                'enabled': True,
                'clahe_clip': args.clahe_clip,
                'clahe_grid': (args.clahe_grid, args.clahe_grid),
                'blur_sigma': args.blur_sigma,
            }
        
        if args.multiscale:
            error_map = compute_ela_multiscale(args.input, preprocess=preprocess_opts)
        else:
            error_map = compute_ela(args.input, quality=args.quality, preprocess=preprocess_opts)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: ELA computation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Document boundary and text masking ---
    doc_mask = None
    text_mask = None
    doc_type = 'PHOTO'

    if not args.raw:
        try:
            doc_mask = detect_document_region(args.input)
            text_mask = generate_text_mask(args.input, doc_mask)
            doc_type = classify_document_type(args.input, doc_mask)
        except Exception as exc:
            print(f"Warning: Document region detection failed, falling back to raw mode — {exc}", file=sys.stderr)
            args.raw = True

    # --- Analyse ---
    score = risk_score(error_map, doc_mask=doc_mask, text_mask=text_mask, doc_type=doc_type, image_path=args.input)
    regions = find_anomalous_regions(error_map, threshold=args.threshold, doc_mask=doc_mask)
    stats = error_stats(error_map)
    label, explanation = classify_risk(score)

    # --- Generate heatmap ---
    mask_threshold = None
    if args.mask:
        mask_threshold = stats["mean_error"] + 2.0 * stats["std_error"]

    try:
        heatmap = generate_ela_heatmap(
            args.input, error_map, threshold=mask_threshold, doc_mask=doc_mask
        )
        Image.fromarray(heatmap).save(str(output_path))
    except Exception as exc:
        print(f"Error: heatmap generation failed — {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Generate dashboard ---
    if args.dashboard:
        try:
            build_dashboard(
                args.input,
                args.dashboard,
                use_multiscale=args.multiscale,
                quality=args.quality,
                preprocess=preprocess_opts
            )
        except Exception as exc:
            print(f"Error: dashboard generation failed — {exc}", file=sys.stderr)
            sys.exit(1)

    # --- Output ---
    result = {
        "risk_score": score,
        "risk_label": label,
        "risk_explanation": explanation,
        "anomalous_regions": regions,
        "document_type": doc_type if not args.raw else 'RAW_IMAGE',
        **stats,
        "ela_image": str(output_path),
        "multiscale": args.multiscale,
        "raw_mode": args.raw,
        "preprocessing_enabled": args.preprocess,
    }
    
    if args.preprocess:
        result["preprocessing"] = {
            "clahe_clip": args.clahe_clip,
            "clahe_grid": args.clahe_grid,
            "blur_sigma": args.blur_sigma,
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        verdict = _format_verdict(label)
        print()
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║     ELA Forgery Detection — Results         ║")
        print("  ╠══════════════════════════════════════════════╣")
        print(f"  ║  Risk Score:        {score:>6}/100               ║")
        print(f"  ╚══════════════════════════════════════════════╝")
        print()
        print(f"  Verdict:           {verdict}")
        print(f"  Explanation:       {explanation}")
        print(f"  Document Type:     {doc_type if not args.raw else 'RAW_IMAGE'}")
        print(f"  Anomalous Regions: {regions}")
        print(f"  Mean Error:        {stats['mean_error']}")
        print(f"  Max Error:         {stats['max_error']}")
        print(f"  95th Percentile:   {stats['p95_error']}")
        print(f"  99th Percentile:   {stats['p99_error']}")
        print(f"  IQR Error:         {stats['iqr_error']}")
        print(f"  ELA Heatmap:       {output_path}")
        if args.dashboard:
            print(f"  Dashboard:         {args.dashboard}")
        print()

        if args.mask:
            print(f"  ℹ Noise floor {mask_threshold:.2f} suppressed in heatmap")
        if args.multiscale:
            print("  ℹ Multi-scale ELA (q75 + q85 + q95) was used")
        if args.raw:
            print("  ℹ Raw image analysis mode (no document masking)")
        if args.preprocess:
            print(f"  ℹ Preprocessing enabled (CLAHE clip={args.clahe_clip}, blur σ={args.blur_sigma})")
        print()


if __name__ == "__main__":
    main()
