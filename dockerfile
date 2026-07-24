FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Generar código gRPC al construir la imagen
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/connect6.proto
CMD ["python", "agente_connect6.py"]