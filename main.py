#!/usr/bin/env python3
"""
CLI Tool for Electrical Label Extraction MVP
Milestone 1: Single image/page prototype
"""
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

from config import settings
from src.pipeline import LabelExtractionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('label_extraction.log')
    ]
)

logger = logging.getLogger(__name__)


def process_single_image(args):
    """Process a single image file"""
    image_path = Path(args.input)

    if not image_path.exists():
        logger.error(f"Input file not found: {image_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = settings.output_dir / f"{image_path.stem}_labels.xlsx"

    logger.info(f"Input: {image_path}")
    logger.info(f"Output: {output_path}")

    # Create pipeline
    pipeline = LabelExtractionPipeline(
        vision_provider=settings.vision_provider,
        vision_api_key=settings.anthropic_api_key if settings.vision_provider == "anthropic" else settings.openai_api_key,
        vision_model=settings.anthropic_model if settings.vision_provider == "anthropic" else settings.openai_model,
        pdf_dpi=settings.pdf_dpi,
        max_image_size=settings.max_image_size
    )

    # Process image
    try:
        labels, excel_path = pipeline.process_image(image_path, output_path)

        print(f"\n{'='*60}")
        print(f"✓ Extraction Complete!")
        print(f"{'='*60}")
        print(f"Labels found: {len(labels)}")
        print(f"Excel output: {excel_path}")
        print(f"{'='*60}\n")

        # Print summary
        if labels:
            print("Label Summary:")
            equipment_types = {}
            for label in labels:
                eq_type = label.equipment_type
                equipment_types[eq_type] = equipment_types.get(eq_type, 0) + 1

            for eq_type, count in sorted(equipment_types.items()):
                print(f"  {eq_type}: {count}")

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


def process_pdf(args):
    """Process a PDF file"""
    pdf_path = Path(args.input)

    if not pdf_path.exists():
        logger.error(f"Input file not found: {pdf_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = settings.output_dir / f"{pdf_path.stem}_labels.xlsx"

    logger.info(f"Input: {pdf_path}")
    logger.info(f"Output: {output_path}")

    # Create pipeline
    pipeline = LabelExtractionPipeline(
        vision_provider=settings.vision_provider,
        vision_api_key=settings.anthropic_api_key if settings.vision_provider == "anthropic" else settings.openai_api_key,
        vision_model=settings.anthropic_model if settings.vision_provider == "anthropic" else settings.openai_model,
        pdf_dpi=settings.pdf_dpi,
        max_image_size=settings.max_image_size
    )

    # Process PDF
    try:
        if args.page:
            # Single page
            labels, excel_path = pipeline.process_single_page_pdf(
                pdf_path, args.page, output_path
            )
        else:
            # Full PDF
            page_range = None
            if args.start_page and args.end_page:
                page_range = (args.start_page, args.end_page)

            labels, excel_path = pipeline.process_pdf(
                pdf_path, output_path, page_range
            )

        print(f"\n{'='*60}")
        print(f"✓ Extraction Complete!")
        print(f"{'='*60}")
        print(f"Labels found: {len(labels)}")
        print(f"Excel output: {excel_path}")
        print(f"{'='*60}\n")

        # Print summary
        if labels:
            print("Label Summary:")
            equipment_types = {}
            for label in labels:
                eq_type = label.equipment_type
                equipment_types[eq_type] = equipment_types.get(eq_type, 0) + 1

            for eq_type, count in sorted(equipment_types.items()):
                print(f"  {eq_type}: {count}")

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


def batch_process(args):
    """Batch process multiple PDFs"""
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Create pipeline
    pipeline = LabelExtractionPipeline(
        vision_provider=settings.vision_provider,
        vision_api_key=settings.anthropic_api_key if settings.vision_provider == "anthropic" else settings.openai_api_key,
        vision_model=settings.anthropic_model if settings.vision_provider == "anthropic" else settings.openai_model,
        pdf_dpi=settings.pdf_dpi,
        max_image_size=settings.max_image_size
    )

    # Batch process
    try:
        results = pipeline.batch_process_directory(
            input_dir, output_dir, args.pattern
        )

        print(f"\n{'='*60}")
        print(f"✓ Batch Processing Complete!")
        print(f"{'='*60}")
        print(f"Files processed: {len(results)}")
        print(f"Output directory: {output_dir}")
        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main CLI entry point"""
    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Electrical Label Extraction Tool - MVP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single image
  python main.py image circuit_page.png

  # Process single PDF page
  python main.py pdf drawing.pdf --page 1

  # Process entire PDF
  python main.py pdf drawing.pdf

  # Process PDF page range
  python main.py pdf drawing.pdf --start-page 1 --end-page 5

  # Batch process directory
  python main.py batch input_pdfs/ output_excel/
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Image command
    image_parser = subparsers.add_parser('image', help='Process single image')
    image_parser.add_argument('input', help='Input image file (PNG, JPG)')
    image_parser.add_argument('-o', '--output', help='Output Excel file path')

    # PDF command
    pdf_parser = subparsers.add_parser('pdf', help='Process PDF file')
    pdf_parser.add_argument('input', help='Input PDF file')
    pdf_parser.add_argument('-o', '--output', help='Output Excel file path')
    pdf_parser.add_argument('-p', '--page', type=int, help='Process specific page number')
    pdf_parser.add_argument('--start-page', type=int, help='Start page (for range)')
    pdf_parser.add_argument('--end-page', type=int, help='End page (for range)')

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch process directory')
    batch_parser.add_argument('input_dir', help='Input directory')
    batch_parser.add_argument('output_dir', help='Output directory')
    batch_parser.add_argument('--pattern', default='*.pdf', help='File pattern (default: *.pdf)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Validate API key
    if settings.vision_provider == "anthropic" and not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set in .env file")
        sys.exit(1)
    elif settings.vision_provider == "openai" and not settings.openai_api_key:
        logger.error("OPENAI_API_KEY not set in .env file")
        sys.exit(1)

    # Execute command
    if args.command == 'image':
        process_single_image(args)
    elif args.command == 'pdf':
        process_pdf(args)
    elif args.command == 'batch':
        batch_process(args)


if __name__ == '__main__':
    main()
