# Use a lightweight Python image
FROM python:3.9-slim

# Set a working directory
WORKDIR /app

# Copy dependency file and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code
COPY app/ ./app/

# Expose the port FastAPI will run on (optional—helps for documentation)
EXPOSE 80

# Default command to run the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
