import os
import subprocess
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import re
import datetime

app = FastAPI(title="Metadata Extractor API")

# Setup CORS to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a file and returns a unique file ID."""
    try:
        file_id = str(uuid.uuid4())
        # Preserve original extension
        ext = os.path.splitext(file.filename)[1]
        filename = f"{file_id}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"file_id": file_id, "filename": file.filename, "saved_path": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metadata/{file_name}")
async def get_metadata(file_name: str):
    """Extracts and returns metadata for the given file using ExifTool."""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Run exiftool command: exiftool -j <file>
        # -j outputs in JSON format
        # -G outputs group names (e.g. EXIF, XMP, File)
        # Set timezone to Europe/Berlin to avoid exposing the server's local timezone (+03:30) 
        # in file system metadata like FileModifyDate and FileAccessDate.
        env = os.environ.copy()
        env['TZ'] = 'Europe/Berlin'
        
        result = subprocess.run(
            ["exiftool", "-j", "-G", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        if result.returncode != 0 and result.stderr:
            # Note: exiftool sometimes returns non-zero for minor warnings, 
            # but usually stdout will have the json if it succeeded partially.
            pass

        metadata = json.loads(result.stdout)
        
        # Exiftool returns a list of dictionaries, one per file. We only passed one file.
        if isinstance(metadata, list) and len(metadata) > 0:
            return metadata[0]
        else:
            return {}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract metadata: {str(e)}")

@app.delete("/cleanup/{file_name}")
async def cleanup_file(file_name: str):
    """Deletes the file from the server."""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "success", "message": "File deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")

def is_iran_related(metadata: dict) -> bool:
    """Checks if any metadata value relates to Iran (GPS, timezone, keywords)."""
    iran_keywords = [
        r'\biran\b', r'\btehran\b', r'\+03:30\b', r'\+04:30\b',
        r'asia/tehran\b', r'\birst\b', r'\birdt\b', r'\biri\b',
        r'islamic republic of iran\b',
        r'\bfa\b', r'\bfa-ir\b', r'\bfas\b', r'\bper\b', r'\bpersian\b',
        r'\bmashhad\b', r'\bisfahan\b', r'\bshiraz\b', r'\btabriz\b', r'\bkaraj\b',
        r'\bir\b', r'\+98\b', r'\b0098\b',
        r'\btic\b', r'\bmci\b', r'\birancell\b'
    ]
    pattern = re.compile("|".join(iran_keywords), re.IGNORECASE)
    
    def search_dict(d):
        for k, v in d.items():
            if isinstance(v, str) and pattern.search(v):
                return True
            if isinstance(v, dict) and search_dict(v):
                return True
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and pattern.search(item):
                        return True
                    if isinstance(item, dict) and search_dict(item):
                        return True
            
            # GPS Check
            if k in ['GPSLatitude', 'GPSLongitude'] and isinstance(v, (int, float, str)):
                try:
                    val = float(v)
                    # Rough bounding box for Iran: Lat 25 to 40, Lon 44 to 64
                    if k == 'GPSLatitude' and (25.0 <= val <= 40.0):
                        # We would need both, but if it has a latitude in this range and longitude in this range
                        # it's better to check both. For simplicity, we just check if it matches the general area.
                        pass # It's better to check them together
                except:
                    pass

        # GPS exact check if both are present in the dictionary
        try:
            lat = float(d.get('GPSLatitude', 0))
            lon = float(d.get('GPSLongitude', 0))
            if (25.0 <= lat <= 40.0) and (44.0 <= lon <= 64.0):
                return True
        except:
            pass
            
        return False

    return search_dict(metadata)

def get_germany_offset(date_str) -> str:
    """Calculates Germany timezone offset considering DST based on the given date string."""
    month = datetime.datetime.now().month
    if date_str and isinstance(date_str, str):
        try:
            # Exiftool date format: "YYYY:MM:DD HH:MM:SS" or similar
            date_part = date_str.split(' ')[0]
            month = int(date_part.split(':')[1])
        except:
            pass
    # Germany DST approximation: April to October (inclusive 4 to 10)
    if 4 <= month <= 10:
        return "+02:00"
    return "+01:00"

@app.get("/process/{file_name}")
async def process_file(file_name: str):
    """Processes the file to remove unnecessary metadata and change Iran to Germany if needed."""
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # 1. Read metadata
        result = subprocess.run(["exiftool", "-j", file_path], stdout=subprocess.PIPE, text=True)
        metadata = json.loads(result.stdout) if result.stdout else [{}]
        file_metadata = metadata[0] if isinstance(metadata, list) and len(metadata) > 0 else {}
        
        has_iran = is_iran_related(file_metadata)
        
        # Get appropriate Germany timezone offset (handling DST)
        date_str = file_metadata.get('DateTimeOriginal') or file_metadata.get('CreateDate') or file_metadata.get('ModifyDate') or file_metadata.get('FileModifyDate')
        germany_offset = get_germany_offset(date_str)
        
        # 2. Strip all metadata (keeps the original file safe in a temp way, but we use -overwrite_original)
        subprocess.run(["exiftool", "-all=", "-overwrite_original", file_path], check=True)
        
        # 3. If Iran detected, add Germany metadata
        if has_iran:
            # Berlin coordinates and timezone
            subprocess.run([
                "exiftool", 
                "-GPSLatitude=52.5200", 
                "-GPSLongitude=13.4050",
                "-GPSLatitudeRef=N",
                "-GPSLongitudeRef=E",
                "-TimeZone=Europe/Berlin",
                f"-OffsetTime={germany_offset}",
                f"-OffsetTimeOriginal={germany_offset}",
                f"-OffsetTimeDigitized={germany_offset}",
                "-Country=Germany",
                "-CountryCode=DE",
                "-Language=de-DE",
                "-overwrite_original", 
                file_path
            ], check=True)
            
        return FileResponse(file_path, media_type='application/octet-stream', filename=f"processed_{file_name}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
