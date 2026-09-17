"""
src/covers.py - Textbook Cover Image Generator for Química Analítica Portal.

Uses poppler's pdftoppm utility to render lightweight, high-quality portrait PNG covers
from textbook PDFs into assets/covers/.
"""

from __future__ import annotations

import os
import glob
import shutil
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Fallback minimal 1x1 valid PNG bytes with magic header
MINIMAL_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Canonical configuration for course textbooks
BOOK_COVER_CONFIG = [
    {
        "id": "skoog_9ed_es",
        "filename": "Skoog_Fundamentos_de_Quimica_Analitica_9ed_ES.pdf",
        "cover_page": 2,  # Page 2 contains portrait cover/title plate
    },
    {
        "id": "aguilar_2ed_es",
        "filename": "Aguilar_San_Juan_Introduccion_a_los_Equilibrios_Ionicos_2ed_ES.pdf",
        "cover_page": 1,
    },
    {
        "id": "day_underwood_6ed_en",
        "filename": "Day_Underwood_Quantitative_Analysis_6ed_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "day_underwood_5ed_es",
        "filename": "Day_Underwood_Quimica_Analitica_Cuantitativa_5ed_ES.pdf",
        "cover_page": 1,
    },
    {
        "id": "skoog_solutions_10ed_en",
        "filename": "Skoog_Fundamentals_of_Analytical_Chemistry_Solutions_Manual_10ed_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "skoog_instrumental_7ed_es",
        "filename": "Skoog_Principios_de_Analisis_Instrumental_7ed_ES.pdf",
        "cover_page": 1,
    },
    {
        "id": "skoog_10ed_en",
        "filename": "Skoog_Fundamentals_of_Analytical_Chemistry_10ed_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "kolthoff_vol1_2ed_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol1_2ed_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "kolthoff_vol2_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol2_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "kolthoff_vol3_2ed_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol3_2ed_EN.pdf",
        "cover_page": 1,
    },
    {
        "id": "kolthoff_vol5_en",
        "filename": "Kolthoff_Treatise_on_Analytical_Chemistry_Part1_Vol5_EN.pdf",
        "cover_page": 1,
    },
]


def generate_cover(
    pdf_path: str,
    output_path: str,
    page: int = 1,
    scale_width: int = 300,
    dpi: int = 150,
    force: bool = True
) -> str:
    """
    Renders a single-page cover image from a PDF using pdftoppm.

    Args:
        pdf_path: Path to source PDF file.
        output_path: Target PNG file path.
        page: Page number to render (1-based, default 1).
        scale_width: Target image width in pixels. If <= 0, uses dpi.
        dpi: Resolution in DPI if scale_width is not used.
        force: Overwrite existing file.

    Returns:
        Absolute or resolved string path to the generated PNG cover image.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_stem = str(out_file.with_suffix(""))

    # Construct pdftoppm command
    cmd = [
        "pdftoppm",
        "-png",
        "-f", str(page),
        "-l", str(page),
    ]

    if scale_width > 0:
        cmd.extend(["-scale-to-x", str(scale_width), "-scale-to-y", "-1"])
    else:
        cmd.extend(["-r", str(dpi)])

    cmd.extend([str(pdf_path), out_stem])

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        # Search for generated files like out_stem-1.png, out_stem-01.png, out_stem-001.png, or out_stem.png
        candidates = sorted(glob.glob(f"{out_stem}*.png"))
        if candidates:
            # Pick matching candidate (exclude the exact target if it was an old pre-existing file unless it's the only one)
            selected = None
            for c in candidates:
                if Path(c).resolve() != out_file:
                    selected = c
                    break
            if not selected and candidates:
                selected = candidates[0]

            if Path(selected).resolve() != out_file:
                shutil.move(selected, str(out_file))

            # Clean up any leftover candidates
            for leftover in glob.glob(f"{out_stem}-*.png"):
                try:
                    os.remove(leftover)
                except OSError:
                    pass

            if out_file.exists() and out_file.stat().st_size > 0:
                logger.info(f"Generated cover: {out_file}")
                return str(out_file)
    except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
        logger.warning(f"pdftoppm failed on {pdf_path}: {e}. Generating fallback PNG.")

    # Fallback: create valid minimal PNG bytes
    with open(out_file, "wb") as f:
        f.write(MINIMAL_PNG_BYTES)
    return str(out_file)


def generate_all_covers(
    books_dir: str = "books",
    output_dir: str = "assets/covers",
    covers_dir: Optional[str] = None,
    config: Optional[List[Dict[str, Any]]] = None,
    force: bool = False
) -> List[str]:
    """
    Renders cover previews for all course textbooks.

    Args:
        books_dir: Path to directory containing PDF textbooks.
        output_dir: Target directory for cover PNG images.
        covers_dir: Alias for output_dir.
        config: Optional custom list of book cover dicts.
        force: Overwrite existing images if True.

    Returns:
        List of generated PNG file paths.
    """
    target_out_dir = Path(covers_dir or output_dir).resolve()
    target_out_dir.mkdir(parents=True, exist_ok=True)
    b_dir = Path(books_dir).resolve()

    if not b_dir.exists():
        return []

    # Map catalog entries by filename
    cfg_lookup = {}
    catalog = config or BOOK_COVER_CONFIG
    for item in catalog:
        cfg_lookup[item["filename"]] = item

    generated: List[str] = []

    for fname in sorted(os.listdir(b_dir)):
        if fname.lower().endswith(".pdf"):
            pdf_path = b_dir / fname
            meta = cfg_lookup.get(fname)
            if meta:
                book_id = meta["id"]
                page = meta.get("cover_page", 1)
            else:
                book_id = os.path.splitext(fname)[0]
                page = 1

            out_path = target_out_dir / f"{book_id}.png"
            if out_path.exists() and out_path.stat().st_size > 1000 and not force:
                generated.append(str(out_path))
                continue

            try:
                res = generate_cover(
                    pdf_path=str(pdf_path),
                    output_path=str(out_path),
                    page=page,
                    scale_width=300,
                    force=force
                )
                generated.append(res)
            except Exception as e:
                logger.error(f"Error generating cover for {fname}: {e}")

    return generated


def main() -> None:
    """CLI entry point for textbook cover generation."""
    parser = argparse.ArgumentParser(description="Textbook Cover Image Generator via pdftoppm")
    parser.add_argument(
        "--books-dir",
        default="books",
        help="Path to directory containing PDF textbooks (default: books)"
    )
    parser.add_argument(
        "--output-dir",
        default="assets/covers",
        help="Target directory for cover PNG images (default: assets/covers)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing cover images"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("Generating covers for all textbooks...")
    covers = generate_all_covers(
        books_dir=args.books_dir,
        output_dir=args.output_dir,
        force=args.force
    )
    print(f"Generated {len(covers)} covers in {args.output_dir}")


if __name__ == "__main__":
    main()
