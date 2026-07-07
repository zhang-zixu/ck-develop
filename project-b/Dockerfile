FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY VERSION ./VERSION

EXPOSE 9090

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9090"]
