# Use official Python image
FROM python:3.12-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY ../requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the project
COPY ../ .

# Collect static files (optional, if you have static files)
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8080

# Start server using Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080"]