# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install opencv dependencies and any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

# Expose the port the app runs on
EXPOSE 80

# Start the Django application
CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]