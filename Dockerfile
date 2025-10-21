FROM python:3.11-slim

# Install system dependencies for EnergyPlus
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    build-essential \
    gfortran \
    libgl1-mesa-glx \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libxft2 \
    libxinerama1 \
    libxcursor1 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libgconf-2-4 \
    libxtst6 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxss1 \
    libasound2 \
    libnss3 \
    libxrandr2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxss1 \
    libasound2 \
    libnss3 \
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
