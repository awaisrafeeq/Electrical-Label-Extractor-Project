"""
Vision AI Analyzer
Uses Claude Vision or GPT-4 Vision to intelligently extract labels
"""
from dataclasses import dataclass
from typing import List, Optional, Literal
from PIL import Image
import base64
import io
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class LabelData:
    """Structured label information"""
    equipment_type: str  # e.g., "MSB", "MDP", "UDP"
    device_tag: str  # Line 1: e.g., "EDC ATL11 MSBBA110"
    fed_from: Optional[str] = None  # Line 2: "FED FROM MSBAA110"
    primary_from: Optional[str] = None  # For 4-line labels
    alternate_from: Optional[str] = None  # For 4-line labels
    specs: Optional[str] = None  # Line 3/4: "600A 480Y/277V"
    is_spare: bool = False
    needs_breaker: bool = True
    confidence: float = 0.0
    # Bounding box coordinates (as percentages of image dimensions: 0-100)
    bbox_x: Optional[float] = None  # X position (left edge) as % of width
    bbox_y: Optional[float] = None  # Y position (top edge) as % of height
    bbox_width: Optional[float] = None  # Width as % of image width
    bbox_height: Optional[float] = None  # Height as % of image height


class VisionAnalyzer:
    """Analyze electrical diagrams using Vision AI"""

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "anthropic",
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize Vision AI analyzer

        Args:
            provider: "openai" or "anthropic"
            api_key: API key for the provider
            model: Model name (optional, uses defaults)
        """
        self.provider = provider
        self.api_key = api_key

        if provider == "openai":
            self.model = model or "gpt-4o"
            self._init_openai()
        else:  # anthropic
            # Try multiple model names for compatibility
            self.model = model or "claude-3-haiku-20240307"  # Working model for this API key
            self._init_anthropic()

    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAI client initialized with model: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed")

    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"Anthropic client initialized with model: {self.model}")
        except ImportError:
            raise ImportError("anthropic package not installed")

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def _build_extraction_prompt(self) -> str:
        """Build the prompt for label extraction"""
        return """You are an expert electrical engineer analyzing one-line electrical diagrams.

Your task is to identify and extract all equipment labels from this electrical drawing.

EQUIPMENT TYPES THAT NEED BREAKER LABELS:
- MSB (Main Switchboard)
- GSB (Switchboard)
- MVS, DSG (Medium Voltage - 4 lines of text)
- GENAH, GENBH (House Generators - has breaker for ATS and loadbank)
- MDP (Main Distribution Panel)
- UDP (Unit Distribution Panel)
- MBC, PDU
- EPP variants (EPPAZ, EPPBZ, EPPCZ)
- HUM (Humidifiers - label on Disconnect switch)
- CONDENSER

EQUIPMENT THAT DOES NOT NEED BREAKER LABELS:
- TRN (Transformers - unless breakers shown)
- UPS, UPB, ATS, RPP, ELP

CRITICAL LABEL FORMATTING RULES:

For equipment with SINGLE FEED source:
- fed_from: Just the source equipment name (e.g., "MSBAA110")
- primary_from: null
- alternate_from: null

For equipment with DUAL FEED (primary + alternate):
- fed_from: null
- primary_from: Primary source equipment name (e.g., "TRNAA110")
- alternate_from: Alternate source equipment name (e.g., "GSBAA110")

EXAMPLES:

Single feed example:
{
  "equipment_type": "MDP",
  "device_tag": "EDC ATL11 MDPAA110",
  "fed_from": "MSBAA110",
  "primary_from": null,
  "alternate_from": null,
  "specs": "600A 480Y/277V"
}

Dual feed example:
{
  "equipment_type": "MSB",
  "device_tag": "EDC ATL11 MSBAA110",
  "fed_from": null,
  "primary_from": "TRNAA110",
  "alternate_from": "GSBAA110",
  "specs": "4000A 480Y/277V"
}

IMPORTANT RULES:
1. Extract ONLY the equipment name/tag for connections (e.g., "MSBAA110", NOT "FED FROM MSBAA110")
2. Do NOT include "FED FROM" or "PRIMARY FROM" in the field values - just the equipment name
3. For single connections, use "fed_from" field only
4. For dual connections, use "primary_from" and "alternate_from" fields only
5. NEVER use both "fed_from" and "primary_from" for the same equipment
6. "specs" should contain ONLY voltage and amperage (e.g., "600A 480Y/277V")

SPARE BREAKER DETECTION:
A breaker is SPARE if:
- Labeled as "SPARE", "FUTURE", "RESERVED"
- No downstream equipment connected
- Empty breaker position in panel
- Device tag contains "SPARE" or "SP"

When you find a SPARE:
{
  "equipment_type": "SPARE",
  "device_tag": "EDC ATL11 SPARE-01" (or original label),
  "is_spare": true,
  "specs": "Breaker rating if shown (e.g., 100A 480V)"
}

INSTRUCTIONS:
1. Identify all equipment symbols in the diagram
2. For each equipment that needs a label, extract the device tag
3. **CHECK FOR SPARE BREAKERS** - Look for "SPARE", "FUTURE", empty positions
4. Trace feeder lines to determine what feeds what
5. Extract voltage and amperage specifications
6. Mark is_spare: true for all spare/future/reserved breakers
7. Return structured JSON data

BOUNDING BOX COORDINATES - VERY IMPORTANT:
For each label you extract, you MUST provide ACCURATE bounding box coordinates:
- bbox_x: X position of left edge (0-100, as % of image width)
- bbox_y: Y position of top edge (0-100, as % of image height)
- bbox_width: Width of label box (0-100, as % of image width)
- bbox_height: Height of label box (0-100, as % of image height)

CRITICAL BOUNDING BOX RULES:
1. The bounding box must TIGHTLY surround the equipment label text
2. DO NOT include empty space, wires, or other diagram elements in the box
3. The box should ONLY contain the label text itself (device tag, fed from, specs, etc.)
4. Be PRECISE - measure the actual label position carefully
5. If you cannot accurately locate a label, DO NOT guess - omit the bbox fields

Example: If a label "EDC ATL11 MSBAA110" is at 25% from left, 15% from top, and takes up 12% width x 8% height:
{
  "bbox_x": 25.0,
  "bbox_y": 15.0,
  "bbox_width": 12.0,
  "bbox_height": 8.0
}

Return a JSON array in this EXACT format:
{
  "labels": [
    {
      "equipment_type": "MSB",
      "device_tag": "EDC ATL11 MSBBA110",
      "fed_from": null,
      "primary_from": "TRNAA110",
      "alternate_from": "GSBAA110",
      "specs": "4000A 480Y/277V",
      "is_spare": false,
      "needs_breaker": true,
      "bbox_x": 25.0,
      "bbox_y": 15.0,
      "bbox_width": 12.0,
      "bbox_height": 8.0
    }
  ]
}

Return ONLY valid JSON, no other text before or after."""

    def extract_labels(self, image: Image.Image) -> List[LabelData]:
        """
        Extract labels from electrical diagram using Vision AI

        Args:
            image: PIL Image of electrical diagram

        Returns:
            List of LabelData objects
        """
        logger.info(f"Analyzing image with {self.provider} Vision AI...")

        try:
            if self.provider == "openai":
                result = self._extract_with_openai(image)
            else:
                result = self._extract_with_anthropic(image)

            return result

        except Exception as e:
            logger.error(f"Vision AI extraction failed: {e}")
            raise

    def _extract_with_anthropic(self, image: Image.Image) -> List[LabelData]:
        """Extract labels using Claude Vision"""
        img_base64 = self._image_to_base64(image)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": self._build_extraction_prompt()
                        }
                    ],
                }
            ],
        )

        # Parse response
        response_text = response.content[0].text
        logger.debug(f"Claude response: {response_text}")

        return self._parse_json_response(response_text)

    def _extract_with_openai(self, image: Image.Image) -> List[LabelData]:
        """Extract labels using GPT-4 Vision"""
        img_base64 = self._image_to_base64(image)

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self._build_extraction_prompt()
                        }
                    ],
                }
            ],
        )

        response_text = response.choices[0].message.content
        logger.debug(f"GPT-4 response: {response_text}")

        return self._parse_json_response(response_text)

    def _parse_json_response(self, response_text: str) -> List[LabelData]:
        """Parse JSON response into LabelData objects"""
        try:
            # Extract JSON from response (may have markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            data = json.loads(json_str)

            labels = []
            for item in data.get("labels", []):
                label = LabelData(
                    equipment_type=item.get("equipment_type", "UNKNOWN"),
                    device_tag=item.get("device_tag", ""),
                    fed_from=item.get("fed_from"),
                    primary_from=item.get("primary_from"),
                    alternate_from=item.get("alternate_from"),
                    specs=item.get("specs"),
                    is_spare=item.get("is_spare", False),
                    needs_breaker=item.get("needs_breaker", True),
                    confidence=1.0,  # Vision AI doesn't provide confidence scores
                    bbox_x=item.get("bbox_x"),
                    bbox_y=item.get("bbox_y"),
                    bbox_width=item.get("bbox_width"),
                    bbox_height=item.get("bbox_height")
                )
                labels.append(label)

            logger.info(f"Extracted {len(labels)} labels from response")
            return labels

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {response_text}")
            return []
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return []
