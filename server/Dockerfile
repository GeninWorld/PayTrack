# Use official lightweight Python image
FROM python:3.8.10

# Set working directory
WORKDIR /app

# Copy requirement file and install deps first (to leverage caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Use Gunicorn for production (more efficient than flask run)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
