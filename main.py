"""
Procesador de CVs - Punto de entrada principal
Este archivo se mantiene para compatibilidad con comandos existentes.
"""

import sys
import os
import subprocess

def main():
    """
    Función principal que redirige a run.py
    """
    print("NOTA: El comando 'python3 main.py' está obsoleto.")
    print("Se recomienda usar 'python3 run.py' en su lugar.")
    print("Redirigiendo a run.py...")
    
    # Obtener la ruta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    run_path = os.path.join(current_dir, "run.py")
    
    # Pasar los argumentos a run.py
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Ejecutar run.py con los mismos argumentos
    subprocess.run([sys.executable, run_path] + args)

if __name__ == "__main__":
    main()
