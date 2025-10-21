FROM python:3.11-slim

WORKDIR /app

# Copy the ultra-simple server
COPY ultra-simple.py .

# Set environment
ENV PORT=8080

EXPOSE 8080

# Run the ultra-simple server
CMD ["python", "ultra-simple.py"]