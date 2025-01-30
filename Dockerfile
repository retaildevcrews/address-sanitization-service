# Use a lightweight Python image
FROM python:3.12-slim

# Install Poetry
RUN pip install poetry

# Set a working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without virtualenv)
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# Copy your code
COPY app/ ./app/

# Expose the port FastAPI will run on
EXPOSE 80

# Default command to run the server
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
