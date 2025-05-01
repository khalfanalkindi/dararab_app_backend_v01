FROM python:3.10-slim

# Install system dependencies including MySQL development files
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directory for static files
RUN mkdir -p staticfiles

# Create entrypoint script
RUN echo '#!/bin/bash\n\
python manage.py collectstatic --noinput\n\
python manage.py migrate\n\
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Command to run the application
ENTRYPOINT ["/app/entrypoint.sh"] 