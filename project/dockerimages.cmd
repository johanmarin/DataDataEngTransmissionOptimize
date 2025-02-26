@echo off
echo 🔹 Iniciando ejecución de todos los scripts...


echo 🚀 Verificando apirest container...
if not exist artifacts\apirest-app.tar (
    echo 🛠 Construyendo apirest container...
    docker build -t apirest-app -f docker\Dockerfile.apirest .
) else (
    echo ✅ apirest-app.tar ya existe, saltando construcción.
)

echo 🚀 Verificando gRPC container...
if not exist artifacts\grpc-app.tar (
    echo 🛠 Generando archivos proto...
    call python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. backends/service.proto
    echo 🛠 Construyendo gRPC container...
    docker build -t grpc-app -f docker\Dockerfile.grpc .
) else (
    echo ✅ grpc-app.tar ya existe, saltando construcción.
)

echo 🚀 Verificando Websockets container...
if not exist artifacts\websockets-app.tar (
    echo 🛠 Construyendo Websockets container...
    docker build -t websockets-app -f docker\Dockerfile.websockets .
) else (
    echo ✅ websockets-app.tar ya existe, saltando construcción.
)

echo ✅ Todos los scripts se ejecutaron correctamente.