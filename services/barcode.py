from io import BytesIO
import requests
from PIL import Image

def decode_barcode(image_bytes):
    """Return first supported numeric EAN/UPC barcode from an uploaded image."""
    try:
        import zxingcpp
    except ImportError as exc:
        raise RuntimeError(
            "Fotoğraftan barkod okumak için zxing-cpp kurulu olmalı: "
            "python -m pip install zxing-cpp"
        ) from exc

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((1800, 1800))
    codes = zxingcpp.read_barcodes(image)
    for code in codes:
        value = str(code.text).strip()
        if value.isdigit() and 8 <= len(value) <= 14:
            return value
    return None

def lookup_barcode(barcode):
    barcode = barcode.strip()
    if not barcode.isdigit() or not 8 <= len(barcode) <= 14:
        raise ValueError("8-14 haneli barkod girin.")
    r = requests.get(
        f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",
        timeout=15,
        headers={"User-Agent": "AkilliUrunAnaliz/0.4 (educational project)"},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != 1:
        return None
    p = data.get("product", {})
    return {k: p.get(k) for k in (
        "product_name", "brands", "ingredients_text", "ingredients_text_tr", "ingredients_text_en",
        "nutriscore_grade", "allergens", "quantity", "nutriments"
    )}
