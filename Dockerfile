# Use the official Python 3.13 slim image as a base
FROM python:3.13-slim

LABEL org.opencontainers.image.source https://github.com/cleign1/frontend-n8n-skripsi

# Set environment variables for Python and Debian
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
# Set the timezone for the container
ENV TZ=Asia/Jakarta

# Set the working directory in the container
WORKDIR /app

# --- System Dependencies ---
# Install timezone data and other necessary packages
# This sets the timezone and cleans up apt cache to keep the image small
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Python Dependencies ---
# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies using pip
# We use --no-cache-dir to reduce the image size.
# IMPORTANT: Make sure 'gunicorn' is listed in your requirements.txt file!
RUN pip install --no-cache-dir -r requirements.txt

# --- Application Code ---
# Copy the rest of your application code into the container
COPY . /app/

# --- Networking ---
# Expose the port the app will run on
EXPOSE 5000

# --- Default Command ---
# The default command to run when the container starts.
# This will be overridden by docker-compose, but it's good practice to have a default.
# It starts Gunicorn with 3 workers, binding to all interfaces on port 5000.
# The application is expected to be the 'app' object in the 'run.py' file.
CMD ["flask", "--app", "run.py", "--host=0.0.0.0"]
