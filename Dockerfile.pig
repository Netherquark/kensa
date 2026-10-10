# Optional compatibility image for Pig Latin demonstration; Apache Pig 0.17 is legacy.
FROM eclipse-temurin:8-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl tar bash ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/pig \
    && curl -fsSL https://archive.apache.org/dist/pig/pig-0.17.0/pig-0.17.0.tar.gz -o /tmp/pig.tar.gz \
    && tar -xzf /tmp/pig.tar.gz --strip-components=1 -C /opt/pig \
    && rm /tmp/pig.tar.gz
ENV PIG_HOME=/opt/pig JAVA_HOME=/opt/java/openjdk
WORKDIR /workspace
CMD ["bash"]
