@echo off
setlocal EnableDelayedExpansion

set REGION=us-east-1
set ECR_TFVARS_FILE=ecr_images.tfvars

:: 🔹 Lista de imágenes a procesar
set IMAGE_NAMES=apirest-lambda apirest websockets grpc websockets-lambda

:: 🔹 Obtener AWS_ACCOUNT_ID automáticamente desde AWS CLI
for /f "tokens=*" %%i in ('aws sts get-caller-identity --query "Account" --output text 2^>error.log') do set AWS_ACCOUNT_ID=%%i
if not defined AWS_ACCOUNT_ID (
    echo ❌ Error obteniendo AWS_ACCOUNT_ID. Verifica que AWS CLI esté configurado correctamente.
    type error.log
    exit /b 1
)

set ECR_URL=%AWS_ACCOUNT_ID%.dkr.ecr.%REGION%.amazonaws.com

:: 🔹 Autenticarse en AWS ECR
echo 🚀 Autenticando en AWS ECR...
aws ecr get-login-password --region %REGION% | docker login --username AWS --password-stdin %ECR_URL%
if %ERRORLEVEL% neq 0 (
    echo ❌ Error autenticando en AWS ECR. Verifica tus credenciales.
    exit /b 1
)

:: 🔹 Inicializar archivo .tfvars
echo ecr_images = { > %ECR_TFVARS_FILE%

:: 🔹 Iterar sobre cada imagen y procesarla
for %%I in (%IMAGE_NAMES%) do (
    echo ------------------------------------------
    echo 🔹 Procesando imagen: %%I
    echo ------------------------------------------

    set IMAGE_NAME=%%I
    set DOCKERFILE=docker\Dockerfile.%%I

    :: 🔹 Verificar si el repositorio ya existe en ECR, si no, crearlo
    aws ecr describe-repositories --repository-names %%I --region %REGION% >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo 🛠 Creando repositorio %%I en AWS ECR...
        aws ecr create-repository --repository-name %%I --region %REGION%
        if !ERRORLEVEL! neq 0 (
            echo ❌ Error creando repositorio %%I en AWS ECR.
            exit /b 1
        )
    ) else (
        echo ✅ El repositorio %%I ya existe en AWS ECR.
    )

    :: 🔹 Eliminar imagen local antes de recompilar
    echo 🗑 Eliminando imagen local %%I...
    docker rmi -f %%I 2>nul

    :: 🔹 Compilar nueva imagen
    echo 🚀 Construyendo nueva imagen %%I...
    docker build -t %%I -f !DOCKERFILE! .
    if !ERRORLEVEL! neq 0 (
        echo ❌ Error compilando la imagen %%I.
        exit /b 1
    )

    :: 🔹 Obtener hash de la imagen local
    for /f "tokens=*" %%j in ('docker images --format "{{.ID}}" %%I') do set LOCAL_HASH=%%j

    :: 🔹 Obtener hash de la imagen en ECR (si existe)
    set ECR_HASH=
    for /f %%j in ('aws ecr describe-images --repository-name %%I --query "imageDetails[0].imageDigest" --output text --region %REGION% 2^>nul') do set ECR_HASH=%%j

    if defined ECR_HASH (
        :: 🔹 Comparar hashes
        if "!LOCAL_HASH!"=="!ECR_HASH!" (
            echo ✅ La imagen %%I ya está en ECR y no ha cambiado.
        ) else (
            echo 🔄 La imagen en ECR es diferente, actualizando...

            :: Eliminar imagen anterior en ECR
            aws ecr batch-delete-image --repository-name %%I --image-ids imageDigest=!ECR_HASH! --region %REGION% >nul 2>&1
            echo 🗑 Imagen anterior eliminada en AWS ECR.

            :: Subir nueva imagen a ECR
            docker tag %%I %ECR_URL%/%%I:latest
            docker push %ECR_URL%/%%I:latest
            if !ERRORLEVEL! neq 0 (
                echo ❌ Error subiendo la imagen %%I a ECR.
                exit /b 1
            )
            echo ✅ Imagen %%I actualizada en ECR.
        )
    ) else (
        :: 🔹 Si la imagen no existe en ECR, subirla
        echo 🚀 Imagen %%I no existe en ECR. Subiéndola...
        docker tag %%I %ECR_URL%/%%I:latest
        docker push %ECR_URL%/%%I:latest
        if !ERRORLEVEL! neq 0 (
            echo ❌ Error subiendo la imagen %%I a ECR.
            exit /b 1
        )
        echo ✅ Imagen %%I subida a ECR.
    )

    :: 🔹 Guardar URL en el .tfvars
    echo   "%%I" = "%ECR_URL%/%%I:latest", >> %ECR_TFVARS_FILE%
)
echo   } >> %ECR_TFVARS_FILE%
echo ✅ Todas las imágenes fueron procesadas correctamente.
