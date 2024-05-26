# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /

# Install the necessary system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc git

# Copy the requirements file into the container
COPY requirements.txt .
COPY openai-1.26.0-py3-none-any.whl .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Navigate to the app directory (if your FastAPI app is inside an 'app' folder)
WORKDIR ./app

# Run main.py when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
