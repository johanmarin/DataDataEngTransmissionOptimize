from mangum import Mangum
from fastapi import FastAPI, Response
import json
import time
import gzip
import boto3

app = FastAPI()

# S3 Config (Para archivos grandes)
S3_BUCKET_NAME = "mi-bucket"  # Reemplazar con el bucket real en AWS
S3_FILE_NAME = "sample.pdf"
s3_client = boto3.client("s3")

@app.get("/simple")
def simple_response():
    return {"message": "Hello, world!"}

@app.get("/large")
def large_response():
    """ Devuelve un JSON grande comprimido con gzip para mejorar rendimiento """
    data = {"data": ["x" * 10000 for _ in range(100)]} 
    compressed_data = gzip.compress(json.dumps(data).encode())
    return Response(compressed_data, media_type="application/json", headers={"Content-Encoding": "gzip"})

@app.get("/heavy")
def heavy_response():
    """ Simula procesamiento pesado """
    data = {"data": ["x" * 1000000000 for _ in range(10000)]} 
    compressed_data = gzip.compress(json.dumps(data).encode())
    return Response(compressed_data, media_type="application/json", headers={"Content-Encoding": "gzip"})

@app.get("/stream")
def stream_response():
    """ Como Lambda no soporta streaming, devolvemos una lista en su lugar """
    return {"messages": [f"Message {i}" for i in range(10)]}

@app.get("/file")
def file_response():
    """ Genera una URL firmada de S3 para descargar el archivo en lugar de servirlo desde Lambda """
    with open("sample.pdf", "rb") as file:
            content = file.read()
    return Response(content, media_type="application/pdf")

# Handler para Lambda con API Gateway
lambda_handler = Mangum(app, lifespan="off")
