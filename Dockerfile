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

# Install pip dependencies first (for caching)
# We install the main dependencies without the full package
RUN pip install --no-cache-dir \
    httpx>=0.27.0 \
    fastapi>=0.109.0 \
    uvicorn>=0.27.0 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    aiosqlite>=0.19.0 \
    playwright>=1.40.0

# Install Playwright browsers (CACHED)
RUN playwright install chromium

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package (quick, deps already installed)
RUN pip install --no-cache-dir --no-deps .

# Create data directory
RUN mkdir -p /app/data

# Expose health check port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "trend_fetcher.main"]
