FROM python:3.12-slim

# Install ExifTool, qpdf, ca-certificates, and apply security upgrades
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends exiftool qpdf ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
