FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose default port
EXPOSE 8000

ENV DB_PATH=/app/agent_api.db
ENV DEFAULT_API_KEY=test-api-key-12345

# Use shell form to expand $PORT dynamically on Render/Cloud platforms
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
