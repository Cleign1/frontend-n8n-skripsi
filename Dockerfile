# 1. Base Image: Use the Alpine-based Miniconda image for a smaller footprint.
FROM continuumio/miniconda3:latest
LABEL authors="ibnuk"

# 2. Set default environment variables.
# WARNING: These are defaults. Override sensitive values at runtime!
# SECRET_KEY should be provided securely at runtime via environment variables or Docker secrets.
ENV EXTERNAL_API_URL="http://api.example.com"
ENV REDIS_HOST="localhost"
ENV REDIS_PORT="6379"
ENV REDIS_DB="0"
# Add any other variables you need
# ENV ANOTHER_VAR="some_value"

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy the environment file first to leverage Docker layer caching.
COPY linux_environment.yml .

# 5. Create the Conda environment.
#    - FIX: Use 'apt-get' for Debian, and install 'build-essential' (the equivalent of 'build-base').
RUN apt-get update && apt-get install -y build-essential && \
    conda env create -f linux_environment.yml && \
    conda clean -afy && \
    rm -rf /var/lib/apt/lists/*

# 6. Copy the rest of your application code into the container.
COPY . .

# 7. Create a startup script to run both Celery and Flask.
RUN echo '#!/bin/sh' > start.sh && \
    echo 'echo "--- Starting Celery Worker ---"' >> start.sh && \
    echo '/opt/conda/envs/fe-n8n/bin/celery -A make_celery.celery worker --loglevel=info &' >> start.sh && \
    echo 'echo "--- Starting Flask App ---"' >> start.sh && \
    echo '/opt/conda/envs/fe-n8n/bin/flask --app run.py --debug run --host=0.0.0.0' >> start.sh && \
    chmod +x start.sh

# 8. Expose the port Flask will run on.
EXPOSE 5000

# 9. Set the command to run when the container starts.
CMD ["./start.sh"]
