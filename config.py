"""
Configuration settings for Electrical Label Extraction MVP
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Vision AI Provider
    vision_provider: Literal["openai", "anthropic"] = "anthropic"
    openai_model: str = "gpt-4-vision-preview"
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # OCR Settings
    ocr_language: str = "en"
    ocr_use_gpu: bool = False

    # Processing Settings
    max_image_size: int = 2048
    pdf_dpi: int = 300

    # Output Settings
    output_dir: Path = Path("./output")
    temp_dir: Path = Path("./temp")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)


# Equipment type definitions
EQUIPMENT_NEEDS_BREAKER_LABELS = [
    "MSB",  # Main Switchboard
    "GSB",  # Switchboard
    "MVS",  # Medium Voltage Switchgear
    "DSG",  # Medium Voltage
    "GENAH", "GENBH",  # House Generators
    "MDP",  # Main Distribution Panel
    "UDP",  # Unit Distribution Panel
    "MBC",
    "PDU",
    "EPP",  # Some EPP types (EPPAZ, EPPBZ, EPPCZ)
    "HUM",  # Humidifiers (Disconnect switch)
    "CONDENSER",  # Condensers
]

EQUIPMENT_NO_BREAKER_LABELS = [
    "TRN",  # Transformers (unless breakers shown)
    "UPS",
    "UPB",
    "ATS",
    "RPP",
    "ELP",
]

# Label formatting rules
LABEL_FORMAT = {
    "max_lines": 4,
    "min_lines": 2,
    "line_1": "Device Tag (e.g., EDC ATL11 MSBBA110)",
    "line_2": "FED FROM (if applicable)",
    "line_3": "AMPS, VOLTS",
    "line_4": "ALTERNATE FROM (optional)",
}


# Global settings instance
settings = Settings()
