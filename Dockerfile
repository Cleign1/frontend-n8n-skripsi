FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta

WORKDIR /app

RUN apt-get update && apt-get install -y tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Jakarta /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY requirements.in .
RUN uv pip compile requirements.in -o requirements.txt
RUN uv pip sync --system requirements.txt

COPY . .

EXPOSE 5000

CMD ["uv", "run", "flask", "--app", "run.py", "run", "--debug", "--host=0.0.0.0"]
