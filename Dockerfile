FROM public.ecr.aws/docker/library/python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DASH_PREFIX=/educacao-superior/

EXPOSE 8050

HEALTHCHECK CMD curl --fail http://localhost:8050/educacao-superior/ || exit 1

CMD ["gunicorn", "app:server", "-b", "0.0.0.0:8050", "-w", "1", "--threads", "4", "--timeout", "120"]
