import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ingestion.engine import ingest_document
from backend.pipelines.ela_forgery.runner import run_ela_pipeline
from backend.pipelines.ela_forgery.dashboard import build_dashboard
from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline
from backend.pipelines.seal_detection.scorer import run_seal_pipeline, _load_yolo_model, _detect_seals
from backend.pipelines.seal_detection.visualize import generate_seal_dashboard
from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline
from backend.ai_investigator.llm_client import llm_client
from backend.fusion.engine import fuse_scores
from backend.fusion.risk_tier import tier_label

async def generate_report(file_path: str, output_md: str, multiscale: bool = True, mask: bool = True):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    print(f"1. Ingesting {file_path}...")
    job_id = "report_job_" + Path(file_path).stem
    output_dir = "tmp/report_output"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("tmp", exist_ok=True)
    
    ingestion = ingest_document(file_path, job_id, output_dir)
    image_paths = [p.image_path for p in ingestion.pages]
    
    print("2. Running ELA Forgery Pipeline...")
    ela_res = await run_ela_pipeline(image_paths, multiscale=multiscale, mask=mask, is_scanned=ingestion.is_scanned)
    
    ela_dashboards = []
    for idx, img_path in enumerate(image_paths):
        page_num = idx + 1
        dash_path = f"tmp/ela_dashboard_page{page_num}.png"
        try:
            build_dashboard(img_path, dash_path, use_multiscale=multiscale, is_scanned=ingestion.is_scanned)
            ela_dashboards.append((page_num, dash_path))
            print(f"Generated ELA dashboard for page {page_num} at: {dash_path}")
        except Exception as e:
            print(f"Failed to generate ELA dashboard for page {page_num}: {e}")
    
    print("3. Running Metadata Forensics Pipeline...")
    meta_res = await run_metadata_pipeline(ingestion)
    
    print("4. Running Seal Detection Pipeline...")
    seal_res = await run_seal_pipeline(image_paths, is_scanned=ingestion.is_scanned)
    
    seal_dashboards = []
    try:
        model = _load_yolo_model()
        for idx, img_path in enumerate(image_paths):
            page_num = idx + 1
            dash_path = f"tmp/seal_dashboard_page{page_num}.png"
            seal_regions = _detect_seals(img_path, model, is_scanned=ingestion.is_scanned)
            if seal_regions:
                generate_seal_dashboard(img_path, seal_regions, dash_path, is_scanned=ingestion.is_scanned)
                seal_dashboards.append((page_num, dash_path))
                print(f"Generated Seal dashboard for page {page_num} at: {dash_path}")
    except Exception as e:
        print(f"Failed to generate Seal dashboards: {e}")

    print("5. Running NLP & Cross-Document Consistency Pipeline...")
    nlp_res = await run_nlp_pipeline(ingestion)
    
    print("6. Executing Fusion Engine...")
    fusion = fuse_scores(
        ela_score=ela_res.score,
        metadata_score=meta_res.score,
        seal_score=seal_res.score,
        nlp_score=nlp_res.score,
        is_scanned=ingestion.is_scanned,
    )
    
    print("7. Generating Forensic Summary via AI Model...")
    prompt = f"""
You are CheckMate AI, a senior forensic document investigator. Analyze the following pipeline results and write a highly professional, comprehensive forensic report.
Do not use emojis in your response. Keep the tone clinical, objective, and authoritative.

Document Details:
- Filename: {Path(file_path).name}
- File Type: {ingestion.file_type}
- Pages: {ingestion.page_count}
- Scan Status: {"Scanned" if ingestion.is_scanned else "Digital PDF"}

Pipeline Metrics:
- ELA (Error Level Analysis) Forgery Score: {ela_res.score}/100 (Risk: {ela_res.risk_label})
- Metadata Anomaly Score: {meta_res.score}/100
- Seal Tampering/Pasting Score: {seal_res.score}/100 (Detected seals: {seal_res.seals_found}, Suspicious seals: {seal_res.suspicious_seals})
- NLP / Cross-Doc Semantic Score: {nlp_res.score}/100

Global Risk Status:
- Final Integrated Score: {fusion.final_score * 100:.1f}/100
- Risk Tier: {fusion.risk_tier.value} ({tier_label(fusion.risk_tier)})

Extracted Entities & Metadata:
- Extracted PANs: {nlp_res.entities.get("pan_numbers", [])}
- Extracted Aadhaar: {nlp_res.entities.get("aadhaar_numbers", [])}
- Extracted GSTINs: {nlp_res.entities.get("gst_numbers", [])}
- Extracted Person Names: {nlp_res.entities.get("person_names", [])}
- QR Code Content: {ingestion.all_qr_codes}
- Document Metadata: {ingestion.pdf_metadata}

Active Flags and Warning Triggers:
- ELA Flags: {ela_res.flags}
- Metadata Flags: {meta_res.flags}
- Seal Flags: {seal_res.flags}
- NLP Flags: {nlp_res.flags}

Please structure the markdown report with the following sections:
1. Executive Summary: Overall assessment of authenticity, key highlights.
2. Forensic Analysis details for each category: Image/ELA, Metadata, Seal, NLP/QR.
3. Verdict & Recommended Next Steps.
"""
    
    try:
        report_text = await llm_client.complete(prompt)
    except Exception as e:
        report_text = f"Failed to generate report via AI model: {e}"

    # Construct the final Markdown file including references to the dashboards
    markdown_content = f"""# Forensic Document Ingestion & Verification Report

{report_text}

---

## Visual Diagnostic Dashboards

"""
    markdown_content += "### Error Level Analysis (ELA) Dashboards\n"
    if ela_dashboards:
        for page_num, path in ela_dashboards:
            markdown_content += f"#### Page {page_num}\n![ELA Dashboard Page {page_num}]({path})\n\n"
    else:
        markdown_content += "*No ELA dashboards generated.*\n\n"

    markdown_content += "### Seal/Stamp Verification Dashboards\n"
    if seal_dashboards:
        for page_num, path in seal_dashboards:
            markdown_content += f"#### Page {page_num}\n![Seal Dashboard Page {page_num}]({path})\n\n"
    else:
        markdown_content += "*No seals detected or dashboards generated.*\n\n"

    with open(output_md, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"\nSuccess! Markdown report generated at: {output_md}")

def main():
    parser = argparse.ArgumentParser(description="Generate forensic document report with AI analysis and dashboards.")
    parser.add_argument("input_file", help="Path to input document (PDF or Image)")
    parser.add_argument("--output", default="ai_report.md", help="Path to save the generated markdown report")
    parser.add_argument(
        "--multiscale",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable multi-quality ELA (default: enabled)",
    )
    parser.add_argument(
        "--mask",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable document/text masking during ELA (default: enabled)",
    )
    args = parser.parse_args()
    
    asyncio.run(generate_report(args.input_file, args.output, multiscale=args.multiscale, mask=args.mask))

if __name__ == "__main__":
    main()
