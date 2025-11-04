"""
PDF to Image Converter
Handles conversion of PDF pages to high-resolution images
"""
from pathlib import Path
from typing import List
from PIL import Image
import logging

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

logger = logging.getLogger(__name__)


class PDFConverter:
    """Convert PDF documents to images"""

    def __init__(self, dpi: int = 300, max_size: int = 2048):
        """
        Initialize PDF converter

        Args:
            dpi: Resolution for image conversion (default: 300)
            max_size: Maximum dimension for resized images (default: 2048)
        """
        self.dpi = dpi
        self.max_size = max_size
        if convert_from_path is None:
            raise ImportError(
                "pdf2image not installed. Install with: pip install pdf2image"
            )

    def _resize_if_needed(self, img: Image.Image) -> Image.Image:
        """
        Resize image if it exceeds max_size to avoid decompression bomb warning

        Args:
            img: PIL Image object

        Returns:
            Resized PIL Image object if needed, original otherwise
        """
        width, height = img.size
        max_dim = max(width, height)

        if max_dim > self.max_size:
            scale = self.max_size / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return img

    def convert_to_images(
        self, pdf_path: Path, output_dir: Path = None
    ) -> List[Image.Image]:
        """
        Convert PDF to list of PIL Images

        Args:
            pdf_path: Path to PDF file
            output_dir: Optional directory to save images

        Returns:
            List of PIL Image objects
        """
        logger.info(f"Converting PDF: {pdf_path}")

        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=self.dpi,
                fmt="PNG"
            )

            logger.info(f"Converted {len(images)} pages from PDF")

            # Resize images if needed
            images = [self._resize_if_needed(img) for img in images]

            # Optionally save images
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(exist_ok=True, parents=True)

                for i, img in enumerate(images, 1):
                    output_path = output_dir / f"page_{i:03d}.png"
                    img.save(output_path, "PNG")
                    logger.debug(f"Saved page {i} to {output_path}")

            return images

        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            raise

    def convert_single_page(
        self, pdf_path: Path, page_num: int = 1
    ) -> Image.Image:
        """
        Convert single page from PDF

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)

        Returns:
            PIL Image object
        """
        logger.info(f"Converting page {page_num} from {pdf_path}")

        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=self.dpi,
                first_page=page_num,
                last_page=page_num,
                fmt="PNG"
            )

            if images:
                return self._resize_if_needed(images[0])
            else:
                raise ValueError(f"No images returned for page {page_num}")

        except Exception as e:
            logger.error(f"Error converting page {page_num}: {e}")
            raise

    def get_page_count(self, pdf_path: Path) -> int:
        """
        Get number of pages in PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages
        """
        try:
            # Quick method to get page count without full conversion
            from pypdfium2 import PdfDocument

            pdf = PdfDocument(str(pdf_path))
            count = len(pdf)
            pdf.close()
            return count
        except ImportError:
            # Fallback: convert and count
            logger.warning("pypdfium2 not available, using slower method")
            images = self.convert_to_images(pdf_path)
            return len(images)
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            raise
