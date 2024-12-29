FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for psutil
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

CMD ["uvicorn", "app.api_endpoints:app", "--host", "0.0.0.0", "--port", "8000"]