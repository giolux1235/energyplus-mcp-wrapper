FROM python:3.11-slim

WORKDIR /app

# Copy the EnergyPlus simulator
COPY energyplus-simulator.py .

# Set environment
ENV PORT=8080

EXPOSE 8080

# Run the EnergyPlus simulator
CMD ["python", "energyplus-simulator.py"]