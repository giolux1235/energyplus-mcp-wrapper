FROM python:3.11-slim

WORKDIR /app

# Install Docker (needed for energyplus-wrapper)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Set environment
ENV PORT=8080

EXPOSE 8080

# Run the EnergyPlus simulator with full capabilities
CMD ["python", "thermal-parser.py"]