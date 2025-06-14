"""
Procesador de CVs - Script de ejecución
Este script inicia la aplicación Streamlit para procesar CVs
"""

import os
import subprocess
import sys

def main():
    """Función principal para ejecutar la aplicación"""
    print("Iniciando Procesador de CVs...")
    
    # Verificar si streamlit está instalado
    try:
        import streamlit
        print("Streamlit está instalado. Iniciando aplicación...")
    except ImportError:
        print("Streamlit no está instalado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
        print("Streamlit instalado correctamente.")
    
    # Verificar otras dependencias
    try:
        import pandas
        import xlsxwriter
    except ImportError:
        print("Instalando dependencias adicionales...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "xlsxwriter"])
        print("Dependencias instaladas correctamente.")
    
    # Obtener la ruta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construir el comando para ejecutar streamlit
    app_path = os.path.join(current_dir, "app.py")
    
    # Ejecutar la aplicación
    print(f"Ejecutando aplicación desde: {app_path}")
    subprocess.run(["streamlit", "run", app_path, "--server.headless", "true"])

if __name__ == "__main__":
    main()
