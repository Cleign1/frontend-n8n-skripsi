# =====================================================================
# Stage 1: The "builder" stage
# We use a full Debian-based image to build our Conda environment.
# =====================================================================
FROM continuumio/miniconda3:latest AS builder

LABEL authors="ibnuk"

WORKDIR /app

# Install the build dependencies needed to create the environment
RUN apt-get update && apt-get install -y build-essential

# Copy only the environment file
COPY linux_environment.yml .

# Create the Conda environment. This will be a large directory.
RUN conda env create -f linux_environment.yml

# =====================================================================
# Stage 2: The "final" production stage
# We start from a much smaller, clean base image.
# =====================================================================
FROM continuumio/miniconda3:latest

WORKDIR /app

# Crucial Step: Copy the entire installed environment from the 'builder' stage.
# This brings over all the packages without any of the build tools or caches.
COPY --from=builder /opt/conda/envs/fe-n8n /opt/conda/envs/fe-n8n

# Set default environment variables
# Secret Key must be set
ENV EXTERNAL_API_URL="http://api.example.com"
ENV REDIS_HOST="localhost"
ENV REDIS_PORT="6379"
ENV REDIS_DB="0"

# Copy your application code
COPY . .

# Create the startup script
RUN echo '#!/bin/sh' > start.sh && \
    echo 'echo "--- Starting Celery Worker ---"' >> start.sh && \
    echo '/opt/conda/envs/fe-n8n/bin/celery -A make_celery.celery worker --loglevel=info --concurrency=10 -n worker1@%h &' >> start.sh && \
    echo 'echo "--- Starting Flask App ---"' >> start.sh && \
    echo '/opt/conda/envs/fe-n8n/bin/flask --app run.py --debug run --host=0.0.0.0' >> start.sh && \
    chmod +x start.sh

# Expose the application port
EXPOSE 5000

# Set the startup command
CMD ["./start.sh"]
