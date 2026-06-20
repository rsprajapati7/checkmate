import os
import sys
import urllib.request

MODEL_DIR = os.path.join("models", "yolov8")
MODEL_PATH = os.path.join(MODEL_DIR, "seal_detector.pt")

# Open-source pre-trained YOLOv8 model for document signature and seal detection
MODEL_URL = "https://huggingface.co/tech4humans/yolov8s-signature-detector/resolve/main/yolov8s.pt"

def download_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Downloading open-source YOLOv8 model weights...")
    print(f"Source: {MODEL_URL}")
    print(f"Destination: {MODEL_PATH}")
    
    # Progress indicator
    def reporthook(blocknum, blocksize, totalsize):
        readsofar = blocknum * blocksize
        if totalsize > 0:
            percent = readsofar * 1e2 / totalsize
            s = f"\rProgress: {percent:5.1f}% [{readsofar}/{totalsize} bytes]"
            sys.stdout.write(s)
            sys.stdout.flush()
        else:
            sys.stdout.write(f"\rDownloaded {readsofar} bytes")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH, reporthook)
        print("\n\nSuccess: Model weights downloaded and saved successfully!")
    except Exception as e:
        print(f"\n\nError downloading model: {e}")
        print("Please check your internet connection or download the file manually from Hugging Face.")

if __name__ == "__main__":
    download_model()
