"""
OCR Text Extraction Engine
Uses PaddleOCR to extract text with bounding boxes
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextBox:
    """Represents detected text with its bounding box"""
    text: str
    confidence: float
    bbox: List[Tuple[int, int]]  # [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]

    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of bounding box"""
        x_coords = [p[0] for p in self.bbox]
        y_coords = [p[1] for p in self.bbox]
        return (
            int(sum(x_coords) / len(x_coords)),
            int(sum(y_coords) / len(y_coords))
        )

    @property
    def min_x(self) -> int:
        return min(p[0] for p in self.bbox)

    @property
    def max_x(self) -> int:
        return max(p[0] for p in self.bbox)

    @property
    def min_y(self) -> int:
        return min(p[1] for p in self.bbox)

    @property
    def max_y(self) -> int:
        return max(p[1] for p in self.bbox)


class OCRExtractor:
    """Extract text from images using PaddleOCR"""

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        """
        Initialize OCR engine

        Args:
            lang: Language code (default: "en")
            use_gpu: Whether to use GPU acceleration
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr = None

    def _initialize_ocr(self):
        """Lazy initialization of PaddleOCR"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR

                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
                logger.info("PaddleOCR initialized successfully")
            except ImportError:
                raise ImportError(
                    "PaddleOCR not installed. Install with: pip install paddleocr"
                )

    def extract_text(self, image: Image.Image) -> List[TextBox]:
        """
        Extract all text from image with bounding boxes

        Args:
            image: PIL Image object

        Returns:
            List of TextBox objects containing text and coordinates
        """
        self._initialize_ocr()

        # Convert PIL Image to numpy array
        img_array = np.array(image)

        logger.info("Running OCR extraction...")

        try:
            # Run OCR
            result = self._ocr.ocr(img_array, cls=True)

            if not result or result[0] is None:
                logger.warning("No text detected by OCR")
                return []

            # Parse results into TextBox objects
            text_boxes = []
            for line in result[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)

                text = text_info[0]
                confidence = text_info[1]

                # Convert bbox to list of tuples
                bbox_tuples = [(int(p[0]), int(p[1])) for p in bbox]

                text_box = TextBox(
                    text=text,
                    confidence=confidence,
                    bbox=bbox_tuples
                )
                text_boxes.append(text_box)

            logger.info(f"Extracted {len(text_boxes)} text boxes")
            return text_boxes

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise

    def extract_text_simple(self, image: Image.Image) -> str:
        """
        Extract all text as a single string (no bounding boxes)

        Args:
            image: PIL Image object

        Returns:
            Concatenated text string
        """
        text_boxes = self.extract_text(image)
        return "\n".join([tb.text for tb in text_boxes])

    def filter_by_confidence(
        self, text_boxes: List[TextBox], min_confidence: float = 0.5
    ) -> List[TextBox]:
        """
        Filter text boxes by confidence threshold

        Args:
            text_boxes: List of TextBox objects
            min_confidence: Minimum confidence (0-1)

        Returns:
            Filtered list of TextBox objects
        """
        return [tb for tb in text_boxes if tb.confidence >= min_confidence]

    def group_nearby_text(
        self, text_boxes: List[TextBox], max_distance: int = 50
    ) -> List[List[TextBox]]:
        """
        Group text boxes that are close to each other (for multi-line labels)

        Args:
            text_boxes: List of TextBox objects
            max_distance: Maximum distance between boxes to group

        Returns:
            List of text box groups
        """
        if not text_boxes:
            return []

        # Sort by vertical position (top to bottom)
        sorted_boxes = sorted(text_boxes, key=lambda tb: tb.min_y)

        groups = []
        current_group = [sorted_boxes[0]]

        for box in sorted_boxes[1:]:
            # Check if box is close to the last box in current group
            last_box = current_group[-1]
            distance = abs(box.min_y - last_box.max_y)

            if distance <= max_distance:
                current_group.append(box)
            else:
                groups.append(current_group)
                current_group = [box]

        # Add last group
        if current_group:
            groups.append(current_group)

        return groups
