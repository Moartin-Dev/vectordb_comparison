FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create virtual environment outside /app to avoid volume mount conflicts
RUN python -m venv /opt/venv

# Update PATH to use venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies in venv
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["/opt/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]