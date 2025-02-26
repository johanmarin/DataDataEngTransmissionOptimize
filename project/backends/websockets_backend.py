import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

# Tiempo de inactividad antes de cerrar conexión (en segundos)
INACTIVITY_TIMEOUT = 30

def get_file(context):
        try:
            with open("sample.pdf", "rb") as file:
                content = file.read()
                print("Leído sample.pdf, tamaño:", len(content))
                return content.hex()
        except Exception as e:
            print("Error al leer sample.pdf:", e)
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return None
        
def build_response(message, context):
    if message == "simple":
        response = "Hello, world!"
    elif message == "large":
        response = json.dumps({"data": ["x" * 10000 for _ in range(100)]})
    elif message == "heavy":            
        response = json.dumps({"data": ["x" * 100000 for _ in range(100)]})
    elif message == "file":
        response = get_file(context)
    else:
        # Abortamos la llamada con un error de argumento inválido
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown command: {message}")
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Cliente conectado")

    while True:
        try:
            # Esperar mensaje con timeout para cerrar por inactividad
            message = await asyncio.wait_for(websocket.receive_text(), timeout=INACTIVITY_TIMEOUT)
            print(f"Received command: {message}")

            if message == "simple":
                await websocket.send_text("Hello, world!")

            elif message == "large":
                large_data = json.dumps({"data": ["x" * 10000 for _ in range(100)]})
                await websocket.send_text(large_data)

            elif message == "heavy":
                heavy_data = json.dumps({"data": ["x" * 100000 for _ in range(100)]})
                await websocket.send_text(heavy_data)

            elif message.startswith("stream:"):
                # Se espera un formato "stream:<request_id>"
                try:
                    _, request_id = message.split(":", 1)
                except ValueError:
                    await websocket.send_text("ERROR: Formato de stream incorrecto. Use 'stream:<id>'.")
                    continue
                # Se lanza una tarea asíncrona para manejar este stream sin bloquear el loop principal
                asyncio.create_task(handle_stream(websocket, request_id))

            elif message == "file":
                try:
                    with open("sample.pdf", "rb") as file:
                        while chunk := file.read(4096):  # Leer en bloques de 4KB
                            await websocket.send_text(chunk.hex())  # Enviar en formato hexadecimal
                except FileNotFoundError:
                    await websocket.send_text("ERROR: Archivo no encontrado.")

            elif message == "exit":
                await websocket.send_text("Closing connection.")
                await websocket.close()
                print("Cliente cerró la conexión")
                break

            else:
                await websocket.send_text("ERROR: Comando no reconocido.")

        except asyncio.TimeoutError:
            # Cerrar conexión tras tiempo de inactividad
            await websocket.send_text("ERROR: Conexión cerrada por inactividad.")
            await websocket.close()
            print("Conexión cerrada por inactividad")
            break

        except WebSocketDisconnect:
            print("Cliente desconectado inesperadamente")
            break

        except Exception as e:
            print(f"Error: {e}")
            break
        
async def handle_stream(websocket: WebSocket, request_id: str):
    """
    Maneja un stream de mensajes de forma asíncrona para un identificador dado.
    Esto permite que, en una misma conexión, se puedan gestionar múltiples
    solicitudes de streaming en paralelo.
    """
    try:
        for i in range(10):
            await websocket.send_text(f"Stream {request_id} - Message {i}")
    except Exception as e:
        print(f"Error en stream {request_id}: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
