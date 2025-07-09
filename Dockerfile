# ───── Base image ─────
FROM python:3.12-slim

# ───── Environment settings ─────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=TalonAILinux.settings

# ───── System packages ─────
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ───── Working directory ─────
WORKDIR /app

# ───── Install dependencies ─────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ───── Copy project files ─────
COPY . .

# ───── Make startup script executable ─────
RUN chmod +x startup.sh

# ───── Collect static files (optional for admin panel) ─────
# Skip collectstatic during build to avoid database connections
# RUN python manage.py collectstatic --noinput || true

# ───── Use startup script that runs migrations then starts server ─────
CMD ["./startup.sh", "gunicorn", "--bind", "0.0.0.0:8000", "TalonAILinux.asgi:application", "-k", "uvicorn.workers.UvicornWorker"]
