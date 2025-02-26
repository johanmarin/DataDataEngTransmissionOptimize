import asyncio
import aiofiles
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/simple")
async def simple_response():
    return {"message": "Hello, world!"}

@app.get("/large")
async def large_response():
    data = {"data": ["x" * 10000 for _ in range(100)]}  # ~1MB de respuesta
    return data

@app.get("/heavy")
async def heavy_response():
    """ Simula procesamiento pesado """
    data = {"data": ["x" * 100000 for _ in range(100)]} 
    return data

@app.get("/file")
async def file_response():
    # Para I/O de archivos, podrías utilizar async file I/O (con aiofiles, por ejemplo)
    async with aiofiles.open("sample.pdf", mode="rb") as file:
        content = await file.read()
    return Response(content, media_type="application/pdf")
