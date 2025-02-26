import os
import json
import boto3
import time

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])  # Nombre de la tabla DynamoDB

# Obtener endpoint de API Gateway
api_gateway_endpoint = os.environ.get("API_GATEWAY_ENDPOINT") or f"https://{os.environ['API_GATEWAY_ID']}.execute-api.{os.environ.get('AWS_REGION', 'us-east-1')}.amazonaws.com/$default"

def lambda_handler(event, context):
    print(f"🟢 Evento recibido: {json.dumps(event)}")

    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")
    body = json.loads(event["body"]) if "body" in event and event["body"] else {}

    if route_key == "$connect":
        print(f"✅ Nueva conexión: {connection_id}")
        table.put_item(Item={"connectionId": connection_id})
        return {"statusCode": 200}

    elif route_key == "$disconnect":
        print(f"❌ Conexión cerrada: {connection_id}")
        table.delete_item(Key={"connectionId": connection_id})
        return {"statusCode": 200}

    elif route_key == "sendMessage":
        message = body.get("message", "")
        return handle_message(connection_id, message)

    else:
        return {"statusCode": 400, "body": "Invalid route"}

def handle_message(connection_id, message):
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=api_gateway_endpoint)

    response = ""
    if message == "simple":
        response = "Hello, world!"
    elif message == "large":
        response = json.dumps({"data": ["x" * 10000 for _ in range(100)]})
    elif message == "heavy":
        time.sleep(2)
        response = "done"
    elif message == "stream":
        for i in range(10):
            try:
                apigw.post_to_connection(ConnectionId=connection_id, Data=json.dumps({"message": f"Message {i}"}))
                time.sleep(1)
            except apigw.exceptions.GoneException:
                print(f"❌ Conexión {connection_id} cerrada, eliminándola de DynamoDB")
                table.delete_item(Key={"connectionId": connection_id})
                return {"statusCode": 410, "body": "Connection closed"}
        return {"statusCode": 200}
    elif message == "file":
        response = "Archivo no soportado en Lambda WebSockets"
    elif message == "exit":
        try:
            apigw.delete_connection(ConnectionId=connection_id)
        except apigw.exceptions.GoneException:
            print(f"❌ Conexión {connection_id} ya estaba cerrada.")
        return {"statusCode": 200, "body": "Connection closed"}
    else:
        response = "ERROR: Comando no reconocido."

    try:
        apigw.post_to_connection(ConnectionId=connection_id, Data=response)
    except apigw.exceptions.GoneException:
        print(f"❌ Conexión {connection_id} cerrada, eliminándola de DynamoDB")
        table.delete_item(Key={"connectionId": connection_id})

    return {"statusCode": 200}
