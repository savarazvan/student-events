FROM python:3.12-slim

WORKDIR /app

# Copiază requirements și instalează dependințele
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiază restul codului din backend
COPY . .

EXPOSE 8000

# Pornire server Uvicorn cu auto-reload pentru dezvoltare
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]