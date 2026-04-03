FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Create non-root user
RUN groupadd --system appuser && useradd --system --gid appuser appuser

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY app/ ./app/

# Create data directory for SQLite
RUN mkdir -p data && chown -R appuser:appuser /app

# Create virtual environment and install dependencies
RUN uv sync

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5001

# Run the application (no --reload in production)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "1"]
