FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create necessary directories
RUN mkdir -p logs outputs

# Set environment variables
ENV WORKSPACE_ROOT=/app/EnergyPlus-MCP/energyplus-mcp-server
ENV PORT=8080

EXPOSE 8080

# Use the simple HTTP wrapper instead of the full one
CMD ["python", "simple-http-wrapper.py"]
