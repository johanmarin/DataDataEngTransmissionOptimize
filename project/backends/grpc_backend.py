import grpc
from concurrent import futures
import service_pb2
import service_pb2_grpc
import json
import time

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
    elif message == "stream":
        # El manejo de stream se realiza en process_request
        response = None
    else:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Unknown command: {message}")
    return response

def process_request(msg, context):
    """Genera respuestas según el comando recibido."""
    if msg == "stream":
        for i in range(10):
            yield service_pb2.Response(message=f"Message {i}")
    else:
        response = build_response(msg, context)
        yield service_pb2.Response(message=response)

class Backend(service_pb2_grpc.BackendServicer):
    def Call(self, request_iterator, context):
        for req in request_iterator:
            yield from process_request(req.message, context)

def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=50),
        options=[
            ('grpc.max_send_message_length', 100 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024)
        ]
    )
    service_pb2_grpc.add_BackendServicer_to_server(Backend(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("Server started on port 50051")
    server.wait_for_termination()
