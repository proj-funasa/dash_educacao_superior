FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DASH_PREFIX=/educacao-superior/
ENV DB_HOST=bigdata.dataiesb.com
ENV DB_PORT=5432
ENV DB_NAME=iesb
ENV DB_USER=iesb

EXPOSE 8051

CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8051", "--workers", "2", "--timeout", "120"]
