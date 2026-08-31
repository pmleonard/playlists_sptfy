FROM python:3.12-slim
WORKDIR /app
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Placed at the container root (not /app) so playlists_sptfy.main's own
# PROJECT_ROOT (three parents above main.py) resolves to "/", matching
# where the docker-compose data volume is mounted (/data).
COPY src /src
ENV PYTHONPATH=/src
COPY web .
CMD ["python", "app.py"]
