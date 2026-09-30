FROM python:3.12-slim
WORKDIR /app

COPY insurance_agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY insurance_agent ./insurance_agent
COPY main.py ./main.py

ENV PORT=8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
