"""filesqueeze.ocr

OCR (Optical Character Recognition) functionality for scanned documents.
Uses Tesseract OCR to add invisible text layers to scanned PDFs.
"""

import os
import subprocess
import tempfile
from pathlib import Path

from .system import logger


def has_text_layer(pdf_path: str) -> bool:
    """Check if a PDF already has a text layer (is already OCRed).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        True if PDF has extractable text, False otherwise.
    """
    try:
        # Try to extract text using pdfminer or PyPDF2
        try:
            from pdfminer.high_level import extract_text

            text = extract_text(pdf_path)
            # Clean up text and check for meaningful content
            # A scanned PDF might have some noise, but real text will have:
            # - Multiple characters
            # - Letters/numbers (not just symbols)
            # - Some structure (spaces, newlines)
            text_clean = text.strip()

            # Check for minimum meaningful text length
            if len(text_clean) < 100:
                return False

            # Check if text contains alphanumeric characters
            # (not just random symbols or noise)
            import re

            alnum_count = len(re.findall(r"[a-zA-Z0-9]", text_clean))
            if alnum_count < 50:
                return False

            # If we have meaningful text, it has a text layer
            return True

        except ImportError:
            # Fallback to PyPDF2
            try:
                import PyPDF2

                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""

                    text_clean = text.strip()

                    # Same checks as above
                    if len(text_clean) < 100:
                        return False

                    import re

                    alnum_count = len(re.findall(r"[a-zA-Z0-9]", text_clean))
                    if alnum_count < 50:
                        return False

                    return True

            except ImportError:
                # If no PDF libraries available, assume it needs OCR
                # This is conservative - better to OCR than skip
                return False
    except Exception as e:
        # On error, assume it needs OCR
        logger.debug(f"Error checking for text layer: {e}", exc_info=True)
        return False


def ocr_image(
    image_path: str,
    output_path: str,
    *,
    tesseract_path: str = "tesseract",
    language: str = "eng",
    oem: int = 3,
    psm: int = 3,
    config: object = None,
) -> bool:
    """Run OCR on an image file and create a searchable PDF.

    Args:
        image_path: Path to input image file.
        output_path: Path for output PDF file.
        tesseract_path: Path to tesseract executable.
        language: OCR language(s).
        oem: OCR Engine Mode (0-3).
        psm: Page Segmentation Mode (0-13).
        config: Optional Config object with settings.

    Returns:
        True if successful, False otherwise.
    """
    try:
        cmd = [
            tesseract_path,
            image_path,
            output_path.replace(".pdf", ""),  # Tesseract adds .pdf automatically
            "-l",
            language,
            "--oem",
            str(oem),
            "--psm",
            str(psm),
            "pdf",  # Output format
        ]

        # Get timeout from config
        timeout = config.get("processing.ocr_timeout_seconds", 300) if config else 300

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        if result.returncode != 0:
            logger.error(f"Tesseract OCR error: {result.stderr}")
            return False

        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error(f"OCR failed: {e}")
        return False


def ocr_pdf(
    pdf_path: str,
    output_path: str,
    *,
    tesseract_path: str = "tesseract",
    language: str = "eng",
    oem: int = 3,
    psm: int = 3,
    dpi: int = 300,
    ghostscript_path: str = "gs",
    config: object = None,
) -> bool:
    """Run OCR on a PDF by converting pages to images first.

    This creates a searchable PDF with an invisible text layer over the original images.

    Args:
        pdf_path: Path to input PDF file.
        output_path: Path for output PDF file.
        tesseract_path: Path to tesseract executable.
        language: OCR language(s).
        oem: OCR Engine Mode (0-3).
        psm: Page Segmentation Mode (0-13).
        dpi: DPI for rendering PDF pages.
        ghostscript_path: Path to ghostscript executable.
        config: Optional Config object with settings.

    Returns:
        True if successful, False otherwise.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Step 1: Convert PDF pages to images using Ghostscript
        image_pattern = temp_path / "page_%06d.png"

        try:
            gs_cmd = [
                ghostscript_path,
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-r{dpi}",
                "-sDEVICE=png16m",
                f"-sOutputFile={image_pattern!s}",
                str(pdf_path),
            ]

            # Get timeout from config
            timeout = config.get("processing.ocr_timeout_seconds", 300) if config else 300

            result = subprocess.run(
                gs_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode != 0:
                logger.error(f"Ghostscript error converting PDF to images: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"PDF to image conversion failed: {e}")
            return False

        # Step 2: Find all generated images
        images = sorted(temp_path.glob("page_*.png"))
        if not images:
            logger.error("No images were generated from PDF")
            return False

        logger.info(f"OCR Processing {len(images)} pages...")

        # Step 3: Run OCR on each image to create individual PDFs
        ocr_pdfs = []
        for i, image in enumerate(images, 1):
            logger.debug(f"Processing page {i}/{len(images)}")

            ocr_pdf_path = temp_path / f"ocr_{i}.pdf"
            if ocr_image(str(image), str(ocr_pdf_path), tesseract_path=tesseract_path, language=language, oem=oem, psm=psm):
                ocr_pdfs.append(ocr_pdf_path)
            else:
                logger.warning(f"OCR failed for page {i}")

        if not ocr_pdfs:
            logger.error("OCR failed for all pages")
            return False

        # Step 4: Combine OCR'd PDFs into single output
        try:
            # Use Ghostscript to merge PDFs
            gs_cmd = [
                ghostscript_path,
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={output_path}",
            ] + [str(pdf) for pdf in ocr_pdfs]

            # Get timeout from config
            timeout = config.get("processing.ocr_timeout_seconds", 300) if config else 300

            result = subprocess.run(
                gs_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            if result.returncode != 0:
                logger.error(f"Ghostscript error merging PDFs: {result.stderr}")
                return False

            return True

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"PDF merge failed: {e}")
            return False


def needs_ocr(pdf_path: str, config: dict | None = None) -> bool:
    """Determine if a PDF needs OCR.

    Args:
        pdf_path: Path to the PDF file.
        config: Optional configuration dictionary.

    Returns:
        True if PDF needs OCR, False otherwise.
    """
    # Check if OCR is enabled in config
    if config:
        enable_ocr = config.get("ocr", {}).get("enable_ocr", True)
        if not enable_ocr:
            return False

    # Check if PDF already has text layer
    return not has_text_layer(pdf_path)


def process_pdf_with_ocr(
    pdf_path: str, output_path: str, config: dict | None = None, ocr_only: bool = False
) -> tuple[bool, str]:
    """Process a PDF with OCR if needed.

    Args:
        pdf_path: Path to input PDF.
        output_path: Path for output PDF.
        config: Configuration dictionary.
        ocr_only: If True, only perform OCR without compression.

    Returns:
        Tuple of (success, message).
    """
    if config is None:
        config = {}

    # Get OCR settings from config
    ocr_config = config.get("ocr", {})
    tesseract_path = ocr_config.get("tesseract_path", "tesseract")
    language = ocr_config.get("language", "eng")
    oem = ocr_config.get("oem", 3)
    psm = ocr_config.get("psm", 3)
    dpi = ocr_config.get("ocr_dpi", 300)

    # Get Ghostscript path
    document_config = config.get("document", {})
    ghostscript_path = document_config.get("ghostscript_path", "gs")

    # Check if PDF needs OCR
    if not needs_ocr(pdf_path, config):
        return False, "PDF already has text layer, skipping OCR"

    logger.info("Running OCR on scanned PDF...")

    # Run OCR
    success = ocr_pdf(
        pdf_path,
        output_path,
        tesseract_path=tesseract_path,
        language=language,
        oem=oem,
        psm=psm,
        dpi=dpi,
        ghostscript_path=ghostscript_path,
    )

    if success:
        return True, "OCR completed successfully"
    else:
        return False, "OCR failed"
