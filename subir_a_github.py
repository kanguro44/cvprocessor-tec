#!/usr/bin/env python3
"""
Script para subir el código a GitHub y configurar Streamlit Cloud
Este script automatiza el proceso de subir el código a GitHub
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

def verificar_git():
    """Verifica si Git está instalado"""
    print_color("Verificando si Git está instalado...", "blue")
    exito, _ = ejecutar_comando("git --version", mostrar_salida=False)
    if not exito:
        print_color("Git no está instalado. Por favor, instala Git antes de continuar.", "red")
        return False
    print_color("✅ Git está instalado", "green")
    return True

def inicializar_repositorio():
    """Inicializa un repositorio Git"""
    print_color("Inicializando repositorio Git...", "blue")
    
    # Verificar si ya existe un repositorio Git
    if os.path.exists(".git"):
        print_color("Ya existe un repositorio Git en este directorio.", "yellow")
        return True
    
    # Inicializar repositorio
    exito, _ = ejecutar_comando("git init")
    if not exito:
        print_color("Error al inicializar el repositorio Git.", "red")
        return False
    
    print_color("✅ Repositorio Git inicializado", "green")
    return True

def configurar_usuario_git(usuario):
    """Configura el usuario de Git"""
    print_color(f"Configurando usuario de Git: {usuario}...", "blue")
    
    # Configurar usuario
    exito, _ = ejecutar_comando(f'git config user.name "{usuario}"')
    if not exito:
        print_color("Error al configurar el nombre de usuario de Git.", "red")
        return False
    
    # Configurar email (usando un email genérico basado en el usuario)
    exito, _ = ejecutar_comando(f'git config user.email "{usuario}@github.com"')
    if not exito:
        print_color("Error al configurar el email de Git.", "red")
        return False
    
    print_color("✅ Usuario de Git configurado", "green")
    return True

def agregar_archivos():
    """Agrega archivos al repositorio"""
    print_color("Agregando archivos al repositorio...", "blue")
    
    # Agregar todos los archivos
    exito, _ = ejecutar_comando("git add .")
    if not exito:
        print_color("Error al agregar archivos al repositorio.", "red")
        return False
    
    print_color("✅ Archivos agregados al repositorio", "green")
    return True

def crear_commit():
    """Crea un commit"""
    print_color("Creando commit...", "blue")
    
    # Crear commit
    exito, _ = ejecutar_comando('git commit -m "Initial commit - Procesador de CVs"')
    if not exito:
        print_color("Error al crear el commit.", "red")
        return False
    
    print_color("✅ Commit creado", "green")
    return True

def crear_repositorio_github(usuario, token, nombre_repo="cvprocessor-tec", privado=True):
    """Crea un repositorio en GitHub"""
    print_color(f"Creando repositorio en GitHub: {nombre_repo}...", "blue")
    
    # Verificar si el repositorio ya existe
    print_color("Verificando si el repositorio ya existe...", "blue")
    comando_verificar = f'curl -s -o /dev/null -w "%{{http_code}}" -u "{usuario}:{token}" https://api.github.com/repos/{usuario}/{nombre_repo}'
    exito, salida = ejecutar_comando(comando_verificar, mostrar_salida=False)
    
    if exito and salida.strip() == "200":
        print_color(f"El repositorio {nombre_repo} ya existe en GitHub.", "yellow")
        return True
    
    # Crear repositorio
    privado_str = "true" if privado else "false"
    comando_crear = f'curl -u "{usuario}:{token}" https://api.github.com/user/repos -d \'{{"name":"{nombre_repo}","private":{privado_str}}}\''
    exito, _ = ejecutar_comando(comando_crear)
    
    if not exito:
        print_color(f"Error al crear el repositorio {nombre_repo} en GitHub.", "red")
        return False
    
    print_color(f"✅ Repositorio {nombre_repo} creado en GitHub", "green")
    return True

def agregar_remoto(usuario, nombre_repo="cvprocessor-tec"):
    """Agrega un remoto al repositorio"""
    print_color("Agregando remoto al repositorio...", "blue")
    
    # Verificar si ya existe un remoto llamado origin
    exito, salida = ejecutar_comando("git remote -v", mostrar_salida=False)
    if exito and "origin" in salida:
        print_color("Ya existe un remoto llamado origin. Eliminándolo...", "yellow")
        ejecutar_comando("git remote remove origin")
    
    # Agregar remoto
    exito, _ = ejecutar_comando(f"git remote add origin https://github.com/{usuario}/{nombre_repo}.git")
    if not exito:
        print_color("Error al agregar el remoto al repositorio.", "red")
        return False
    
    print_color("✅ Remoto agregado al repositorio", "green")
    return True

def subir_a_github(usuario, token, nombre_rama="main"):
    """Sube el código a GitHub"""
    print_color(f"Subiendo código a GitHub (rama {nombre_rama})...", "blue")
    
    # Configurar credenciales temporales
    os.environ["GIT_ASKPASS"] = "echo"
    os.environ["GIT_USERNAME"] = usuario
    os.environ["GIT_PASSWORD"] = token
    
    # Subir código
    comando_push = f"git push -u origin {nombre_rama}"
    exito, _ = ejecutar_comando(comando_push)
    
    # Limpiar credenciales
    os.environ.pop("GIT_ASKPASS", None)
    os.environ.pop("GIT_USERNAME", None)
    os.environ.pop("GIT_PASSWORD", None)
    
    if not exito:
        print_color(f"Error al subir el código a GitHub (rama {nombre_rama}).", "red")
        return False
    
    print_color(f"✅ Código subido a GitHub (rama {nombre_rama})", "green")
    return True

def main():
    """Función principal"""
    print_color("\n=== SUBIR CÓDIGO A GITHUB ===\n", "blue")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app_dashboard.py"):
        print_color("❌ Error: Este script debe ejecutarse desde el directorio cvprocessor-tec-new", "red")
        print_color("   Por favor, ejecuta: cd /ruta/a/cvprocessor-tec-new", "yellow")
        return False
    
    # Verificar Git
    if not verificar_git():
        return False
    
    # Solicitar credenciales
    usuario = "kanguro44"  # Reemplaza con tu usuario de GitHub
    token = input("Ingresa tu token de GitHub (o contraseña): ")
    nombre_repo = "cvprocessor-tec"
    
    # Inicializar repositorio
    if not inicializar_repositorio():
        return False
    
    # Configurar usuario
    if not configurar_usuario_git(usuario):
        return False
    
    # Agregar archivos
    if not agregar_archivos():
        return False
    
    # Crear commit
    if not crear_commit():
        return False
    
    # Crear repositorio en GitHub
    if not crear_repositorio_github(usuario, token, nombre_repo, privado=True):
        return False
    
    # Agregar remoto
    if not agregar_remoto(usuario, nombre_repo):
        return False
    
    # Subir a GitHub
    if not subir_a_github(usuario, token):
        return False
    
    print_color("\n✅ Código subido a GitHub exitosamente!", "green")
    print_color(f"\nRepositorio: https://github.com/{usuario}/{nombre_repo}", "blue")
    print_color("\nAhora puedes configurar Streamlit Cloud:", "blue")
    print_color("1. Ve a https://streamlit.io/cloud", "blue")
    print_color("2. Inicia sesión con GitHub", "blue")
    print_color("3. Haz clic en 'New app'", "blue")
    print_color(f"4. Selecciona el repositorio {nombre_repo}", "blue")
    print_color("5. En 'Main file path', escribe 'app_dashboard.py'", "blue")
    print_color("6. Haz clic en 'Advanced settings'", "blue")
    print_color("7. En la sección 'Secrets', añade el contenido del archivo credentials_base64.txt", "blue")
    print_color("8. Haz clic en 'Deploy'", "blue")
    
    print_color("\n¡Listo! Tu aplicación estará disponible en Streamlit Cloud en unos minutos.", "green")
    
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
