FROM python:3.11-slim

WORKDIR /app

# Install git for repository tracking
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications and source
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install anchor package
RUN pip install --no-cache-dir .

ENTRYPOINT ["anchor"]
CMD ["--help"]
