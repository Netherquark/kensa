FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    HOME=/tmp \
    SPARK_LOCAL_IP=127.0.0.1 \
    PYSPARK_PYTHON=python3 \
    PYSPARK_DRIVER_PYTHON=python3

RUN apt-get update && apt-get install -y --no-install-recommends \
      openjdk-17-jre-headless procps tini ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && chmod 666 /etc/passwd /etc/group \
    && chmod 1777 /tmp

WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt
COPY . /workspace
RUN chmod +x /workspace/scripts/*.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/workspace/scripts/entrypoint.sh"]
CMD ["help"]
