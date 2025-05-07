# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies needed by Celery (e.g., for multiprocessing, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Expose the ports the app runs on
EXPOSE 8000

# Set environment variables (optional, if needed)
ENV ENV_VAR_NAME=value

# Command to run the FastAPI application (this will be overridden by docker-compose commands for other services)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
