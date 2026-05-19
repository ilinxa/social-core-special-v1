# Stage 1: Build dependencies
FROM python:3.12.9-slim-bookworm AS builder

WORKDIR /app
COPY requirements/ requirements/

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements/production.lock

# Stage 2: Production image
FROM python:3.12.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Create non-root user
RUN groupadd --gid 1000 django && \
    useradd --uid 1000 --gid django --shell /bin/bash django

WORKDIR $APP_HOME

# Install dependencies from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application
COPY --chown=django:django . .

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app/staticfiles /app/media

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER django

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
