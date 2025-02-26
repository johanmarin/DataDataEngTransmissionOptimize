
provider "aws" {
  region = "us-east-1" # Cambia a tu región
}

# 🔹 IAM Role para Lambda
resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"

  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}


# # 🔹 IAM Role para Lambda
# resource "aws_iam_role" "lambda_role2" {
#   name = "apirest_lambda_role2"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Action = "sts:AssumeRole"
#       Effect = "Allow"
#       Principal = { Service = "lambda.amazonaws.com" }
#     }]
#   })
# }

# # 🔹 Políticas para que Lambda escriba logs en CloudWatch
# resource "aws_iam_policy_attachment" "lambda_logs" {
#   name       = "lambda_logs"
#   roles      = [aws_iam_role.lambda_role2.name]
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
# }

# # 🔹 Crear Lambda Function
# resource "aws_lambda_function" "apirest_lambda" {
#   function_name = "apirest_lambda"
#   runtime       = "python3.12"
#   handler       = "main.lambda_handler"
#   role          = aws_iam_role.lambda_role2.arn

#   filename         = "artifacts/apirest_lambda.zip"
#   source_code_hash = filebase64sha256("artifacts/apirest_lambda.zip")

#   environment {
#     variables = {
#       API_GATEWAY_URL = aws_apigatewayv2_api.apirest_api.api_endpoint
#     }
#   }
# }

# # 🔹 Crear API Gateway HTTP
# resource "aws_apigatewayv2_api" "apirest_api" {
#   name            = "apirest-api"
#   protocol_type   = "HTTP"
# }

# # 🔹 Integrar API Gateway con Lambda
# resource "aws_apigatewayv2_integration" "apirest_integration" {
#   api_id             = aws_apigatewayv2_api.apirest_api.id
#   integration_type   = "AWS_PROXY"
#   integration_uri    = aws_lambda_function.apirest_lambda.invoke_arn
# }

# # 🔹 Crear la ruta raíz "/" para manejar FastAPI dinámicamente
# resource "aws_apigatewayv2_route" "apirest_route" {
#   api_id    = aws_apigatewayv2_api.apirest_api.id
#   route_key = "ANY /{proxy+}"
#   target    = "integrations/${aws_apigatewayv2_integration.apirest_integration.id}"
# }

# # 🔹 Permitir que API Gateway invoque la Lambda
# resource "aws_lambda_permission" "apirest_api_permission" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.apirest_lambda.function_name
#   principal     = "apigateway.amazonaws.com"

#   source_arn = "${aws_apigatewayv2_api.apirest_api.execution_arn}/*/*"
# }

# # 🔹 Desplegar API Gateway
# resource "aws_apigatewayv2_stage" "apirest_stage" {
#   api_id      = aws_apigatewayv2_api.apirest_api.id
#   name        = "production"
#   auto_deploy = true
# }

# # 🔹 Mostrar el Endpoint de la API
# output "apirest_api_url" {
#   value = aws_apigatewayv2_api.apirest_api.api_endpoint
# }
