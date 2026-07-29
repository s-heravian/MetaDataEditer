# Metadata Extractor

A containerized tool for safely extracting and anonymizing metadata from files. 

## Features
- Complete removal of unnecessary, tracking, and device-specific EXIF/XMP metadata.
- Automatic detection of specific geographic footprints (e.g., Iran) based on keywords, GPS, and Timezones.
- Automatic spoofing to a safe zone (Berlin, Germany), including dynamic calculation of Daylight Saving Time (DST) offsets.
- Simple, beautiful, drag-and-drop web interface.
- Fully containerized (Backend: FastAPI + ExifTool, Frontend: Nginx).

## Requirements
- Docker
- Docker Compose

## Getting Started
1. Clone this repository.
2. In the root directory, run:
   ```bash
   docker compose up -d --build
   ```
3. Open your browser and navigate to `http://localhost:8080`.

## Architecture
- **Backend:** Python (FastAPI) wrapped around ExifTool for highly reliable metadata manipulation.
- **Frontend:** Vanilla HTML/JS/CSS served via Nginx.
- **Volumes:** Uses Docker volumes to safely manage uploaded files during processing.
