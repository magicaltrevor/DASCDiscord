FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
# For Fly/Render/Railway we don’t need to expose a port for a Discord bot.
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]