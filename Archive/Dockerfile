FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg gcc g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Upgrade pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set `PYTHONUNBUFFERED` to `1` for better logging/debugging
ENV PYTHONUNBUFFERED=1

# Set environment variable to indicate running in Docker
ENV RUNNING_IN_DOCKER=true

COPY . .

CMD ["bash", "start.sh"]
