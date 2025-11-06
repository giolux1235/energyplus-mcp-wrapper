FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and EnergyPlus
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libxinerama1 \
    libxcursor1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install EnergyPlus 25.1.0
ARG EPLUS_VER=25.1.0
ARG EPLUS_HASH=68a4a7c774
ARG EPLUS_PREFIX=/usr/local/EnergyPlus-25-1-0

RUN set -eux; \
    mkdir -p ${EPLUS_PREFIX}; \
    wget -q "https://github.com/NREL/EnergyPlus/releases/download/v${EPLUS_VER}/EnergyPlus-${EPLUS_VER}-${EPLUS_HASH}-Linux-Ubuntu22.04-x86_64.tar.gz" \
         -O /tmp/eplus.tgz || \
    wget -q "https://github.com/NREL/EnergyPlus/releases/download/v${EPLUS_VER}/EnergyPlus-${EPLUS_VER}-${EPLUS_HASH}-Linux-Ubuntu22.04-arm64.tar.gz" \
         -O /tmp/eplus.tgz; \
    tar -xzf /tmp/eplus.tgz -C ${EPLUS_PREFIX} --strip-components=1; \
    ln -sf ${EPLUS_PREFIX}/energyplus /usr/local/bin/energyplus; \
    ln -sf ${EPLUS_PREFIX}/Energy+.idd /usr/local/bin/Energy+.idd; \
    rm /tmp/eplus.tgz

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Set environment
ENV PORT=8080
ENV PATH="${EPLUS_PREFIX}:${PATH}"
ENV EPLUS_IDD_PATH="${EPLUS_PREFIX}/Energy+.idd"

EXPOSE 8080

# Run the EnergyPlus robust API (matches Procfile)
CMD ["python", "energyplus-robust-api.py"]