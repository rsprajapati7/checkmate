"""
QR code extractor for document images.

Uses pyzbar to decode QR codes from PIL images.
Falls back gracefully if pyzbar is not installed.
"""

from dataclasses import dataclass, field
from typing import List

from PIL import Image

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    _PYZBAR_AVAILABLE = True
except ImportError:
    _PYZBAR_AVAILABLE = False


@dataclass
class QRResult:
    data: str
    qr_type: str       # "QRCODE" | "PDF417" | etc.
    polygon: list = field(default_factory=list)


def extract_qr_codes(pil_img: Image.Image) -> List[QRResult]:
    """
    Decode all QR/barcode symbols from a PIL image.
    Returns an empty list if pyzbar is unavailable or no codes found.
    """
    if not _PYZBAR_AVAILABLE:
        return []

    try:
        decoded = pyzbar_decode(pil_img)
        results = []
        for sym in decoded:
            try:
                data_str = sym.data.decode("utf-8", errors="replace")
            except Exception:
                data_str = str(sym.data)
            results.append(QRResult(
                data=data_str,
                qr_type=sym.type,
                polygon=[(p.x, p.y) for p in sym.polygon],
            ))
        return results
    except Exception:
        return []


def extract_qr_from_pages(page_images: List[Image.Image]) -> List[QRResult]:
    """Scan all pages and return all decoded QR codes."""
    all_results = []
    for img in page_images:
        all_results.extend(extract_qr_codes(img))
    return all_results
