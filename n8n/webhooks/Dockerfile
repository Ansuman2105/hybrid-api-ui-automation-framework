# ============================================================
# STB Automation Framework — Webhook Server + Dashboard Image
# Base: Python 3.11 slim (guaranteed wheel availability)
# ============================================================
FROM python:3.11-slim

LABEL maintainer="STB QA Team"
LABEL description="STB Automation webhook server and Streamlit dashboard"

# System deps: adb for device management
RUN apt-get update && apt-get install -y --no-install-recommends \
    android-tools-adb \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir flask flask-cors waitress

# Copy project
COPY . .

# Create runtime directories
RUN mkdir -p reports/screenshots logs

# Default: run webhook server
# Override with: command: streamlit run dashboard/dashboard.py ...
CMD ["python", "n8n/webhooks/webhook_server.py"]

EXPOSE 5050 8501
