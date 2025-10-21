FROM python:3.11-slim

# Install system dependencies for EnergyPlus
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    build-essential \
    gfortran \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxrender-dev \
    libxext-dev \
    libxft-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    libxrandr-dev \
    libxss-dev \
    libxtst-dev \
    libxcomposite-dev \
    libxdamage-dev \
    libxfixes-dev \
    libasound2-dev \
    libnss3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download and install EnergyPlus
RUN wget -O energyplus.tar.gz "https://github.com/NREL/EnergyPlus/releases/download/v24.2.0/EnergyPlus-24.2.0-48c1128f03-Linux-Ubuntu22.04-x86_64.tar.gz" \
    && tar -xzf energyplus.tar.gz \
    && mv EnergyPlus-24.2.0-48c1128f03-Linux-Ubuntu22.04-x86_64 /usr/local/energyplus \
    && ln -s /usr/local/energyplus/energyplus /usr/local/bin/energyplus \
    && ln -s /usr/local/energyplus/Energy+.idd /usr/local/bin/Energy+.idd \
    && rm energyplus.tar.gz

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create necessary directories
RUN mkdir -p logs outputs sample_files

# Set environment variables
ENV WORKSPACE_ROOT=/app/EnergyPlus-MCP/energyplus-mcp-server
ENV PORT=8080
ENV ENERGYPLUS_EXE=/usr/local/bin/energyplus
ENV ENERGYPLUS_IDD=/usr/local/bin/Energy+.idd

EXPOSE 8080

# Use the full HTTP wrapper with EnergyPlus
CMD ["python", "simple-http-wrapper.py"]
