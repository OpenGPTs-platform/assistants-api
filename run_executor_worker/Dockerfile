# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install the necessary system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc git

# Copy the requirements file into the container
COPY requirements.txt .
COPY openai-1.26.0-py3-none-any.whl .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the watcher script
CMD ["python", "scripts/watcher.py"]
