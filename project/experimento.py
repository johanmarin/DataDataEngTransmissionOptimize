import docker
import time
import requests
import grpc
import asyncio
import websockets
import csv
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from backends import service_pb2, service_pb2_grpc

# Archivo CSV para guardar las métricas
CSV_FILE = "data/metrics.csv"

def init_csv():
    """Inicializa el archivo CSV con encabezados si no existe."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "herramienta", "conexion", "endpoint", "concurrency", 
                "cpu", "memory", "volumen", "latency", "capacidad_procesamiento"
            ])

def write_metric(test_name, cnxn, endpoint, concurrency, latency, configured_cpu, configured_mem):
    """Guarda la métrica de cada petición en el CSV."""
    volumen_bytes = {
        "simple": 28,
        "large": 1000410,
        "heavy": 100004010,
        "stream": 144,
        "file": 178320
    }
    volumen_MB = {k: v/1048576 for k, v in volumen_bytes.items()}
    with open(CSV_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            test_name,
            cnxn,
            endpoint,
            concurrency,
            float(configured_cpu) / 1e9,
            float(configured_mem[:-1]) / 1024 if configured_mem.endswith("m") else float(configured_mem[:-1]),
            volumen_MB.get(endpoint, 0),
            latency,
            volumen_MB.get(endpoint, 0) / latency if latency > 0 else 0
        ])

#########################################
# Función para crear y arrancar contenedor
#########################################
def create_and_start_container(image, nano_cpus, mem_limit):
    client = docker.from_env()
    
    ports_mapping = {
        "apirest-app": {'8000/tcp': 8000},
        "grpc-app":    {'50051/tcp': 8001},
        "websockets-app": {'8000/tcp': 8002}
    }

    try:
        existing = client.containers.get(image)
        print(f"El contenedor '{image}' ya existe. Se detiene y elimina.")
        existing.stop()
        existing.remove()
    except docker.errors.NotFound:
        pass

    client.containers.run(
        image=image,
        name=image,
        detach=True,
        auto_remove=False,
        nano_cpus=nano_cpus,   
        mem_limit=mem_limit,    
        ports=ports_mapping[image]
    )
    print(f"Contenedor '{image}' iniciado.")
    host_port = list(ports_mapping[image].values())[0]
    return host_port

def stop_all_containers():
    """Detiene y elimina todos los contenedores en ejecución."""
    client = docker.from_env()
    for container in client.containers.list(all=True):
        try:
            container.stop()
            container.remove()
            print(f"Contenedor '{container.name}' detenido y eliminado.")
        except Exception as e:
            print(f"Error al detener/eliminar contenedor '{container.name}': {e}")

#########################################
# Pruebas para API REST
#########################################
# Modo síncrono (sin gateway) – se incluye el tiempo de conexión (ya que requests abre y cierra conexión en cada llamada)
def test_apirest_sync(host_port, endpoint, concurrency=1, configured_cpu="1e9", configured_mem="512m"):
    url = f"http://localhost:{host_port}/{endpoint}"
    delay = 1.0 / concurrency + 1
    start = time.time()
    for i in range(concurrency):        
        try:
            response = requests.get(url, stream=True)
            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" in content_type:
                for chunk in response.iter_content(chunk_size=8192):
                    pass
                result = "PDF recibido"
            else:
                try:
                    result = response.json()
                except Exception:
                    result = response.content.decode()
            _time = time.time()
            latency = _time - (start + delay*i) # Tiempo de repuesta menso tiempo en que llego la petición
            write_metric("test_apirest_sync", "multiple-sync", endpoint, concurrency, latency, configured_cpu, configured_mem)
        except Exception as e:
            print(f"Error en REST Sync, petición {i+1}, endpoint '{endpoint}': {e}")
        time.sleep(max(0, delay*(i + 1) - (time.time() - start)))

# Modo asíncrono (con gateway) – se incluye el tiempo de conexión, usando aiohttp
async def test_apirest_async(host_port, endpoint, concurrency=1, configured_cpu="1e9", configured_mem="512m"):
    import aiohttp
    url = f"http://localhost:{host_port}/{endpoint}"
    delay = 1.0 / concurrency + 1  # Intervalo programado entre envíos
    tasks = []
    # Lanza cada petición en su propia tarea sin esperar la respuesta de las anteriores
    for i in range(concurrency):
        # Calcula el instante de envío programado para esta petición
        scheduled_send_time = time.time() + delay * i
        # Crea la tarea que enviará la petición en el momento adecuado
        tasks.append(asyncio.create_task(send_request(url,
            concurrency,
            index=i,
            scheduled_send_time=scheduled_send_time,
            endpoint=endpoint,
            configured_cpu=configured_cpu,
            configured_mem=configured_mem)))
        # Espera el intervalo entre lanzamientos de tareas
        await asyncio.sleep(delay)
    # Espera a que todas las tareas finalicen
    await asyncio.gather(*tasks)

async def send_request(session_url, concurrency, index, scheduled_send_time, endpoint, configured_cpu, configured_mem):
    import aiohttp
    async with aiohttp.ClientSession() as session:
        # Espera hasta el instante programado (en caso de que se haya creado la tarea antes de la hora de envío)
        now = time.time()
        if scheduled_send_time >= now:
            await asyncio.sleep(scheduled_send_time - now)
        start = time.time()
        try:
            async with session.get(session_url) as response:
                data = await response.text()
            latency = time.time() - start
            # Se registra el valor de concurrencia total en cada métrica para poder compararlos
            write_metric("test_apirest_async", "multiple-async", endpoint, 
                         concurrency, latency, configured_cpu, configured_mem)
        except Exception as e:
            print(f"Error en REST Async, petición {index+1}, endpoint '{endpoint}': {e}")

#########################################
# Pruebas para gRPC
#########################################
def test_grpc_sync(host_port, cnxn, endpoint, concurrency=1, configured_cpu="1e9", configured_mem="512m"):
    SERVER_ADDRESS = f"localhost:{host_port}"
    delay = 1.0 / concurrency + 1
    if cnxn == "unica":
        # Canal único: se usa una única conexión; la primera petición incluye el tiempo de conexión.
        with grpc.insecure_channel(SERVER_ADDRESS) as channel:
            stub = service_pb2_grpc.BackendStub(channel)
            request = service_pb2.Request(message=endpoint)
            start = time.time() 
            for i in range(concurrency):
                try:
                    response = stub.Call(request)
                    _time = time.time()
                    latency = _time - (start + delay*i) # Tiempo de repuesta menso tiempo en que llego la petición
                    write_metric("test_grpc", "unica-sync", endpoint, concurrency, latency, configured_cpu, configured_mem)
                except grpc.RpcError as error:
                    print(f"Error en gRPC Unica, petición {i+1}: {error.details()}")
                time.sleep(max(0, delay*(i + 1) - (time.time() - start)))
            channel.close()
    elif cnxn == "multiple":
        # Cada petición abre su propia conexión; el tiempo de conexión se mide desde antes de establecer el canal.
        for i in range(concurrency):
            start = time.time()
            with grpc.insecure_channel(SERVER_ADDRESS) as channel:
                stub = service_pb2_grpc.BackendStub(channel)
                request = service_pb2.Request(message=endpoint)
                try:
                    responses = list(stub.Call(iter([request])))
                    _time = time.time()
                    latency = _time - (start + delay*i)
                    channel.close()
                    write_metric("test_grpc", "multiple-sync", endpoint, concurrency, latency, configured_cpu, configured_mem)
                except grpc.RpcError as error:
                    print(f"Error en gRPC Multiple, petición {i+1}: {error.details()}")
            time.sleep(max(0, delay*(i + 1) - (time.time() - start)))
            
            
async def test_grpc_async(host_port, cnxn, endpoint, concurrency=1, configured_cpu="1e9", configured_mem="512m"):
    SERVER_ADDRESS = f"localhost:{host_port}"
    delay = 1.0 / concurrency + 1  # Intervalo programado entre envíos
    global_start = time.time()     # Punto de partida para programar todas las peticiones
    tasks = []
    
    if cnxn == "unica":
        # Modo "unica": se usa un único canal asíncrono para todas las peticiones.
        async with grpc.aio.insecure_channel(SERVER_ADDRESS) as channel:
            stub = service_pb2_grpc.BackendStub(channel)
            for i in range(concurrency):
                scheduled_send_time = global_start + delay * i
                tasks.append(asyncio.create_task(async_grpc_unica(stub, endpoint, scheduled_send_time, i, concurrency, configured_cpu, configured_mem)))
                await asyncio.sleep(delay)  # Lanza las tareas a intervalos
    elif cnxn == "multiple":
        # Modo "multiple": cada petición abre su propio canal asíncrono.
        for i in range(concurrency):
            scheduled_send_time = global_start + delay * i
            tasks.append(asyncio.create_task(async_grpc_multiple(SERVER_ADDRESS, endpoint, scheduled_send_time, i, concurrency, configured_cpu, configured_mem)))
            await asyncio.sleep(delay)
    await asyncio.gather(*tasks, return_exceptions=True)

async def async_grpc_unica(stub, endpoint, scheduled_send_time, index, concurrency, configured_cpu, configured_mem):
    now = time.time()
    if scheduled_send_time > now:
        await asyncio.sleep(scheduled_send_time - now)
    req = service_pb2.Request(message=endpoint)
    try:
        # Se espera la respuesta y se itera sobre el stream.
        response = None
        async for resp in stub.Call(iter([req])):
            response = resp
            break  # Tomamos la primera respuesta
        latency = time.time() - scheduled_send_time
        print(f"[gRPC Async Unica] Conexión {index+1} → {response.message} (latency: {latency:.3f}s)")
        write_metric("test_grpc_async", "unica-async", endpoint, concurrency, latency, configured_cpu, configured_mem)
    except grpc.aio.AioRpcError as error:
        print(f"Error en gRPC Async Unica, conexión {index+1}: {error.details()}")


async def async_grpc_multiple(server_address, endpoint, scheduled_send_time, index, concurrency, configured_cpu, configured_mem):
    now = time.time()
    if scheduled_send_time > now:
        await asyncio.sleep(scheduled_send_time - now)
    # Cada petición crea su propio canal.
    async with grpc.aio.insecure_channel(server_address) as channel:
        await channel.channel_ready()  # Espera a que el canal esté listo
        stub = service_pb2_grpc.BackendStub(channel)
        req = service_pb2.Request(message=endpoint)
        try:
            responses = []
            async for response in stub.Call(iter([req])):
                responses.append(response)
            latency = time.time() - scheduled_send_time
            print(f"[gRPC Async Multiple] Petición {index+1} → {[r.message for r in responses]} (latency: {latency:.3f}s)")
            write_metric("test_grpc_async", "multiple-async", endpoint, concurrency, latency, configured_cpu, configured_mem)
        except grpc.aio.AioRpcError as error:
            print(f"Error en gRPC Async Multiple, petición {index+1}: {error.details()}")


#########################################
# Pruebas para WebSockets
#########################################

async def test_websocket(host_port, endpoint, concurrency=1, configured_cpu="", configured_mem=""):
    uri = f"ws://localhost:{host_port}/ws"
    print(f"Conectando a {uri}...")
    
    delay = 1.0 / concurrency + 1
    start = time.time()
    
    async with websockets.connect(uri, max_size=None) as websocket:
        for i in range(concurrency):
            await websocket.send(endpoint)
            print(f"Comando enviado: {endpoint}")

            if endpoint == "stream":
                print("Recibiendo mensajes de stream:")
                try:
                    while True:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        print("Received:", response)
                except asyncio.TimeoutError:
                    print("No se recibieron más mensajes en stream.")
            elif endpoint == "file":
                print("Recibiendo datos del archivo:")
                file_data = b""
                try:
                    while True:
                        chunk = await asyncio.wait_for(websocket.recv(), timeout=5)
                        if chunk.startswith("ERROR"):
                            print("Error recibido:", chunk)
                            break
                        file_data += bytes.fromhex(chunk)
                except asyncio.TimeoutError:
                    print("Fin de la recepción de datos del archivo.")

                if file_data:
                    print(file_data)
                    print("Archivo PDF recibido y guardado como 'archivo_ws.pdf'.")
                else:
                    print("No se recibieron datos de archivo.")
            else:
                response = await websocket.recv()
                print("Received:", response)
            
            _time = time.time()
            latency = _time - (start + delay*i)
            write_metric("test_websocket", "async-unica", endpoint, 1, latency, configured_cpu, configured_mem)
            await asyncio.sleep(max(0, delay*(i + 1) - (time.time() - start)))
                
    for i in range(concurrency):
        async with websockets.connect(uri, max_size=None) as websocket:
            await websocket.send(endpoint)
            print(f"Comando enviado: {endpoint}")

            if endpoint == "stream":
                print("Recibiendo mensajes de stream:")
                try:
                    while True:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        print("Received:", response)
                except asyncio.TimeoutError:
                    print("No se recibieron más mensajes en stream.")
            elif endpoint == "file":
                print("Recibiendo datos del archivo:")
                file_data = b""
                try:
                    while True:
                        chunk = await asyncio.wait_for(websocket.recv(), timeout=5)
                        if chunk.startswith("ERROR"):
                            print("Error recibido:", chunk)
                            break
                        file_data += bytes.fromhex(chunk)
                except asyncio.TimeoutError:
                    print("Fin de la recepción de datos del archivo.")

                if file_data:
                    print(file_data)
                    print("Archivo PDF recibido y guardado como 'archivo_ws.pdf'.")
                else:
                    print("No se recibieron datos de archivo.")
            else:
                response = await websocket.recv()
                print("Received:", response)
            
            _time = time.time()
            latency = _time - (start + delay*i)
            write_metric("test_websocket", "async-unica", endpoint, 1, latency, configured_cpu, configured_mem)
            await asyncio.sleep(max(0, delay*(i + 1) - (time.time() - start)))
            

#########################################
# Ejecución principal
#########################################
if __name__ == '__main__':
    init_csv()
    
    # Niveles de concurrencia a probar
    concurrencias = [1, 1, 5, 10, 50, 100]
    # Configuraciones de máquina: (nano_cpus, mem_limit)
    # machines = [
    #     (100_000_000, "128m"),
    #     (200_000_000, "256m"),
    #     (250_000_000, "512m"),
    #     (400_000_000, "512m"),
    #     (500_000_000, "1g"),
    #     (800_000_000, "1g"),
    #     (1_000_000_000, "2g"),
    #     (1_200_000_000, "1.5g"),
    #     (1_600_000_000, "2g"),
    #     (2_000_000_000, "1g"),
    #     (2_000_000_000, "2g"),
    #     (2_000_000_000, "4g"),
    #     (2_000_000_000, "8g"),
    #     (2_400_000_000, "3g"),
    #     (3_200_000_000, "4g"),
    #     (4_000_000_000, "5g"),
    #     (4_000_000_000, "8g"),
    #     (4_000_000_000, "16g"),
    #     (8_000_000_000, "10g")
    # ]
    
    
    # Se itera sobre cada imagen a testear
    for nano_cpus, mem_limit in machines[:1]:
        for image in ["apirest-app", "grpc-app", "websockets-app"][1:]:
            print(f"\n--- Instanciando contenedor: {image} ---")
            host_port = create_and_start_container(image, nano_cpus, mem_limit)
            time.sleep(5)  # Espera a que el contenedor esté listo
            
            for conc in concurrencias:
                print(f"\n=== Ejecutando tests en {image} con concurrencia = {conc} ===")                
                for endpoint in ["simple", "large", "heavy", "file", "stream"]:
                    print(f"\n--- Test {image} - Endpoint '{endpoint}' ---")
                    if image == "apirest-app":  
                        if endpoint != "stream":
                            print("Ejecutando REST asincrónico")
                            asyncio.run(test_apirest_async(host_port, endpoint, conc,
                                configured_cpu=nano_cpus, configured_mem=mem_limit))
                            print("Ejecutando REST síncrono")
                            test_apirest_sync(host_port, endpoint, conc,
                                configured_cpu=nano_cpus, configured_mem=mem_limit)
                    else:
                        for cnxn in ["unica", "multiple"]:
                            if image == "grpc-app":
                                test_grpc_sync(host_port, cnxn, endpoint, concurrency=conc,
                                    configured_cpu=nano_cpus, configured_mem=mem_limit)
                                # asyncio.run(test_grpc_async(host_port, cnxn, endpoint, concurrency=conc,
                                #     configured_cpu=nano_cpus, configured_mem=mem_limit))
                                
                            elif image == "websockets-app":
                                print("Ejecutando WebSockets con única conexión:")
                                asyncio.run(test_websocket(host_port, cnxn, endpoint, conc,
                                    configured_cpu=nano_cpus, configured_mem=mem_limit))
        stop_all_containers()
    print("¡Todos los tests han finalizado!")
    print(f"Los resultados se han guardado en '{CSV_FILE}'")
