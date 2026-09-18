FROM python:3.11

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update --allow-releaseinfo-change \
 && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    pango1.0-tools \
    libgdk-pixbuf-2.0-0 \
    libgdk-pixbuf2.0-bin \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    libjpeg-dev \
    zlib1g-dev \
    libssl-dev \
    libglib2.0-0 \
    shared-mime-info \
    ca-certificates \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /core

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn bill_management.wsgi:application --bind 0.0.0.0:8000"]
