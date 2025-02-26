
variable "service_name" {
  default = "apirest-lambda"
}

# 🔹 Función Lambda
resource "aws_lambda_function" "lambda" {
  function_name = "apirest-lambda"
  package_type  = "Image"
  image_uri     = var.ecr_images["apirest-lambda"]
  memory_size   = var.lambda_memory
  timeout       = var.lambda_timeout
  role          = aws_iam_role.lambda_role.arn
}


# 🔹 API Gateway HTTP
resource "aws_apigatewayv2_api" "api" {
  name          = "apirest-lambda-api"
  protocol_type = "HTTP"
}

# 🔹 Integración API Gateway <-> Lambda
resource "aws_apigatewayv2_integration" "integration" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.lambda.invoke_arn
  payload_format_version = "2.0"
}

# 🔹 Ruta (ANY /{proxy+})
resource "aws_apigatewayv2_route" "route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.integration.id}"
}

# 🔹 Etapa de despliegue
resource "aws_apigatewayv2_stage" "stage" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

# 🔹 Permiso para que API Gateway invoque la Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda.function_name
  principal     = "apigateway.amazonaws.com"
  # El ARN de la API Gateway debe coincidir con el formato que API Gateway usa para invocar funciones
  source_arn = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

output "api_url" {
  value = aws_apigatewayv2_api.api.api_endpoint
}
