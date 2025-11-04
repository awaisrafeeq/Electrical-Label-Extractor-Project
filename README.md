# Electrical Label Extraction MVP

AI-powered tool to extract equipment labels from electrical drawings and export to Excel.

## Overview

This tool uses Vision AI (Claude or GPT-4 Vision) combined with OCR to automatically identify and extract electrical equipment labels from PDF drawings or images.

**Current Status:** Milestone 1 - Single Image Prototype

## Features

- Extract labels from electrical diagrams (PDF or images)
- Support for multiple equipment types (MSB, MDP, UDP, etc.)
- Intelligent label formatting (2-4 lines)
- Excel export with summary statistics
- CLI tool for easy testing

## Installation

### Prerequisites

- Python 3.10 or higher
- Poppler (for PDF processing)

**Install Poppler:**

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
```

### Setup

1. Clone or navigate to the project directory

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env and add your API key:
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
# OPENAI_API_KEY=sk-your-key-here
```

## Usage

### Process Single Image

```bash
python main.py image circuit_page.png
```

### Process PDF (Single Page)

```bash
python main.py pdf drawing.pdf --page 1
```

### Process Entire PDF

```bash
python main.py pdf drawing.pdf
```

### Process PDF Page Range

```bash
python main.py pdf drawing.pdf --start-page 1 --end-page 5
```

### Batch Process Directory

```bash
python main.py batch input_pdfs/ output_excel/
```

### Custom Output Path

```bash
python main.py image circuit.png -o custom_output.xlsx
```

## Equipment Types Supported

### Needs Breaker Labels:
- MSB (Main Switchboard)
- GSB (Switchboard)
- MVS, DSG (Medium Voltage)
- GENAH, GENBH (House Generators)
- MDP (Main Distribution Panel)
- UDP (Unit Distribution Panel)
- MBC, PDU
- EPP variants (EPPAZ, EPPBZ, EPPCZ)
- HUM (Humidifiers)
- CONDENSER

### Does NOT Need Breaker Labels:
- TRN (Transformers)
- UPS, UPB, ATS, RPP, ELP

## Label Format

Labels are extracted in 2-4 line format:

**3-line example:**
```
EDC ATL11 MDPAA110
FED FROM MSBAA110
600A 480Y/277V
```

**4-line example:**
```
EDC ATL11 MSBAA110
PRIMARY FROM TRNAA110
ALTERNATE FROM GSBAA110
4000A 480Y/277V
```

## Output

Excel file with:
- **Labels Sheet:** All extracted labels with formatting
- **Summary Sheet:** Statistics and equipment type breakdown

## Configuration

Edit `config.py` or `.env` file:

- `VISION_PROVIDER`: "anthropic" or "openai"
- `PDF_DPI`: Resolution for PDF conversion (default: 300)
- `MAX_IMAGE_SIZE`: Maximum image dimension
- `OUTPUT_DIR`: Directory for output files

## Project Structure

```
MVP/
├── main.py                 # CLI tool
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── src/
│   ├── pdf_processor/      # PDF to image conversion
│   ├── ocr_engine/         # OCR text extraction
│   ├── vision_ai/          # Vision AI analysis
│   ├── excel_exporter/     # Excel generation
│   └── pipeline.py         # Main processing pipeline
├── output/                 # Generated Excel files
└── temp/                   # Temporary files
```

## Milestones

- [x] **Milestone 1:** Single image prototype (Week 1)
- [ ] **Milestone 2:** Full PDF extraction (Week 2)
- [ ] **Milestone 3:** Web deployment (Week 3)
- [ ] **Milestone 4:** Testing & refinement (Week 4)

## Development

### Run Tests

```bash
pytest
```

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Costs

Approximate costs per page:
- **Anthropic (Claude Vision):** ~$0.01-0.03
- **OpenAI (GPT-4 Vision):** ~$0.01-0.05

## Troubleshooting

**Issue:** `pdf2image` not working
- **Solution:** Install Poppler (see Prerequisites)

**Issue:** OCR not detecting text
- **Solution:** Increase PDF_DPI to 400-600

**Issue:** Vision AI not extracting labels
- **Solution:** Check API key in `.env` file

## License

Proprietary - Client Project

## Support

For issues or questions, contact the development team.

---

**Version:** 0.1.0 (Milestone 1)
**Last Updated:** 2025-10-21
