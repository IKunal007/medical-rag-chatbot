from pathlib import Path
from typing import List
from PIL import Image as PILImage



def is_useful_image(path: Path) -> bool:
    img = PILImage.open(path)
    w, h = img.size

    # 🚫 tiny images (logos, icons)
    if w < 300 or h < 300:
        return False

    # 🚫 extreme aspect ratios (lines, separators)
    if w / h > 5 or h / w > 5:
        return False

    return True


def extract_pdf_figures(doc, output_dir: Path) -> List[Path]:
    """
    Extracts useful figures/images and saves them as PNG files.
    Filters out logos, icons, and decorative images.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    image_paths: List[Path] = []

    if not hasattr(doc, "pictures") or not doc.pictures:
        return image_paths

    for i, pic in enumerate(doc.pictures):
        if not pic.image or not hasattr(pic.image, "pil_image"):
            continue

        img_path = output_dir / f"figure_{i}.png"

        try:
            # Save image first
            pic.image.pil_image.save(img_path)

            # ✅ Keep only meaningful figures
            if is_useful_image(img_path):
                image_paths.append(img_path)
            else:
                img_path.unlink(missing_ok=True)

        except Exception:
            # Safety: never break report generation because of one bad image
            if img_path.exists():
                img_path.unlink()

    return image_paths
