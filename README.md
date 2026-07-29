# Metadata Editer & Spoofer

A containerized, high-performance forensic tool for safely extracting, anonymizing, and spoofing metadata from files. It ensures total privacy by wiping hidden geographic and system footprints (EXIF, XMP, PDF dictionaries) and replacing them with untraceable, realistic European identities.

## ✨ Features
- **Total Metadata Wiping:** Safely strips out tracking, device-specific, and unnecessary EXIF/XMP metadata from files (Images, PDFs, etc.).
- **Smart Geographic Detection:** Automatically detects footprints indicating an origin from Iran (keywords, GPS bounding boxes, timezones).
- **Multi-Country Spoofing:** Injects flawless, realistic metadata (Coordinates, exact Timezone Offsets with DST logic, Language Codes) for any selected target country:
  - 🇩🇪 Germany (Berlin)
  - 🇫🇷 France (Paris)
  - 🇬🇧 United Kingdom (London)
  - 🇳🇱 Netherlands (Amsterdam)
  - 🇮🇹 Italy (Rome)
- **Deep Forensic Hardening:** Unlike basic tools, it dives into nested PDF dictionaries and uses isolated Docker container timezones to perfectly sync system-level file attributes (like `ModifyDate`) to the target country.
- **Dynamic File Regeneration:** Generate multiple spoofed versions of the same file securely without overwriting the original file on the server.
- **Clean Naming:** Automatically assigns unique IDs to downloaded files, guaranteeing no trace of original names (e.g., Persian characters or internal IDs).

---

## 🛠️ Requirements
- Docker
- Docker Compose

---

## 🚀 Implementation & Deployment Guide

You can run this project locally or deploy it on a VPS. It uses a FastAPI backend and a Vanilla JS/CSS frontend served via Nginx.

### 1. Local Deployment (Development / Testing)
Clone the repository and run the pre-configured docker-compose:
```bash
git clone https://github.com/s-heravian/MetaDataEditer.git
cd MetaDataEditer
docker compose up -d --build
```
Navigate to `http://localhost:8080` in your web browser.

### 2. Production Deployment using GitHub Container Registry (GHCR)
This repository uses GitHub Actions to automatically build and publish Docker images to GHCR upon a new Release.

**Steps to deploy using published images on your server:**
1. Generate a **Personal Access Token (PAT)** in GitHub with `read:packages` permissions.
2. Login to GHCR on your server:
   ```bash
   echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u s-heravian --password-stdin
   ```
3. Run the project using the production compose file:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

---

## 🏗️ Architecture
- **Backend (`/backend`):** Python (FastAPI). Uses a `subprocess` wrapper around ExifTool. Timezone environments are strictly sandboxed per-request to trick ExifTool's system hooks.
- **Frontend (`/frontend`):** Sleek, glassmorphism UI built with Vanilla HTML/JS/CSS. Hosted on an ultra-light Nginx Alpine container.
- **Volumes:** Uses a persistent Docker volume (`uploads_data`) to safely manage original and processed files temporarily. Background workers and cleanup APIs ensure files are deleted efficiently.
