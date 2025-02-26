@echo off
echo Creando estructura de carpetas y archivos...

:: Crear directorios
mkdir project
mkdir project\terraform
mkdir project\terraform\scripts
mkdir project\backends
mkdir project\load_testing
mkdir project\managed_backends
mkdir project\docker
mkdir project\scripts

:: Crear archivos vacíos en Terraform
cd project\terraform
type nul > main.tf
type nul > managed_services.tf
type nul > variables.tf
type nul > outputs.tf
cd scripts
type nul > fastapi.sh
type nul > kafka.sh
type nul > grpc.sh
type nul > websockets.sh
type nul > rabbitmq.sh
type nul > pulsar.sh
cd ..\..

:: Crear archivos vacíos en Backends
cd project\backends
type nul > fastapi_backend.py
type nul > kafka_backend.py
type nul > grpc_backend.py
type nul > websockets_backend.py
type nul > rabbitmq_backend.py
type nul > pulsar_backend.py
type nul > service.proto
cd ..

:: Crear archivos en Load Testing
cd load_testing
type nul > request_generator.py
type nul > scenarios.py
type nul > endpoints.json
cd ..

:: Crear archivos en Managed Backends
cd managed_backends
type nul > amazon_mq.py
type nul > msk_kafka.py
type nul > managed_pulsar.py
cd ..

:: Crear archivos en Docker
cd docker
type nul > Dockerfile.fastapi
type nul > Dockerfile.kafka
type nul > Dockerfile.grpc
type nul > Dockerfile.websockets
type nul > Dockerfile.rabbitmq
type nul > Dockerfile.pulsar
cd ..

:: Crear archivos en Scripts
cd scripts
type nul > deploy_backends.sh
type nul > run_tests.sh
cd ..

:: Crear README
cd project
type nul > README.md
cd ..

echo Estructura creada con éxito.
pause
