import numpy as np
from scipy.optimize import minimize

# Definir la función predict_capacity
def predict_capacity(concurrency, vcpu, volumen, tool):
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

# Definir diccionarios de configuración
aws_tools_config = {
    "apirest": {
        "gestionado": {
            "instancias": ["lambda"],
            "costos": {"C_sl_H": 3.50, "C_tr_H_aws": 0.09, "C_tr_H_externo": 0.09, "C_cn_H": None},
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {"C_sl_H": None, "C_tr_H_aws": 0.01, "C_tr_H_externo": 0.09, "C_cn_H": None},
        },
    },
    "grpc": {
        "gestionado": {
            "instancias": ["fargate-0.25", "fargate-0.5", "fargate-1", "fargate-2", "fargate-4"],
            "costos": {"C_sl_H": None, "C_tr_H_aws": None, "C_tr_H_externo": 0.09, "C_cn_H": None},
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {"C_sl_H": None, "C_tr_H_aws": None, "C_tr_H_externo": 0.09, "C_cn_H": None},
        },
    },
    "websockets": {
        "gestionado": {
            "instancias": ["lambda"],
            "costos": {"C_sl_H": 3.50, "C_tr_H_aws": 0.09, "C_tr_H_externo": 0.09, "C_cn_H": 0.25},
        },
        "autogestionado": {
            "instancias": ["t3.micro", "t3.small", "t3.medium", "m5.large", "m5.xlarge"],
            "costos": {"C_sl_H": None, "C_tr_H_aws": None, "C_tr_H_externo": 0.09, "C_cn_H": None},
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

# Definir función de optimización con restricciones
def optimizar_configuracion_restringida(gamma, lambda_max, v_max, d_req):
    resultados = []
    for tool, tool_data in aws_tools_config.items():
        for deploy_model, deploy_data in tool_data.items():
            instancias = deploy_data["instancias"]
            if not instancias:
                continue

            x0 = np.ones(len(instancias))  # Inicialización con 1 instancia por tipo

            # Restricciones
            restricciones = [{"type": "ineq", "fun": lambda x: min(x) - 1}]

            # Optimización
            resultado = minimize(
                lambda x: sum(x) * aws_instances[instancias[0]]["cost_per_hour"],
                x0,
                method="SLSQP",
                constraints=restricciones,
                bounds=[(1, None)] * len(instancias),
            )

            if resultado.success:
                resultados.append({
                    "herramienta": tool,
                    "modelo": deploy_model,
                    "instancias": {inst: int(resultado.x[i]) for i, inst in enumerate(instancias)},
                    "costo_total": resultado.fun
                })

    # Ordenar por costo y devolver las tres mejores opciones
    return sorted(resultados, key=lambda x: x["costo_total"])[:3]

# Definir casos de prueba
pruebas_restringidas = [
    {"gamma": 100000, "lambda_max": 500, "v_max": 90, "d_req": 7},
    {"gamma": 500000, "lambda_max": 2000, "v_max": 2, "d_req": 24},
    {"gamma": 10000, "lambda_max": 100, "v_max": 0.5, "d_req": 3},
]

# Ejecutar pruebas y mostrar resultados
resultados_pruebas_restringidas = {f"Prueba {i+1}": optimizar_configuracion_restringida(**test) for i, test in enumerate(pruebas_restringidas)}

# Mostrar resultados en formato de tabla
import pandas as pd

df_resultados = []
for prueba, resultados in resultados_pruebas_restringidas.items():
    for resultado in resultados:
        df_resultados.append({
            "Prueba": prueba,
            "Herramienta": resultado["herramienta"],
            "Modelo": resultado["modelo"],
            "Instancias": resultado["instancias"],
            "Costo Total": resultado["costo_total"]
        })

df_resultados = pd.DataFrame(df_resultados)

# Mostrar tabla de resultados
# Convertir los resultados en un DataFrame
df_resultados = pd.DataFrame(resultados_pruebas_restringidas)
# Mostrar los resultados en forma de tabla
print(df_resultados)