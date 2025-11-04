#!/usr/bin/env python3
"""
Web Server Launcher
Starts the FastAPI web interface for Electrical Label Extractor
"""
import uvicorn
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("=" * 60)
    print("Electrical Label Extractor - Web Interface")
    print("=" * 60)
    print()
    print("Starting web server...")
    print("Access the application at: http://localhost:8000")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Run uvicorn
    uvicorn.run(
        "web.backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
