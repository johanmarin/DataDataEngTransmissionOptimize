terraform {
  required_version = ">= 0.14.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

##############################################
# IAM Role y Permisos para la función Lambda
##############################################
resource "aws_iam_role" "lambda_role" {
  name = "ws_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name   = "ws_lambda_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

####################################################
# Función Lambda (Docker) para manejar el WebSocket
####################################################
resource "aws_lambda_function" "ws_handler" {
  function_name = "wsHandler"
  package_type  = "Image"
  image_uri     = "302263089548.dkr.ecr.us-east-1.amazonaws.com/websockets-lambda:latest"
  role          = aws_iam_role.lambda_role.arn
}

##############################################
# API Gateway WebSocket
##############################################
resource "aws_apigatewayv2_api" "ws_api" {
  name                       = "ws-api"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

# Integración con Lambda (AWS_PROXY)
resource "aws_apigatewayv2_integration" "ws_integration" {
  api_id           = aws_apigatewayv2_api.ws_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.ws_handler.invoke_arn
  # Nota: Para WebSocket no se utiliza payload_format_version
}

# Rutas para eventos WebSocket
resource "aws_apigatewayv2_route" "connect_route" {
  api_id    = aws_apigatewayv2_api.ws_api.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_integration.id}"
}

resource "aws_apigatewayv2_route" "disconnect_route" {
  api_id    = aws_apigatewayv2_api.ws_api.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_integration.id}"
}

resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.ws_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.ws_integration.id}"
}

# Creación de un Stage para el API (por ejemplo, prod)
resource "aws_apigatewayv2_stage" "ws_stage" {
  api_id      = aws_apigatewayv2_api.ws_api.id
  name        = "prod"
  auto_deploy = true
}

####################################################
# Permiso para que API Gateway invoque la función Lambda
####################################################
resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ws_api.execution_arn}/*/*"
}

##############################################
# Salida: Endpoint del WebSocket API
##############################################
output "websocket_api_endpoint" {
  description = "Endpoint del API Gateway WebSocket (usar wss://)"
  value       = aws_apigatewayv2_api.ws_api.api_endpoint
}
