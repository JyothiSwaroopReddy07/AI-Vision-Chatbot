FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --fix-missing \
    gcc \
    g++ \
    postgresql-client \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    curl \
    || (apt-get update && apt-get install -y --fix-missing \
    gcc \
    g++ \
    postgresql-client \
    poppler-utils \
    libpq-dev \
    curl) \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /data/uploads /data/pubmed_pdfs /data/processed /data/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

