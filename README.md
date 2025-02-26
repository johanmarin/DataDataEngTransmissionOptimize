# DataDataEngTransmissionOptimize
Este repositorio contiene un modelo de optimización multiobjetivo para seleccionar la tecnología de transmisión de datos más adecuada en sistemas distribuidos. Se evalúan tecnologías como REST, gRPC, GraphQL, SFTP, WebSockets y sistemas de colas (Kafka, RabbitMQ) considerando latencia, seguridad, escalabilidad y costos.

# Proyecto de Optimización y Backend

Este proyecto incluye varios componentes para la optimización y gestión de backends utilizando diferentes tecnologías y servicios. A continuación se detalla la estructura del proyecto y las funcionalidades principales.

## Estructura del Proyecto


```
DataDataEngTransmissionOptimize
├─ endpoints.json
├─ LICENSE
├─ project
│  ├─ .terraform
│  │  ├─ modules
│  │  │  └─ modules.json
│  │  └─ providers
│  │     └─ registry.terraform.io
│  │        └─ hashicorp
│  │           ├─ aws
│  │           │  ├─ 4.0.0
│  │           │  │  └─ windows_amd64
│  │           │  │     └─ terraform-provider-aws_v4.0.0_x5.exe
│  │           │  └─ 5.87.0
│  │           │     └─ windows_amd64
│  │           │        ├─ LICENSE.txt
│  │           │        └─ terraform-provider-aws_v5.87.0_x5.exe
│  │           └─ random
│  │              └─ 3.1.3
│  │                 └─ windows_amd64
│  │                    └─ terraform-provider-random_v3.1.3_x5.exe
│  ├─ attachments
│  ├─ backends
│  │  ├─ apirest_lambda.py
│  │  ├─ fastapi_backend.py
│  │  ├─ grpc_backend.py
│  │  ├─ service.proto
│  │  ├─ service_pb2.py
│  │  ├─ service_pb2_grpc.py
│  │  ├─ websockets_backend.py
│  │  └─ websockets_lambda.py
│  ├─ data
│  │  ├─ adaptive_metrics.csv
│  │  ├─ data.csv
│  │  └─ metrics.csv
│  ├─ docker
│  │  ├─ Dockerfile.apirest
│  │  ├─ Dockerfile.apirest-lambda
│  │  ├─ Dockerfile.grpc
│  │  ├─ Dockerfile.websockets
│  │  └─ Dockerfile.websockets-lambda
│  ├─ dockerimages.cmd
│  ├─ experimento.py
│  ├─ generated_files
│  │  ├─ 1MB.json
│  │  ├─ 2MB.json
│  │  └─ 3MB.json
│  ├─ model.py
│  ├─ modelo_capacidad_proceasmiento.ipynb
│  ├─ modelo_optimizacion.py
│  ├─ pruebas_modelo.ipynb
│  ├─ scripts
│  │  ├─ ecr.cmd
│  │  └─ run.cmd
│  └─ terraform
│     ├─ .terraform.lock.hcl
│     ├─ apirest.tf
│     ├─ ecr_images.tfvars
│     ├─ main.tf
│     ├─ terraform.tfstate
│     ├─ terraform.tfstate.backup
│     ├─ variables.tf
│     └─ websockets.tf
├─ README.md
├─ request_generator.py
├─ scenarios.py
└─ setup_project.bat

```

### Archivos y Directorios Principales

- **project/**: Directorio principal del proyecto.
  - **__pycache__/**: Archivos compilados de Python.
  - **.terraform/**: Configuraciones y módulos de Terraform.
  - **attachments/**: Archivos adjuntos utilizados en el proyecto.
  - **backends/**: Implementaciones de diferentes backends.
  - **data/**: Directorio para almacenar datos.
  - **docker/**: Archivos Docker para construir imágenes de contenedores.
  - **generated_files/**: Archivos generados automáticamente.
  - **scripts/**: Scripts para automatización y despliegue.
  - **terraform/**: Configuraciones de Terraform para infraestructura.

### Archivos Docker

- **Dockerfile.websockets**: Configuración para un backend de WebSockets.
- **Dockerfile.websockets-lambda**: Configuración para un backend de WebSockets en AWS Lambda.
- **Dockerfile.apirest**: Configuración para un backend API REST.
- **Dockerfile.apirest-lambda**: Configuración para un backend API REST en AWS Lambda.

### Scripts

- **setup_project.bat**: Script para crear la estructura de carpetas y archivos del proyecto.

### Archivos de Código

- **experimento.py**: Archivo principal para experimentos.
- **model.py**: Modelo de datos.
- **modelo_capacidad_proceasmiento.ipynb**: Notebook para el modelo de capacidad de procesamiento.
- **modelo_optimizacion.py**: Implementación del modelo de optimización.
- **pruebas_modelo.ipynb**: Notebook para pruebas del modelo.
- **request_generator.py**: Generador de solicitudes para pruebas de carga.
- **scenarios.py**: Definición de escenarios para pruebas de carga.

## Licencia

Este proyecto está bajo la licencia especificada en el archivo [LICENSE](LICENSE).

## Cómo Empezar

1. Clona el repositorio.
2. Ejecuta el script `setup_project.bat` para crear la estructura de carpetas y archivos necesarios.
3. Configura los archivos Docker y Terraform según tus necesidades.
4. Despliega los backends utilizando los scripts en el directorio `scripts`.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para discutir cualquier cambio que te gustaría hacer.

## Contacto

Para cualquier consulta, por favor contacta al mantenedor del proyecto.
