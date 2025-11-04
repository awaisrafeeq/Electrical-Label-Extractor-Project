"""
Main Processing Pipeline
Orchestrates the entire label extraction workflow
"""
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
import logging
import time

from .pdf_processor import PDFConverter
from .ocr_engine import OCRExtractor
from .vision_ai import VisionAnalyzer, LabelData
from .excel_exporter import ExcelExporter
from .utils import LabelValidator, LabelStatistics

logger = logging.getLogger(__name__)


class LabelExtractionPipeline:
    """Main pipeline for extracting labels from electrical diagrams"""

    def __init__(
        self,
        vision_provider: str = "anthropic",
        vision_api_key: Optional[str] = None,
        vision_model: Optional[str] = None,
        use_ocr: bool = True,
        pdf_dpi: int = 300,
        max_image_size: int = 2048
    ):
        """
        Initialize the extraction pipeline

        Args:
            vision_provider: "openai" or "anthropic"
            vision_api_key: API key for vision AI
            vision_model: Model name (optional)
            use_ocr: Whether to use OCR preprocessing (currently informational)
            pdf_dpi: DPI for PDF conversion
            max_image_size: Maximum image dimension for resizing
        """
        self.pdf_converter = PDFConverter(dpi=pdf_dpi, max_size=max_image_size)
        self.ocr_extractor = OCRExtractor() if use_ocr else None
        self.vision_analyzer = VisionAnalyzer(
            provider=vision_provider,
            api_key=vision_api_key,
            model=vision_model
        )
        self.excel_exporter = ExcelExporter()
        self.validator = LabelValidator()

        logger.info("Label extraction pipeline initialized")

    def _extract_with_retry(
        self, image: Image.Image, page_num: int, max_retries: int = 3
    ) -> List[LabelData]:
        """
        Extract labels with retry logic for API failures

        Args:
            image: PIL Image to process
            page_num: Page number for logging
            max_retries: Maximum retry attempts

        Returns:
            List of LabelData objects
        """
        for attempt in range(max_retries):
            try:
                labels = self.vision_analyzer.extract_labels(image)
                return labels
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed for page {page_num}: {e}")

                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts exhausted for page {page_num}")
                    return []  # Return empty list if all retries fail

        return []

    def process_image(
        self,
        image_path: Path,
        output_excel: Optional[Path] = None
    ) -> tuple[List[LabelData], Optional[Path]]:
        """
        Process a single image file

        Args:
            image_path: Path to image file
            output_excel: Optional path for Excel output

        Returns:
            Tuple of (labels, excel_path)
        """
        logger.info(f"Processing image: {image_path}")

        # Load image
        image = Image.open(image_path)

        # Extract labels using Vision AI
        labels = self.vision_analyzer.extract_labels(image)

        logger.info(f"Extracted {len(labels)} labels from image")

        # Export to Excel if requested
        excel_path = None
        if output_excel:
            excel_path = self.excel_exporter.export_labels(labels, output_excel)

        return labels, excel_path

    def process_pdf(
        self,
        pdf_path: Path,
        output_excel: Optional[Path] = None,
        page_range: Optional[tuple[int, int]] = None
    ) -> tuple[List[LabelData], Optional[Path]]:
        """
        Process a multi-page PDF document

        Args:
            pdf_path: Path to PDF file
            output_excel: Optional path for Excel output
            page_range: Optional (start, end) page numbers (1-indexed)

        Returns:
            Tuple of (all_labels, excel_path)
        """
        logger.info(f"Processing PDF: {pdf_path}")

        # Get page count
        total_pages = self.pdf_converter.get_page_count(pdf_path)
        logger.info(f"PDF has {total_pages} pages")

        # Determine page range
        if page_range:
            start_page, end_page = page_range
            start_page = max(1, start_page)
            end_page = min(total_pages, end_page)
        else:
            start_page, end_page = 1, total_pages

        logger.info(f"Processing pages {start_page} to {end_page}")

        # Convert PDF to images
        images = self.pdf_converter.convert_to_images(pdf_path)

        # Process each page with retry logic
        all_labels = []
        failed_pages = []

        for i, image in enumerate(images[start_page - 1:end_page], start=start_page):
            logger.info(f"Processing page {i}/{end_page}...")

            labels = self._extract_with_retry(image, i)

            if labels:
                logger.info(f"Page {i}: Found {len(labels)} labels")
                all_labels.extend(labels)
            else:
                logger.warning(f"Page {i}: No labels extracted (may have failed)")
                failed_pages.append(i)

        logger.info(f"Total labels extracted: {len(all_labels)}")

        if failed_pages:
            logger.warning(f"Failed pages: {failed_pages}")

        # Validate labels
        validation_errors = self.validator.validate_all(all_labels)

        if validation_errors:
            logger.warning(f"Validation found {len(validation_errors)} issues")
            for error in validation_errors[:5]:  # Log first 5 errors
                logger.warning(f"  {error.error_type}: {error.message}")

        # Generate statistics
        stats = LabelStatistics(all_labels)
        stats_report = stats.generate_report()
        logger.info("\n" + stats_report)

        # Export to Excel if requested
        excel_path = None
        if output_excel:
            excel_path = self.excel_exporter.export_labels(
                all_labels, output_excel,
                validation_errors=validation_errors,
                statistics=stats
            )

        return all_labels, excel_path

    def process_single_page_pdf(
        self,
        pdf_path: Path,
        page_num: int = 1,
        output_excel: Optional[Path] = None
    ) -> tuple[List[LabelData], Optional[Path]]:
        """
        Process a single page from PDF (for Milestone 1 testing)

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            output_excel: Optional path for Excel output

        Returns:
            Tuple of (labels, excel_path)
        """
        logger.info(f"Processing page {page_num} from PDF: {pdf_path}")

        # Convert single page
        image = self.pdf_converter.convert_single_page(pdf_path, page_num)

        # Extract labels
        labels = self.vision_analyzer.extract_labels(image)

        logger.info(f"Extracted {len(labels)} labels from page {page_num}")

        # Export to Excel if requested
        excel_path = None
        if output_excel:
            excel_path = self.excel_exporter.export_labels(labels, output_excel)

        return labels, excel_path

    def batch_process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        file_pattern: str = "*.pdf"
    ) -> dict[Path, Path]:
        """
        Process all PDFs in a directory

        Args:
            input_dir: Directory containing input files
            output_dir: Directory for Excel outputs
            file_pattern: Glob pattern for files to process

        Returns:
            Dictionary mapping input paths to output Excel paths
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        results = {}

        # Find all matching files
        files = list(input_dir.glob(file_pattern))
        logger.info(f"Found {len(files)} files to process")

        for pdf_file in files:
            try:
                # Generate output filename
                output_file = output_dir / f"{pdf_file.stem}_labels.xlsx"

                logger.info(f"Processing: {pdf_file.name}")

                # Process PDF
                _, excel_path = self.process_pdf(pdf_file, output_file)

                results[pdf_file] = excel_path

            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                continue

        logger.info(f"Batch processing complete. Processed {len(results)} files")
        return results
