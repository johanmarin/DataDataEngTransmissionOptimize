@echo off

echo 🚀 compilando las imagenes de docker...
echo call scripts\ecr.cmd


echo 🚀 obteniendo el terrraform plan...
terraform init
terraform apply -auto-approve -var-file="ecr_images.tfvars"
