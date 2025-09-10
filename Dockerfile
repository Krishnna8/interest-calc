# Use an official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system deps for Pandas & SQLite
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port (Render expects 10000+ but we just expose 5000)
EXPOSE 5000

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the app with Gunicorn (recommended for production)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
