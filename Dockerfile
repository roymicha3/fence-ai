# Dockerfile for Fence-AI Python project
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (override in docker-compose if needed)
CMD ["bash"]
