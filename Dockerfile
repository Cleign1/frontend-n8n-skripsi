FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta

WORKDIR /app

RUN apt-get update && apt-get install -y tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Jakarta /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH=/root/.local/bin:$PATH

# Create a virtual environment at /app/.venv
RUN uv venv

# Copy requirements and install dependencies into the venv.
# uv will automatically detect and use the virtual environment in the workdir.
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

COPY . /app/

EXPOSE 5000

CMD ["uv", "run", "flask", "--app", "run.py", "run", "--debug", "--host=0.0.0.0"]
