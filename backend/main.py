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

EUROPEAN_COUNTRIES = {
    "DE": {
        "name": "Germany", "lat": "52.5200", "lon": "13.4050", "tz": "Europe/Berlin", "lang": "de-DE", "std_offset": "+01:00", "dst_offset": "+02:00"
    },
    "FR": {
        "name": "France", "lat": "48.8566", "lon": "2.3522", "tz": "Europe/Paris", "lang": "fr-FR", "std_offset": "+01:00", "dst_offset": "+02:00"
    },
    "GB": {
        "name": "United Kingdom", "lat": "51.5074", "lon": "-0.1278", "tz": "Europe/London", "lang": "en-GB", "std_offset": "+00:00", "dst_offset": "+01:00"
    },
    "NL": {
        "name": "Netherlands", "lat": "52.3676", "lon": "4.9041", "tz": "Europe/Amsterdam", "lang": "nl-NL", "std_offset": "+01:00", "dst_offset": "+02:00"
    },
    "IT": {
        "name": "Italy", "lat": "41.9028", "lon": "12.4964", "tz": "Europe/Rome", "lang": "it-IT", "std_offset": "+01:00", "dst_offset": "+02:00"
    }
}

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

def get_country_offset(date_str, country_code: str) -> str:
    """Calculates country timezone offset considering DST based on the given date string."""
    month = datetime.datetime.now().month
    if date_str and isinstance(date_str, str):
        try:
            # Exiftool date format: "YYYY:MM:DD HH:MM:SS" or similar
            date_part = date_str.split(' ')[0]
            month = int(date_part.split(':')[1])
        except:
            pass
            
    country_data = EUROPEAN_COUNTRIES.get(country_code, EUROPEAN_COUNTRIES["DE"])
    # Europe DST approximation: April to October (inclusive 4 to 10)
    if 4 <= month <= 10:
        return country_data["dst_offset"]
    return country_data["std_offset"]

@app.get("/process/{file_name}")
async def process_file(file_name: str, target_country: str = 'DE'):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Check unsupported formats
    unsupported_exts = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    ext = os.path.splitext(file_name)[1].lower()
    if ext in unsupported_exts:
        raise HTTPException(status_code=400, detail="متاسفانه هسته پردازشی (ExifTool) از ویرایش و حذف متادیتا روی فایل‌های Office (مانند Word و Excel) پشتیبانی نمی‌کند. این فایل‌ها فقط قابلیت خواندن دارند.")

    try:
        # Create a copy for processing
        processed_path = os.path.join(UPLOAD_DIR, f"processed_{file_name}")
        shutil.copy(file_path, processed_path)
        
        if target_country not in EUROPEAN_COUNTRIES:
            target_country = "DE"
        country_data = EUROPEAN_COUNTRIES[target_country]

        # Dynamically set container environment timezone for Exiftool processes
        env = os.environ.copy()
        env['TZ'] = country_data['tz']
        
        # 1. Read metadata from original (with -G to get exact groups like PDF:ModifyDate)
        result = subprocess.run(["exiftool", "-j", "-G", file_path], stdout=subprocess.PIPE, text=True, env=env)
        metadata = json.loads(result.stdout) if result.stdout else [{}]
        file_metadata = metadata[0] if isinstance(metadata, list) and len(metadata) > 0 else {}
        
        has_iran = is_iran_related(file_metadata)
        
        # Get appropriate timezone offset (handling DST)
        # Check standard date keys (now they might have group prefixes like XMP:CreateDate)
        date_str = None
        for key in ['EXIF:DateTimeOriginal', 'XMP:CreateDate', 'PDF:CreateDate', 'System:ModifyDate', 'File:FileModifyDate']:
            if key in file_metadata:
                date_str = file_metadata[key]
                break
        
        country_offset = get_country_offset(date_str, target_country)
        
        # 2. Strip all metadata
        subprocess.run(["exiftool", "-all=", "-overwrite_original", processed_path], check=True, env=env)
        
        # 3. If Iran detected, add spoofed metadata
        if has_iran:
            lon_str = country_data['lon']
            lon_ref = 'W' if lon_str.startswith('-') else 'E'
            lon_val = lon_str.replace('-', '')
            
            exif_cmd = [
                "exiftool", 
                f"-GPSLatitude={country_data['lat']}", 
                f"-GPSLongitude={lon_val}",
                "-GPSLatitudeRef=N",
                f"-GPSLongitudeRef={lon_ref}",
                f"-TimeZone={country_data['tz']}",
                f"-OffsetTime={country_offset}",
                f"-OffsetTimeOriginal={country_offset}",
                f"-OffsetTimeDigitized={country_offset}",
                f"-Country={country_data['name']}",
                f"-CountryCode={target_country}",
                f"-Language={country_data['lang']}"
            ]
            
            # Find and overwrite any embedded date strings that contain Iran timezones
            for key, val in file_metadata.items():
                if isinstance(val, str) and ('+03:30' in val or '+04:30' in val):
                    new_val = val.replace('+03:30', country_offset).replace('+04:30', country_offset)
                    # Skip file system tags, ExifTool handles them based on the OS timezone or throws errors
                    if not key.startswith('File:'):
                        exif_cmd.append(f"-{key}={new_val}")
                        
            exif_cmd.extend(["-overwrite_original", processed_path])
            
            subprocess.run(exif_cmd, check=True, env=env)
            
        # Download filename clean up to assure no traces of original Persian filename
        download_name = f"Document_{uuid.uuid4().hex[:8]}.pdf" if processed_path.lower().endswith('.pdf') else f"Media_{uuid.uuid4().hex[:8]}{os.path.splitext(processed_path)[1]}"
        return FileResponse(processed_path, media_type='application/octet-stream', filename=download_name)
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail="هسته پردازشی قادر به ویرایش یا ذخیره این فرمت فایل نیست.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
