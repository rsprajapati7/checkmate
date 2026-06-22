FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Tesseract and ZBar (for QR decoding)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y opencv-python opencv-python-headless && \
    pip install --no-cache-dir opencv-python-headless



# Copy source code, models, and configuration
COPY backend/ ./backend/
COPY models/ ./models/


EXPOSE 8000

# Set python path to the app directory
ENV PYTHONPATH=/app

# Start the FastAPI web application
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

