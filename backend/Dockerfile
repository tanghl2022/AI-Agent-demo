FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY wms_agent ./wms_agent
EXPOSE 8000
CMD ["uvicorn", "wms_agent.application:app", "--host", "0.0.0.0", "--port", "8000"]
