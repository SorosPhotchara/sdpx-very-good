# Pin the Python base used to install production dependencies.
FROM python:3.12-slim AS deps

# Disable bytecode files and flush Python output directly to container logs.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"

# Keep all backend build paths under one predictable directory.
WORKDIR /workspace/backend

# Copy dependency manifests before source code to preserve dependency layer caching.
COPY backend/requirements.txt backend/requirements-dev.txt ./

# Install production dependencies only into a reusable virtual environment.
RUN python -m venv /opt/venv && pip install -r requirements.txt --no-cache-dir

# Reuse the production dependency environment for source validation and packaging.
FROM deps AS build

# Copy application and migration source after the dependency layer is complete.
COPY backend/ ./

# Compile Python source to catch syntax errors during the image build.
RUN python -m compileall -q app

# Extend the build image with development dependencies for the test target.
FROM build AS test

# Install test dependencies without caching downloaded Python packages.
RUN pip install -r requirements-dev.txt --no-cache-dir

# Run the backend pytest suite when the test target is started.
CMD ["python", "-m", "pytest"]

# Start runtime from a clean pinned image without development dependencies.
FROM python:3.12-slim AS runtime

# Configure predictable Python behavior and expose the copied virtual environment.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"

# Create an unprivileged system account for the API process.
RUN groupadd --system paireval && useradd --system --gid paireval --create-home paireval

# Set the runtime application directory.
WORKDIR /app

# Copy the production-only virtual environment from the dependency stage.
COPY --from=deps /opt/venv /opt/venv

# Copy the compiled application source from the build stage.
COPY --from=build --chown=paireval:paireval /workspace/backend/app ./app

# Copy Alembic migrations so deployments can run schema upgrades with this image.
COPY --from=build --chown=paireval:paireval /workspace/backend/migrations ./migrations

# Copy Alembic configuration required by migration commands.
COPY --from=build --chown=paireval:paireval /workspace/backend/alembic.ini ./alembic.ini

# Drop root privileges before starting the application.
USER paireval

# Document the port served by Uvicorn.
EXPOSE 8000

# Verify the public API health endpoint without adding curl to the runtime image.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]

# Start the FastAPI application on all container interfaces.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
