import sys
import os
import argparse
from backend.pipelines.seal_detection.scorer import _detect_seals, _load_yolo_model
from backend.pipelines.seal_detection.visualize import generate_seal_dashboard

def main():
    parser = argparse.ArgumentParser(description="Test Seal Detection Visualizer CLI")
    parser.add_argument("input_image", help="Path to the input image file")
    parser.add_argument("--output", default="tmp/seal_dashboard.png", help="Path to save the output dashboard image")
    args = parser.parse_args()
    
    if not os.path.exists(args.input_image):
        print(f"Error: input image '{args.input_image}' not found.")
        sys.exit(1)
        
    print(f"Loading YOLO model...")
    model = _load_yolo_model()
    
    print(f"Detecting seals in '{args.input_image}'...")
    boxes = _detect_seals(args.input_image, model)
    print(f"Found {len(boxes)} seals: {boxes}")
    
    if len(boxes) == 0:
        print("No seals detected. Cannot generate dashboard.")
        sys.exit(0)
        
    print(f"Generating seal dashboard...")
    success = generate_seal_dashboard(args.input_image, boxes, args.output)
    if success:
        print(f"Dashboard successfully generated at: {args.output}")
    else:
        print("Failed to generate dashboard.")

if __name__ == "__main__":
    main()
