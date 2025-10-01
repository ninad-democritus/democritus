FROM python:3.11-slim

# Install Java (required for PySpark) and curl (for health checks)
RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set Java environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY startup.sh ./startup.sh

RUN chmod +x startup.sh

EXPOSE 8000
CMD ["./startup.sh"]


