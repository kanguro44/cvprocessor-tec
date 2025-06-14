#!/usr/bin/env python3
"""
Script para desplegar la aplicación en la nube
Este script automatiza todo el proceso de despliegue en la nube,
incluyendo la preparación del código y la subida a GitHub.
"""

import os
import subprocess
import sys
import time

def print_color(text, color="green"):
    """Imprime texto con color"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "end": "\033[0m"
    }
    print(f"{colors.get(color, colors['green'])}{text}{colors['end']}")

def ejecutar_comando(comando, mostrar_salida=True):
    """Ejecuta un comando y devuelve su salida"""
    try:
        resultado = subprocess.run(comando, shell=True, check=True, text=True, 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if mostrar_salida and resultado.stdout:
            print(resultado.stdout)
        return True, resultado.stdout
    except subprocess.CalledProcessError as e:
        print_color(f"Error al ejecutar el comando: {comando}", "red")
        print_color(f"Código de error: {e.returncode}", "red")
        print_color(f"Salida de error: {e.stderr}", "red")
        return False, e.stderr

def preparar_para_nube():
    """Prepara la aplicación para su despliegue en la nube"""
    print_color("\n=== PREPARACIÓN PARA DESPLIEGUE EN LA NUBE ===\n", "blue")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app_dashboard.py"):
        print_color("❌ Error: Este script debe ejecutarse desde el directorio cvprocessor-tec-new", "red")
        print_color("   Por favor, ejecuta: cd /ruta/a/cvprocessor-tec-new", "yellow")
        return False
    
    # Ejecutar el script preparar_para_nube.py
    print_color("Ejecutando script preparar_para_nube.py...", "blue")
    exito, _ = ejecutar_comando("python3 preparar_para_nube.py")
    if not exito:
        print_color("Error al ejecutar el script preparar_para_nube.py.", "red")
        return False
    
    print_color("✅ Preparación para la nube completada", "green")
    return True

def subir_a_github():
    """Sube el código a GitHub"""
    print_color("\n=== SUBIR CÓDIGO A GITHUB ===\n", "blue")
    
    # Verificar Git
    print_color("Verificando si Git está instalado...", "blue")
    exito, _ = ejecutar_comando("git --version", mostrar_salida=False)
    if not exito:
        print_color("Git no está instalado. Por favor, instala Git antes de continuar.", "red")
        return False
    print_color("✅ Git está instalado", "green")
    
    # Solicitar credenciales
    usuario = "kanguro44"  # Usuario de GitHub
    token = "Fb5cteeaml."  # Contraseña de GitHub
    nombre_repo = "cvprocessor-tec"
    
    # Inicializar repositorio
    print_color("Inicializando repositorio Git...", "blue")
    if os.path.exists(".git"):
        print_color("Ya existe un repositorio Git en este directorio.", "yellow")
    else:
        exito, _ = ejecutar_comando("git init")
        if not exito:
            print_color("Error al inicializar el repositorio Git.", "red")
            return False
    print_color("✅ Repositorio Git inicializado", "green")
    
    # Configurar usuario
    print_color(f"Configurando usuario de Git: {usuario}...", "blue")
    exito, _ = ejecutar_comando(f'git config user.name "{usuario}"')
    if not exito:
        print_color("Error al configurar el nombre de usuario de Git.", "red")
        return False
    exito, _ = ejecutar_comando(f'git config user.email "{usuario}@github.com"')
    if not exito:
        print_color("Error al configurar el email de Git.", "red")
        return False
    print_color("✅ Usuario de Git configurado", "green")
    
    # Agregar archivos
    print_color("Agregando archivos al repositorio...", "blue")
    exito, _ = ejecutar_comando("git add .")
    if not exito:
        print_color("Error al agregar archivos al repositorio.", "red")
        return False
    print_color("✅ Archivos agregados al repositorio", "green")
    
    # Crear commit
    print_color("Creando commit...", "blue")
    exito, _ = ejecutar_comando('git commit -m "Initial commit - Procesador de CVs"')
    if not exito:
        print_color("Error al crear el commit.", "red")
        return False
    print_color("✅ Commit creado", "green")
    
    # Crear repositorio en GitHub
    print_color(f"Creando repositorio en GitHub: {nombre_repo}...", "blue")
    print_color("Verificando si el repositorio ya existe...", "blue")
    comando_verificar = f'curl -s -o /dev/null -w "%{{http_code}}" -u "{usuario}:{token}" https://api.github.com/repos/{usuario}/{nombre_repo}'
    exito, salida = ejecutar_comando(comando_verificar, mostrar_salida=False)
    if exito and salida.strip() == "200":
        print_color(f"El repositorio {nombre_repo} ya existe en GitHub.", "yellow")
    else:
        privado_str = "true"  # Repositorio privado
        comando_crear = f'curl -u "{usuario}:{token}" https://api.github.com/user/repos -d \'{{"name":"{nombre_repo}","private":{privado_str}}}\''
        exito, _ = ejecutar_comando(comando_crear)
        if not exito:
            print_color(f"Error al crear el repositorio {nombre_repo} en GitHub.", "red")
            return False
    print_color(f"✅ Repositorio {nombre_repo} creado en GitHub", "green")
    
    # Agregar remoto
    print_color("Agregando remoto al repositorio...", "blue")
    exito, salida = ejecutar_comando("git remote -v", mostrar_salida=False)
    if exito and "origin" in salida:
        print_color("Ya existe un remoto llamado origin. Eliminándolo...", "yellow")
        ejecutar_comando("git remote remove origin")
    exito, _ = ejecutar_comando(f"git remote add origin https://github.com/{usuario}/{nombre_repo}.git")
    if not exito:
        print_color("Error al agregar el remoto al repositorio.", "red")
        return False
    print_color("✅ Remoto agregado al repositorio", "green")
    
    # Subir a GitHub
    print_color("Subiendo código a GitHub (rama main)...", "blue")
    os.environ["GIT_ASKPASS"] = "echo"
    os.environ["GIT_USERNAME"] = usuario
    os.environ["GIT_PASSWORD"] = token
    comando_push = "git push -u origin main"
    exito, _ = ejecutar_comando(comando_push)
    os.environ.pop("GIT_ASKPASS", None)
    os.environ.pop("GIT_USERNAME", None)
    os.environ.pop("GIT_PASSWORD", None)
    if not exito:
        print_color("Error al subir el código a GitHub (rama main).", "red")
        return False
    print_color("✅ Código subido a GitHub (rama main)", "green")
    
    print_color("\n✅ Código subido a GitHub exitosamente!", "green")
    print_color(f"\nRepositorio: https://github.com/{usuario}/{nombre_repo}", "blue")
    
    return True

def configurar_streamlit_cloud():
    """Muestra instrucciones para configurar Streamlit Cloud"""
    print_color("\n=== CONFIGURAR STREAMLIT CLOUD ===\n", "blue")
    
    print_color("Para configurar Streamlit Cloud, sigue estos pasos:", "blue")
    print_color("1. Ve a https://streamlit.io/cloud", "blue")
    print_color("2. Inicia sesión con GitHub", "blue")
    print_color("3. Haz clic en 'New app'", "blue")
    print_color("4. Selecciona el repositorio 'cvprocessor-tec'", "blue")
    print_color("5. En 'Main file path', escribe 'app_dashboard.py'", "blue")
    print_color("6. Haz clic en 'Advanced settings'", "blue")
    print_color("7. En la sección 'Secrets', añade el contenido del archivo credentials_base64.txt", "blue")
    print_color("8. Haz clic en 'Deploy'", "blue")
    
    print_color("\n¡Listo! Tu aplicación estará disponible en Streamlit Cloud en unos minutos.", "green")
    
    return True

def main():
    """Función principal"""
    print_color("\n=== DESPLIEGUE EN LA NUBE - PROCESADOR DE CVS ===\n", "purple")
    print_color("Este script automatiza todo el proceso de despliegue en la nube.", "yellow")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app_dashboard.py"):
        print_color("❌ Error: Este script debe ejecutarse desde el directorio cvprocessor-tec-new", "red")
        print_color("   Por favor, ejecuta: cd /ruta/a/cvprocessor-tec-new", "yellow")
        return False
    
    # Paso 1: Preparar para la nube
    if not preparar_para_nube():
        return False
    
    # Paso 2: Subir a GitHub
    if not subir_a_github():
        return False
    
    # Paso 3: Configurar Streamlit Cloud
    if not configurar_streamlit_cloud():
        return False
    
    print_color("\n✅ Proceso de despliegue completado exitosamente!", "green")
    print_color("\nTu aplicación estará disponible en Streamlit Cloud en unos minutos.", "green")
    print_color("Visita https://streamlit.io/cloud para verificar el estado del despliegue.", "blue")
    
    return True

if __name__ == "__main__":
    try:
        main()
        print_color("\nPresiona Enter para salir...", "blue")
        input()
    except KeyboardInterrupt:
        print_color("\n\n⚠️ Operación cancelada por el usuario.", "yellow")
    except Exception as e:
        print_color(f"\n❌ Error inesperado: {e}", "red")
        print_color("\nPresiona Enter para salir...", "blue")
        input()
