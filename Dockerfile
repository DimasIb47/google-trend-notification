FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright (CACHED - rarely changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY dependency files first (for layer caching)
COPY pyproject.toml README.md ./

# Create minimal src structure for pip install
RUN mkdir -p src/trend_fetcher && \
    echo '__version__ = "1.0.0"' > src/trend_fetcher/__init__.py

# Install Python dependencies (CACHED - only rebuilds if pyproject.toml changes)
RUN pip install --no-cache-dir .

# Install Playwright browsers (CACHED - only rebuilds if pip deps change)
RUN playwright install chromium

# NOW copy the actual source code (this layer changes often, but doesn't trigger re-download)
COPY src/ ./src/

# Create data directory
RUN mkdir -p /app/data

# Expose health check port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "trend_fetcher.main"]
