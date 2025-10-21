FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install flask energyplus-mcp
EXPOSE 8080
CMD ["python", "http-wrapper.py"]
