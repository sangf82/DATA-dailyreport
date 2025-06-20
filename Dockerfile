# Use Python 3.8 as the base image
FROM python:3.8-slim

# Install system dependencies required for building some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the application files to the container
COPY requirements.txt app.py /app/

# Install the required Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# THIS IS JUST A METADATA, it does not affect the build process
EXPOSE 5001

# Command to run the app with Gunicorn and Gevent worker
CMD ["gunicorn", "-b", "0.0.0.0:5001", "--reload", "--timeout=300", "--workers=4", "--threads=5", "--worker-class=gthread", "app:app"]