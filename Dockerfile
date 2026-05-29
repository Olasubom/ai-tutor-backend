FROM python:3.12-slim

WORKDIR /app

COPY agency/requirements.txt /app/agency/requirements.txt
RUN pip install --no-cache-dir -r /app/agency/requirements.txt

COPY . /app

ENV PYTHONPATH=/app

CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
