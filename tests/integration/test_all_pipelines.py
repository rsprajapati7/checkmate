import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path if needed
sys.path.insert(0, str(Path(__file__).parent))

from backend.ingestion.engine import ingest_document, IngestionResult
from backend.pipelines.ela_forgery.runner import run_ela_pipeline
from backend.pipelines.metadata_forensics.scorer import run_metadata_pipeline
from backend.pipelines.seal_detection.scorer import run_seal_pipeline
from backend.pipelines.nlp_cross_doc.scorer import run_nlp_pipeline
from backend.cross_analysis.registry_client import verify_document

async def run_pipeline_test(file_path: str):
    print("=" * 80)
    print(f"Testing File: {file_path}")
    print("=" * 80)
    
    # 1. Ingestion
    job_id = "test_job_" + Path(file_path).stem
    output_dir = "tmp/test_output"
    
    print("\n--- [Step 1] Running Ingestion ---")
    try:
        ingestion = ingest_document(file_path, job_id, output_dir)
        print(f"Ingestion successful!")
        print(f"Document ID: {ingestion.document_id}")
        print(f"File Type: {ingestion.file_type}")
        print(f"Page Count: {ingestion.page_count}")
        print(f"Is Scanned: {ingestion.is_scanned}")
        print(f"Full OCR Text (length): {len(ingestion.full_ocr_text)}")
        print(f"Full Native Text (length): {len(ingestion.full_native_text)}")
        print(f"All QR Codes: {ingestion.all_qr_codes}")
        print(f"PDF Metadata: {ingestion.pdf_metadata}")
        print(f"XMP Metadata (length): {len(ingestion.xmp_metadata) if ingestion.xmp_metadata else 0}")
    except Exception as e:
        print(f"Ingestion FAILED: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Get image paths for visual pipelines
    image_paths = [p.image_path for p in ingestion.pages]
    print(f"\nGenerated page images: {image_paths}")
    for path in image_paths:
        print(f"  - {path} exists: {os.path.exists(path)}")

    # 3. ELA Pipeline
    print("\n--- [Step 2] Running ELA Pipeline ---")
    try:
        ela_res = await run_ela_pipeline(image_paths)
        print(f"Score: {ela_res.score}")
        print(f"Label: {ela_res.risk_label}")
        print(f"Anomalous Regions: {ela_res.anomalous_regions}")
        print(f"Flags: {ela_res.flags}")
        print(f"Per Page Scores: {ela_res.per_page_scores}")
    except Exception as e:
        print(f"ELA Pipeline FAILED: {e}")

    # 4. Metadata Pipeline
    print("\n--- [Step 3] Running Metadata Pipeline ---")
    try:
        meta_res = await run_metadata_pipeline(ingestion)
        print(f"Score: {meta_res.score}")
        print(f"Flags: {meta_res.flags}")
        print(f"Raw Metadata Keys: {list(meta_res.raw_metadata.keys())}")
    except Exception as e:
        print(f"Metadata Pipeline FAILED: {e}")

    # 5. Seal Pipeline
    print("\n--- [Step 4] Running Seal Pipeline ---")
    try:
        seal_res = await run_seal_pipeline(image_paths)
        print(f"Score: {seal_res.score}")
        print(f"Seals Found: {seal_res.seals_found}")
        print(f"Suspicious Seals: {seal_res.suspicious_seals}")
        print(f"Flags: {seal_res.flags}")
    except Exception as e:
        print(f"Seal Pipeline FAILED: {e}")

    # 6. NLP Pipeline
    print("\n--- [Step 5] Running NLP Pipeline ---")
    try:
        nlp_res = await run_nlp_pipeline(ingestion)
        print(f"Score: {nlp_res.score}")
        print(f"Flags: {nlp_res.flags}")
        print(f"Entities: {nlp_res.entities}")
    except Exception as e:
        print(f"NLP Pipeline FAILED: {e}")

    # 7. Registry check (Simulate if entity extracted)
    print("\n--- [Step 6] Simulating Registry Check ---")
    if nlp_res and nlp_res.entities.get("pan_numbers"):
        pan = nlp_res.entities["pan_numbers"][0]
        print(f"Verifying detected PAN: {pan}")
        try:
            reg_res = verify_document("PAN", pan)
            if reg_res:
                print(f"Registry Result: Found={reg_res.found}, Match={reg_res.match}, Message={reg_res.message}")
        except Exception as e:
            print(f"Registry Check FAILED: {e}")
    else:
        print("No PAN numbers found to check in registry.")

async def main():
    if len(sys.argv) > 1:
        assets = sys.argv[1:]
    else:
        assets = ["Neeraj-7.pdf", "Roll.jpeg"]
        if os.path.exists("Rajat.pdf"):
            assets.append("Rajat.pdf")
            
    for asset in assets:
        if os.path.exists(asset):
            await run_pipeline_test(asset)
        else:
            print(f"Asset '{asset}' not found in current directory.")

if __name__ == "__main__":
    asyncio.run(main())
