variable "aws_region" {
  default = "us-east-1"
}


# Lambda
variable "lambda_memory" { default = 512 }
variable "lambda_timeout" { default = 30 }

# EC2
variable "ec2_instance_type" { default = "t3.micro" }
variable "ec2_min_instances" { default = 1 }
variable "ec2_max_instances" { default = 3 }

# Fargate
variable "fargate_cpu" { default = 512 }
variable "fargate_memory" { default = 1024 }


variable "ecr_images" {
  description = "Mapeo de imágenes en ECR"
  type        = map(string)
}
