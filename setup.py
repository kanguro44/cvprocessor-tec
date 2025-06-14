#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de instalación para el Procesador de CVs
Este script ayuda a instalar todas las dependencias necesarias
y configurar el entorno para ejecutar la aplicación.
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Verifica que la versión de Python sea 3.7 o superior"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("Error: Se requiere Python 3.7 o superior")
        print(f"Versión actual: {platform.python_version()}")
        return False
    return True

def install_dependencies():
    """Instala las dependencias desde requirements.txt"""
    print("Instalando dependencias...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error al instalar dependencias: {e}")
        return False

def check_credentials():
    """Verifica si existe el archivo de credenciales"""
    if not os.path.exists("credentials.json"):
        print("Advertencia: No se encontró el archivo credentials.json")
        print("Este archivo es necesario para la integración con Google Drive y Google Sheets")
        print("Por favor, coloca el archivo credentials.json en la carpeta del proyecto")
        return False
    return True

def create_folders():
    """Crea las carpetas necesarias para la aplicación"""
    # Importar la constante FOLDER_CVS desde procesar_drive_cvs.py
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from procesar_drive_cvs import FOLDER_CVS
        
        if not os.path.exists(FOLDER_CVS):
            os.makedirs(FOLDER_CVS, exist_ok=True)
            print(f"Carpeta {FOLDER_CVS} creada correctamente")
        
        return True
    except Exception as e:
        print(f"Error al crear carpetas: {e}")
        return False

def main():
    """Función principal"""
    print("=== Configuración del Procesador de CVs ===")
    
    # Verificar versión de Python
    if not check_python_version():
        print("Por favor, actualiza Python a la versión 3.7 o superior")
        return
    
    # Instalar dependencias
    if not install_dependencies():
        print("Por favor, instala las dependencias manualmente:")
        print("pip install -r requirements.txt")
    
    # Verificar credenciales
    check_credentials()
    
    # Crear carpetas
    create_folders()
    
    print("\n=== Configuración completada ===")
    print("Para ejecutar la aplicación, usa el siguiente comando:")
    print("streamlit run app.py")

if __name__ == "__main__":
    main()
