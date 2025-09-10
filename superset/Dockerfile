FROM apache/superset:latest

USER root

# Install additional database drivers
RUN pip install psycopg2-binary pymongo Flask-Caching redis

# Install MySQL client for testing
# RUN apt-get update && apt-get install -y mariadb-client && rm -rf /var/lib/apt/lists/*


# Copy custom configuration
COPY superset_config.py /app/superset_config.py

USER superset