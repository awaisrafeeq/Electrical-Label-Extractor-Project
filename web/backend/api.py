"""
FastAPI Backend for Label Extraction Web Interface
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict, List
import uuid
import logging
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Import our extraction pipeline
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.pipeline import LabelExtractionPipeline
from src.vision_ai.analyzer import LabelData
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Electrical Label Extractor")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories - use absolute paths based on project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "output"
PAGE_IMAGES_DIR = PROJECT_ROOT / "page_images"
CROPPED_LABELS_DIR = PROJECT_ROOT / "cropped_labels"
ANNOTATED_PAGES_DIR = PROJECT_ROOT / "annotated_pages"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PAGE_IMAGES_DIR.mkdir(exist_ok=True)
CROPPED_LABELS_DIR.mkdir(exist_ok=True)
ANNOTATED_PAGES_DIR.mkdir(exist_ok=True)

# Job storage (in-memory for now, use Redis in production)
jobs: Dict[str, dict] = {}


def draw_bounding_boxes(image: Image.Image, labels: List, label_page_map: dict, page_num: int) -> Image.Image:
    """
    Draw bounding boxes on page image for labels on this page

    Args:
        image: PIL Image of the page
        labels: List of LabelData objects (all labels)
        label_page_map: Dict mapping label index to page number
        page_num: Current page number

    Returns:
        New image with bounding boxes drawn
    """
    # Create a copy to draw on
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)

    img_width, img_height = image.size

    logger.info(f"Drawing bounding boxes for page {page_num}, image size: {img_width}x{img_height}")

    # Load font with better size
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
        except:
            font = ImageFont.load_default()

    # Find labels on this page
    labels_drawn = 0
    for idx, label in enumerate(labels):
        # Check if this label is on the current page
        label_page = label_page_map.get(idx)
        if label_page != page_num:
            logger.debug(f"Skipping label {idx} - on page {label_page}, not {page_num}")
            continue

        # Skip if no bounding box coordinates
        if not all([label.bbox_x is not None, label.bbox_y is not None,
                   label.bbox_width is not None, label.bbox_height is not None]):
            logger.debug(f"Skipping label {idx} - no bbox coordinates")
            continue

        # Convert percentage coordinates to pixels
        x1 = int((label.bbox_x / 100.0) * img_width)
        y1 = int((label.bbox_y / 100.0) * img_height)
        x2 = int(((label.bbox_x + label.bbox_width) / 100.0) * img_width)
        y2 = int(((label.bbox_y + label.bbox_height) / 100.0) * img_height)

        logger.debug(f"Drawing bbox for label {idx}: ({x1},{y1}) to ({x2},{y2})")

        # Draw rectangle with thicker line
        draw.rectangle([x1, y1, x2, y2], outline="#FF0000", width=6)

        # Add label number with background
        label_text = f"#{idx + 1}"

        # Get text size for background
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Draw background rectangle for text
        text_bg_x1 = x1
        text_bg_y1 = y1 - text_height - 10
        text_bg_x2 = x1 + text_width + 20
        text_bg_y2 = y1

        draw.rectangle([text_bg_x1, text_bg_y1, text_bg_x2, text_bg_y2], fill="#FF0000")

        # Draw text
        draw.text((x1 + 10, y1 - text_height - 5), label_text, fill="white", font=font)

        labels_drawn += 1

    logger.info(f"Drew {labels_drawn} bounding boxes on page {page_num}")
    return img_copy


def crop_label_image(image: Image.Image, label) -> Optional[Image.Image]:
    """
    Crop label region from page image

    Args:
        image: PIL Image of the page
        label: LabelData object with bounding box coordinates

    Returns:
        Cropped PIL Image or None if no bbox coordinates
    """
    # Check if bounding box exists
    if not all([label.bbox_x is not None, label.bbox_y is not None,
               label.bbox_width is not None, label.bbox_height is not None]):
        return None

    img_width, img_height = image.size

    # Convert percentage coordinates to pixels with padding
    padding_percent = 2  # Add 2% padding around the label
    x1 = max(0, int(((label.bbox_x - padding_percent) / 100.0) * img_width))
    y1 = max(0, int(((label.bbox_y - padding_percent) / 100.0) * img_height))
    x2 = min(img_width, int(((label.bbox_x + label.bbox_width + padding_percent) / 100.0) * img_width))
    y2 = min(img_height, int(((label.bbox_y + label.bbox_height + padding_percent) / 100.0) * img_height))

    # Crop the image
    cropped = image.crop((x1, y1, x2, y2))

    return cropped


class ProcessingConfig(BaseModel):
    """Configuration for PDF processing"""
    vision_provider: str = "openai"
    pdf_dpi: int = 200
    equipment_filter: str = "all"


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # uploaded, processing, completed, failed, cancelled
    filename: str
    pages: Optional[int] = None
    current_page: Optional[int] = None
    labels_found: int = 0
    progress_percent: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_activity: Optional[str] = None
    processing_speed: Optional[float] = None  # pages per minute
    estimated_time_remaining: Optional[int] = None  # seconds


class LabelUpdate(BaseModel):
    """Label update request"""
    device_tag: Optional[str] = None
    equipment_type: Optional[str] = None
    fed_from: Optional[str] = None
    primary_from: Optional[str] = None
    alternate_from: Optional[str] = None
    specs: Optional[str] = None
    is_spare: Optional[bool] = None


@app.get("/")
async def root():
    """Root endpoint"""
    return FileResponse("web/frontend/index.html")


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    config: str = None
):
    """Upload PDF file"""
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are allowed")

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")

    # Get page count
    from pypdfium2 import PdfDocument
    try:
        pdf = PdfDocument(str(file_path))
        page_count = len(pdf)
        pdf.close()
    except Exception:
        page_count = None

    # Parse config or use defaults from settings
    if config:
        parsed_config = eval(config)
    else:
        parsed_config = {
            "vision_provider": settings.vision_provider,
            "pdf_dpi": settings.pdf_dpi
        }

    # Store job info
    jobs[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "status": "uploaded",
        "pages": page_count,
        "current_page": 0,
        "labels_found": 0,
        "labels": [],
        "config": parsed_config,
        "created_at": datetime.now().isoformat()
    }

    logger.info(f"Uploaded file: {file.filename} (Job: {job_id})")

    return {
        "job_id": job_id,
        "filename": file.filename,
        "pages": page_count,
        "status": "uploaded"
    }


async def process_pdf_job(job_id: str):
    """Background task to process PDF"""
    job = jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = "processing"
        job["started_at"] = datetime.now().isoformat()
        job["cancel_requested"] = False
        start_time = datetime.now()

        file_path = Path(job["file_path"])
        config = job["config"]

        # Get API key from settings
        api_key = (
            settings.anthropic_api_key
            if config["vision_provider"] == "anthropic"
            else settings.openai_api_key
        )

        # Create pipeline
        pipeline = LabelExtractionPipeline(
            vision_provider=config["vision_provider"],
            vision_api_key=api_key,
            pdf_dpi=config["pdf_dpi"],
            max_image_size=settings.max_image_size
        )

        # Process PDF with progress tracking
        output_excel = OUTPUT_DIR / f"{job_id}_labels.xlsx"

        # Get PDF page count
        from pypdfium2 import PdfDocument
        pdf_doc = PdfDocument(str(file_path))
        total_pages = len(pdf_doc)
        pdf_doc.close()

        job["pages"] = total_pages
        job["current_page"] = 0
        job["progress_percent"] = 0
        job["current_activity"] = "Converting PDF to images..."

        # Convert PDF to images first
        pdf_images = pipeline.pdf_converter.convert_to_images(file_path)

        # Save page images for preview
        job["current_activity"] = "Saving page previews..."
        job_image_dir = PAGE_IMAGES_DIR / job_id
        job_image_dir.mkdir(exist_ok=True)

        for page_num, img in enumerate(pdf_images, start=1):
            if job.get("cancel_requested"):
                raise Exception("Processing cancelled by user")
            img_path = job_image_dir / f"page_{page_num}.jpg"
            img.save(img_path, "JPEG", quality=85)

        # Process pages one by one with progress updates
        all_labels = []
        label_page_map = {}  # Track which page each label came from
        page_times = []

        for page_num, page_image in enumerate(pdf_images, start=1):
            # Check for cancellation
            if job.get("cancel_requested"):
                logger.info(f"Job {job_id} cancelled at page {page_num}/{total_pages}")
                break

            # Update progress
            page_start_time = datetime.now()
            job["current_page"] = page_num
            job["progress_percent"] = int((page_num / total_pages) * 90)  # Reserve 10% for Excel generation
            job["current_activity"] = f"Analyzing page {page_num}/{total_pages} with AI..."

            # Calculate processing speed and time remaining
            if page_times:
                avg_time_per_page = sum(page_times) / len(page_times)
                pages_remaining = total_pages - page_num + 1
                estimated_seconds = int(avg_time_per_page * pages_remaining)
                job["estimated_time_remaining"] = estimated_seconds
                job["processing_speed"] = round(60 / avg_time_per_page, 2) if avg_time_per_page > 0 else 0

            logger.info(f"Processing page {page_num}/{total_pages} for job {job_id}")

            # Extract labels from this page
            page_labels = pipeline.vision_analyzer.extract_labels(page_image)

            # Track processing time
            page_time = (datetime.now() - page_start_time).total_seconds()
            page_times.append(page_time)

            # Add page number to labels
            start_idx = len(all_labels)
            for idx, label in enumerate(page_labels):
                all_labels.append(label)
                label_page_map[start_idx + idx] = page_num

            job["labels_found"] = len(all_labels)
            job["current_activity"] = f"Found {len(page_labels)} labels on page {page_num}"

        # Set labels as processed
        labels = all_labels

        # Check if cancelled
        was_cancelled = job.get("cancel_requested", False)

        # Create annotated images and cropped labels
        if labels:
            job["current_activity"] = "Creating annotated images and label crops..."
            job["progress_percent"] = 92

            # Create job-specific directories
            job_annotated_dir = ANNOTATED_PAGES_DIR / job_id
            job_cropped_dir = CROPPED_LABELS_DIR / job_id
            job_annotated_dir.mkdir(exist_ok=True)
            job_cropped_dir.mkdir(exist_ok=True)

            # Draw bounding boxes on each page and save cropped labels
            for page_num, page_image in enumerate(pdf_images, start=1):
                # Draw bounding boxes on this page
                annotated_img = draw_bounding_boxes(page_image, labels, label_page_map, page_num)
                annotated_path = job_annotated_dir / f"page_{page_num}_annotated.jpg"
                annotated_img.save(annotated_path, "JPEG", quality=90)

            # Crop individual labels
            for idx, label in enumerate(labels):
                page_num = label_page_map.get(idx, 1)
                page_image = pdf_images[page_num - 1]

                cropped = crop_label_image(page_image, label)
                if cropped:
                    cropped_path = job_cropped_dir / f"label_{idx}.jpg"
                    cropped.save(cropped_path, "JPEG", quality=95)

        # Generate Excel with progress update (even for partial results)
        if labels:
            job["current_activity"] = "Generating Excel file..."
            job["progress_percent"] = 95
            excel_path = pipeline.excel_exporter.export_labels(labels, output_excel)
            job["progress_percent"] = 100
            job["excel_path"] = str(excel_path)

        # Store results with correct page numbers and bounding box info
        job["labels"] = [
            {
                "id": i,
                "equipment_type": label.equipment_type,
                "device_tag": label.device_tag,
                "fed_from": label.fed_from,
                "primary_from": label.primary_from,
                "alternate_from": label.alternate_from,
                "specs": label.specs,
                "is_spare": label.is_spare,
                "needs_breaker": label.needs_breaker,
                "image_page": label_page_map.get(i, 1),  # Use actual page number
                "has_bbox": all([label.bbox_x is not None, label.bbox_y is not None,
                                label.bbox_width is not None, label.bbox_height is not None])
            }
            for i, label in enumerate(labels)
        ]
        job["labels_found"] = len(labels)

        if was_cancelled:
            job["status"] = "cancelled"
            job["current_activity"] = f"Cancelled - Partial results available ({len(labels)} labels from {job['current_page']} pages)"
        else:
            job["status"] = "completed"
            job["current_activity"] = f"Complete - Extracted {len(labels)} labels from {total_pages} pages"

        job["completed_at"] = datetime.now().isoformat()
        job["progress_percent"] = 100

        logger.info(f"{'Cancelled' if was_cancelled else 'Completed'} job {job_id}: {len(labels)} labels")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)

        # Save partial results even on error
        if "labels" not in job or not job["labels"]:
            job["labels"] = []

        if "Processing cancelled" in str(e):
            job["status"] = "cancelled"
            job["current_activity"] = "Cancelled by user"
        else:
            job["status"] = "failed"
            job["error"] = str(e)
            job["current_activity"] = f"Failed: {str(e)}"

        job["completed_at"] = datetime.now().isoformat()


@app.post("/api/process/{job_id}")
async def start_processing(job_id: str, background_tasks: BackgroundTasks):
    """Start processing a job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] != "uploaded":
        raise HTTPException(400, f"Job already {job['status']}")

    # Add background task
    background_tasks.add_task(process_pdf_job, job_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Processing started"
    }


@app.get("/api/page-image/{job_id}/{page_num}")
async def get_page_image(job_id: str, page_num: int):
    """Get page image for preview"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    img_path = PAGE_IMAGES_DIR / job_id / f"page_{page_num}.jpg"

    if not img_path.exists():
        raise HTTPException(404, "Page image not found")

    return FileResponse(img_path, media_type="image/jpeg")


@app.get("/api/annotated-image/{job_id}/{page_num}")
async def get_annotated_image(job_id: str, page_num: int):
    """Get page image with bounding boxes drawn"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    img_path = ANNOTATED_PAGES_DIR / job_id / f"page_{page_num}_annotated.jpg"

    if not img_path.exists():
        raise HTTPException(404, "Annotated page image not found")

    return FileResponse(img_path, media_type="image/jpeg")


@app.get("/api/cropped-label/{job_id}/{label_id}")
async def get_cropped_label(job_id: str, label_id: int):
    """Get cropped label image"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    img_path = CROPPED_LABELS_DIR / job_id / f"label_{label_id}.jpg"

    if not img_path.exists():
        raise HTTPException(404, "Cropped label image not found")

    return FileResponse(img_path, media_type="image/jpeg")


@app.post("/api/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a processing job"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] != "processing":
        raise HTTPException(400, f"Cannot cancel job with status: {job['status']}")

    job["cancel_requested"] = True
    logger.info(f"Cancel requested for job {job_id}")

    return {
        "job_id": job_id,
        "message": "Cancellation requested. Processing will stop after current page."
    }


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job_id,
        "status": job["status"],
        "filename": job["filename"],
        "pages": job.get("pages"),
        "current_page": job.get("current_page", 0),
        "labels_found": job.get("labels_found", 0),
        "progress_percent": job.get("progress_percent", 0),
        "error": job.get("error"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "current_activity": job.get("current_activity"),
        "processing_speed": job.get("processing_speed"),
        "estimated_time_remaining": job.get("estimated_time_remaining")
    }


@app.get("/api/labels/{job_id}")
async def get_labels(job_id: str):
    """Get extracted labels"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Allow access to labels for completed, cancelled, or failed jobs with partial results
    if job["status"] not in ["completed", "cancelled", "failed"]:
        raise HTTPException(400, f"Job is {job['status']}, labels not available yet")

    return {
        "job_id": job_id,
        "labels": job.get("labels", []),
        "status": job["status"]
    }


@app.put("/api/labels/{job_id}/{label_id}")
async def update_label(job_id: str, label_id: int, update: LabelUpdate):
    """Update a label"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    labels = job.get("labels", [])
    if label_id >= len(labels):
        raise HTTPException(404, "Label not found")

    # Update label fields
    label = labels[label_id]
    if update.device_tag is not None:
        label["device_tag"] = update.device_tag
    if update.equipment_type is not None:
        label["equipment_type"] = update.equipment_type
    if update.fed_from is not None:
        label["fed_from"] = update.fed_from
    if update.primary_from is not None:
        label["primary_from"] = update.primary_from
    if update.alternate_from is not None:
        label["alternate_from"] = update.alternate_from
    if update.specs is not None:
        label["specs"] = update.specs
    if update.is_spare is not None:
        label["is_spare"] = update.is_spare

    return {"success": True, "label": label}


@app.delete("/api/labels/{job_id}/{label_id}")
async def delete_label(job_id: str, label_id: int):
    """Delete a label"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    labels = job.get("labels", [])
    if label_id >= len(labels):
        raise HTTPException(404, "Label not found")

    deleted = labels.pop(label_id)
    job["labels_found"] = len(labels)

    return {"success": True, "deleted": deleted}


@app.get("/api/export/{job_id}")
async def export_excel(job_id: str):
    """Download Excel file"""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    # Allow export for completed or cancelled jobs (partial results)
    if job["status"] not in ["completed", "cancelled"]:
        raise HTTPException(400, f"Cannot export - job status is {job['status']}")

    excel_path = job.get("excel_path")
    if not excel_path or not Path(excel_path).exists():
        raise HTTPException(404, "Excel file not found")

    # Add suffix for partial results
    suffix = "_partial" if job["status"] == "cancelled" else ""
    filename = f"{job['filename'].replace('.pdf', '')}{suffix}_labels.xlsx"

    return FileResponse(
        excel_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs"""
    return {
        "jobs": [
            {
                "job_id": job_id,
                "filename": job["filename"],
                "status": job["status"],
                "labels_found": job.get("labels_found", 0),
                "created_at": job.get("created_at")
            }
            for job_id, job in jobs.items()
        ]
    }


# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
