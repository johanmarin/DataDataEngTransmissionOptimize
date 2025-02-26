import numpy as np
from scipy.optimize import minimize
import numpy as np

def predict_capacity(concurrency, vcpu, volumen, tool):
    """
    Calcula la capacidad de procesamiento predicha (throughput) para una instancia,
    según la tecnología especificada.
    
    Parámetros:
      - concurrency: número de peticiones simultáneas (C)
      - vcpu: cantidad de vCPU (V)
      - volumen: tamaño del payload (L)
      - tool: una cadena que indique 'apirest', 'grpc' o 'websocket'
      
    Retorna:
      - La capacidad de procesamiento predicha, calculada como:
        mu = exp(modelo), donde el modelo es el valor de log(mu) según el modelo correspondiente.
    """
    tool = tool.lower()
    if tool == "apirest":
        log_mu = (-1.186e-7 * concurrency + 0.5323 * vcpu + 0.0002 * volumen 
                  - 47.9322 * (volumen ** 2) - 5.932e-5 * (concurrency ** 2)
                  + 0.1019 * (volumen * concurrency))
    elif tool == "grpc":
        log_mu = (-8.3651 - 0.0097 * concurrency + 0.7644 * vcpu + 51.4944 * volumen 
                  - 44.9057 * (volumen ** 2) + 9.877e-6 * (concurrency ** 2)
                  + 0.0032 * (volumen * concurrency))
    elif tool in ["websocket", "websockets"]:
        log_mu = (-7.1534 - 0.0163 * concurrency + 0.4592 * vcpu - 3.144e4 * volumen 
                  - 5.1573 * (volumen ** 2) + 7.817e-7 * (concurrency ** 2)
                  + 114.4586 * (volumen * concurrency))
    else:
        raise ValueError("La herramienta debe ser 'apirest', 'grpc' o 'websocket'.")
    
    return np.exp(log_mu)


# Definir la estructura del diccionario de configuración
aws_tools_config = {
    "apirest": {
        "gestionado": {
            "instancias": ["lambda"],
            "costos": {
                "C_sl_H": 3.50,  # USD por millón de solicitudes
                "C_tr_H_aws": 0.09,  # USD por GB transferido en AWS
                "C_tr_H_externo": 0.09,  # USD por GB transferido fuera de AWS
                "C_cn_H": None,  # No aplica costo de conexión
            },
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {
                "C_sl_H": None,  # No hay costo por solicitud
                "C_tr_H_aws": 0.01,  # USD por GB transferido en AWS
                "C_tr_H_externo": 0.09,  # USD por GB transferido fuera de AWS
                "C_cn_H": None,  # No aplica costo de conexión
            },
        },
    },
    "grpc": {
        "gestionado": {
            "instancias": ["fargate-0.25", "fargate-0.5", "fargate-1", "fargate-2", "fargate-4"],
            "costos": {
                "C_sl_H": None,
                "C_tr_H_aws": None,
                "C_tr_H_externo": 0.09,
                "C_cn_H": None,
            },
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {
                "C_sl_H": None,
                "C_tr_H_aws": None,
                "C_tr_H_externo": 0.09,
                "C_cn_H": None,
            },
        },
    },
    "websockets": {
        "gestionado": {
            "instancias": ["lambda"],
            "costos": {
                "C_sl_H": 3.50,  # USD por millón de mensajes
                "C_tr_H_aws": 0.09,
                "C_tr_H_externo": 0.09,
                "C_cn_H": 0.25,  # USD por millón de minutos de conexión
            },
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {
                "C_sl_H": None,
                "C_tr_H_aws": None,
                "C_tr_H_externo": 0.09,
                "C_cn_H": None,
            },
        },
    },
}

aws_instances = {
    "lambda": {"vcpu": 0.1, "memory_gib": 0.125, "cost_per_hour": 0.00000625},
    "t3.micro": {"vcpu": 2, "memory_gib": 1, "cost_per_hour": 0.0104},
    "t3.small": {"vcpu": 2, "memory_gib": 2, "cost_per_hour": 0.0208},
    "t3.medium": {"vcpu": 2, "memory_gib": 4, "cost_per_hour": 0.0416},
    "m5.large": {"vcpu": 2, "memory_gib": 8, "cost_per_hour": 0.096},
    "m5.xlarge": {"vcpu": 4, "memory_gib": 16, "cost_per_hour": 0.192},
    "fargate-0.25": {"vcpu": 0.25, "memory_gib": 0.5, "cost_per_hour": 0.0123},
    "fargate-0.5": {"vcpu": 0.5, "memory_gib": 1, "cost_per_hour": 0.0246},
    "fargate-1": {"vcpu": 1, "memory_gib": 2, "cost_per_hour": 0.0492},
    "fargate-2": {"vcpu": 2, "memory_gib": 4, "cost_per_hour": 0.0984},
    "fargate-4": {"vcpu": 4, "memory_gib": 8, "cost_per_hour": 0.1968},
}

# Restricciones: Debemos garantizar que la capacidad de procesamiento cubra la carga esperada
def restriccion_procesamiento(x, tool, deploy_model, lambda_max, v_max):
    """
    Garantiza que las instancias seleccionadas cubran la demanda de procesamiento.
    """
    N_p = x[0]
    instancias = aws_tools_config[tool][deploy_model]["instancias"]
    instancia = aws_instances[instancias[0]]
    v_pr = predict_capacity(concurrency=lambda_max, vcpu=instancia["vcpu"], volumen=v_max, tool=tool)
    
    return N_p * v_pr - lambda_max


def costo_total(x, tool, deploy_model, instancia, gamma, lambda_max, v_max, d_req, u_max=0.8, u_min=0.2, k=0.1):
    """
    Calcula el costo total basado en la cantidad de instancias seleccionadas.
    """
    # Obtener costos y capacidad de procesamiento
    C_pr = aws_instances[instancia]["cost_per_hour"] / 3600
    vcpu = aws_instances[instancia]["vcpu"]
    
    I_pr_min = 0 if deploy_model == "gestionado" else 1  
    costos = aws_tools_config[tool][deploy_model]["costos"] 

    # Calcular sesgo y capacidad de procesamiento
    bias_v = (v_max - (v_max / 2)) / (v_max / 2)
    rho_pr = predict_capacity(lambda_max, vcpu, v_max, tool)
    
    # Calcular umbral de utilización correcto
    u = max(u_min, min(u_max, 1 - k * bias_v * (lambda_max * v_max / rho_pr)))

    # Número de instancias necesarias
    I_pr = max(I_pr_min, gamma / (rho_pr * u)) 
    
    # Costo de infraestructura
    C_infra = I_pr * gamma / (rho_pr * I_pr) * C_pr
    
    # Tiempo de uso y costo de inactividad
    T_uso = max(d_req, gamma / (rho_pr * I_pr))
    C_inact = max(0, d_req - T_uso) * C_pr * I_pr_min
    
    # Costo de transferencia
    C_transferencia = gamma * costos["C_tr_H_aws"] if costos["C_tr_H_aws"] else 0
    
    # Costo por solicitudes
    C_solicitudes = lambda_max * costos["C_sl_H"] if costos["C_sl_H"] else 0
    
    return C_infra + C_inact + C_transferencia + C_solicitudes

def restriccion_positividad(x):
    """
    Restricción de positividad: todas las variables deben ser mayores o iguales a 1.
    """
    return min(x) - 1  # Debe ser >= 0

def restriccion_nodos_maximos(x, tool, deploy_model, lambda_max, nodos_max=100):
    """
    Restricción de recursos limitados: el número de nodos no debe exceder un máximo.
    """
    instancias = aws_tools_config[tool][deploy_model]["instancias"]
    capacidad_total = sum(
        predict_capacity(lambda_max, aws_instances[inst]["vcpu"], 1, tool)
        for inst in instancias
    )
    return nodos_max - (lambda_max / capacidad_total)  # Debe ser >= 0

# Modificar la función de optimización para incluir estas restricciones
def optimizar_configuracion_restringida(gamma, lambda_max, v_max, d_req):
    resultados = []
    for tool, tool_data in aws_tools_config.items():
        for deploy_model, deploy_data in tool_data.items():
            instancias = deploy_data["instancias"]
            for instancia in instancias:
                x0 = np.ones(len(instancias))  # Inicialización con 1 instancia por tipo

                # Restricciones del modelo
                restricciones = [
                    {"type": "ineq", "fun": restriccion_positividad},
                    {"type": "ineq", "fun": restriccion_nodos_maximos, "args": (tool, deploy_model, lambda_max)},
                ]

                # Optimización
                resultado = minimize(costo_total, x0, args=(tool, deploy_model, instancia, gamma, lambda_max, v_max, d_req),
                                    method="SLSQP", constraints=restricciones, bounds=[(1, None)] * len(instancias))

                if resultado.success:
                    resultados.append({
                        "herramienta": tool,
                        "modelo": deploy_model,
                        "instancias": {inst: int(resultado.x[i]) for i, inst in enumerate(instancias)},
                        "costo_total": resultado.fun
                    })

    # Ordenar por costo y devolver las tres mejores opciones
    return sorted(resultados, key=lambda x: x["costo_total"])[:3]

# Pruebas con las nuevas restricciones
pruebas_restringidas = [
    {"gamma": 100000, "lambda_max": 500, "v_max": 90, "d_req": 7},  # Caso base
    {"gamma": 500000, "lambda_max": 2000, "v_max": 2, "d_req": 24},  # Carga alta
    {"gamma": 10000, "lambda_max": 100, "v_max": 0.5, "d_req": 3},  # Carga baja
]

# Ejecutar pruebas
resultados_pruebas_restringidas = {f"Prueba {i+1}": optimizar_configuracion_restringida(**test) for i, test in enumerate(pruebas_restringidas)}
print(resultados_pruebas_restringidas)
