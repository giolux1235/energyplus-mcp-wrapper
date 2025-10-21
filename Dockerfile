FROM python:3.11-slim

WORKDIR /app

# Copy the enhanced server
COPY enhanced-server.py .

# Set environment
ENV PORT=8080

EXPOSE 8080

# Run the enhanced server
CMD ["python", "enhanced-server.py"]