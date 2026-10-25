"""Check an already headlessly exported PDF and build background QA images."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import unicodedata

import pymupdf as fitz
from PIL import Image, ImageDraw

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
STEM = "演示文稿_Phase2_章节清晰_讲述增强版"


def norm(text):
    text = unicodedata.normalize("NFKC", text).replace("−", "-")
    return re.sub(r"[\s|]", "", text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", help="Comma-separated changed pages to rasterize; default: all")
    args = parser.parse_args()
    render_pages = set(map(int, args.pages.split(","))) if args.pages else set(range(1, 38))
    doc = fitz.open(ROOT / (STEM + ".pdf"))
    manifest = json.loads((QA / "slides_manifest.json").read_text())
    assert len(doc) == len(manifest) == 37
    missing_text = []
    for i, (page, spec) in enumerate(zip(doc, manifest), 1):
        expected = norm("".join(t["text"] for t in spec["text"]))
        actual = norm(page.get_text())
        missing = Counter(expected) - Counter(actual)
        count = sum(missing.values())
        if count > max(4, len(expected) * 0.015):
            missing_text.append({"page": i, "missing_chars": count, "details": dict(missing)})
        if i in render_pages:
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(QA / f"slide-{i:02d}.png")

    chart_labels = {
        5: ["76.0%", "89.1%", "100.0%", "0.1%"],
        6: ["51.03", "48.05", "7.94", "3.91"],
        9: ["63.7", "90.0", "57.3", "111.2"],
        15: ["52.7%", "35.8%", "4.6%", "3.4%"],
        16: ["3.4%", "0.6%", "52.6%", "38.2%"],
        20: ["16.9%", "4.5%", "7.9%", "0.6%"],
        22: ["43.5%", "56.3%", "26.7%", "6.4%"],
        25: ["89.0%", "9.1%", "2.0%"],
        27: ["49.6%", "29.9%", "74.1%"],
    }
    missing_labels = []
    for n, labels in chart_labels.items():
        actual = norm(doc[n - 1].get_text())
        absent = [v for v in labels if norm(v) not in actual]
        if absent:
            missing_labels.append({"page": n, "missing_chart_labels": absent})
    for batch, start in enumerate(range(0, len(doc), 12), 1):
        rows = min(3, (len(doc) - start + 3) // 4)
        contact = Image.new("RGB", (1600, rows * 250), "#DFDEE5")
        draw = ImageDraw.Draw(contact)
        for j in range(start, min(start + 12, len(doc))):
            im = Image.open(QA / f"slide-{j + 1:02d}.png")
            im.thumbnail((384, 216))
            x = (j - start) % 4 * 400 + 8
            y = (j - start) // 4 * 250 + 26
            contact.paste(im, (x, y))
            draw.text((x, y - 19), f"{j + 1:02d}", fill="#292044")
        contact.save(QA / f"contact-{batch}.png")
    result = {
        "mode": "background_only_no_GUI",
        "renderer": "LibreOffice headless",
        "pdf_pages": len(doc),
        "pdf_sha256": hashlib.sha256((ROOT / (STEM + ".pdf")).read_bytes()).hexdigest(),
        "missing_body_text": missing_text,
        "missing_chart_labels": missing_labels,
        "chart_pages_checked": list(chart_labels),
        "contact_sheets": 4,
        "visual_review": "Pending inspection of generated slide images.",
    }
    (QA / "render_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not missing_text, "Body text may have been clipped"
    assert not missing_labels, "Native chart labels absent from PDF"


if __name__ == "__main__":
    main()
