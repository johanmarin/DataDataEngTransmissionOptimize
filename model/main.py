import streamlit as st
import pandas as pd
from model import optimizar_configuracion_restringida

# Configuración del frontend en Streamlit
st.set_page_config(page_title="Optimización AWS", layout="wide")

st.title("Optimización de Configuración en AWS")

st.sidebar.header("Parámetros de entrada")

gamma = st.sidebar.number_input("Gamma", min_value=1, value=100000)
lambda_max = st.sidebar.number_input("Lambda Max", min_value=1, value=500)
v_max = st.sidebar.number_input("Volumen Max", min_value=1, value=90)
d_req = st.sidebar.number_input("Duración Requerida", min_value=1, value=7)

if st.sidebar.button("Ejecutar Optimización"):
    resultados = optimizar_configuracion_restringida(gamma, lambda_max, v_max, d_req)
    df_resultados = pd.DataFrame(resultados)
    
    st.write("### Resultados de Optimización")
    st.dataframe(df_resultados)
    
    # Mostrar detalles de cada configuración
    for i, res in enumerate(resultados):
        st.subheader(f"Opción {i+1}: {res['herramienta'].capitalize()} - {res['modelo'].capitalize()}")
        st.write("**Instancias:**", res["instancias"])
        st.write("**Costo Total:**", f"${res['costo_total']:.2f}")
