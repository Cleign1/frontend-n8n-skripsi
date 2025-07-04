# Step 1: Use an official Python 3.13 slim image as the base
FROM python:3.13-slim

# Step 2: Set environment variables
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Step 3: Install uv using pip
RUN pip install uv

# Step 4: Copy and install dependencies
# We removed "RUN uv venv ."
COPY requirements.in .
RUN uv pip compile requirements.in -o requirements.txt
RUN uv pip sync --system requirements.txt

# Step 5: Copy the rest of the application code into the container
COPY . .

# Step 6: Expose the port the app runs on
EXPOSE 5000

# Step 7: Define the command to run the application
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:create_app()"]