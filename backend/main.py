import os
import subprocess
import json
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
        result = subprocess.run(
            ["exiftool", "-j", "-G", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
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
