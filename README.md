# Procesador de CVs

Una aplicación potente y fácil de usar para procesar CVs académicos, extraer información clave y generar reportes.

## Características

- Interfaz moderna y amigable
- Procesamiento de archivos PDF y DOCX
- Extracción de datos con IA
- Búsqueda de universidades en ranking QS
- Exportación a Excel y CSV
- Integración con Google Drive y Google Sheets
- Autenticación con contraseña

## Requisitos

- Python 3.8 o superior
- Dependencias listadas en `requirements.txt`

## Instalación Local

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/cvprocessor-tec.git
   cd cvprocessor-tec
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta la aplicación:
   ```bash
   python run.py
   ```

## Despliegue en Streamlit Community Cloud

Para desplegar esta aplicación en internet y hacerla accesible a través de una URL, sigue estos pasos:

### 1. Preparar el Repositorio en GitHub

1. Crea un nuevo repositorio en GitHub
2. Sube todo el código a ese repositorio:
   ```bash
   git init
   git add .
   git commit -m "Versión inicial"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/cvprocessor-tec.git
   git push -u origin main
   ```

### 2. Configurar Streamlit Community Cloud

1. Visita [Streamlit Community Cloud](https://streamlit.io/cloud) y regístrate con tu cuenta de GitHub
2. Haz clic en "New app"
3. Selecciona tu repositorio, rama (main) y archivo principal (app.py)
4. Configura las variables de entorno necesarias (si aplica)
5. Haz clic en "Deploy"

### 3. Configurar Autenticación

La aplicación ya incluye autenticación con contraseña. La contraseña predeterminada es `cvprocessor2025` y se puede cambiar en el archivo `.streamlit/secrets.toml`.

Para configurar la autenticación en Streamlit Cloud:

1. Ve a la configuración de tu aplicación en Streamlit Cloud
2. En la sección "Secrets", añade el contenido de tu archivo `.streamlit/secrets.toml`

### 4. Configurar Dominio Personalizado

Para usar tu dominio globaledjobs.com:

1. En la configuración de tu aplicación en Streamlit Cloud, ve a la sección "Custom domain"
2. Sigue las instrucciones para configurar un subdominio (ej. cvs.globaledjobs.com)
3. En tu proveedor de DNS, crea un registro CNAME que apunte a la URL proporcionada por Streamlit

## Estructura del Proyecto

- `app.py`: Punto de entrada principal
- `app_simple.py`: Interfaz de usuario moderna
- `procesar_drive_cvs.py`: Funciones principales para procesar CVs
- `run.py`: Script para ejecutar la aplicación
- `.streamlit/`: Configuración de Streamlit
  - `config.toml`: Configuración general
  - `secrets.toml`: Secretos y credenciales
- `requirements.txt`: Dependencias del proyecto
- `credentials.json`: Credenciales para Google Drive/Sheets

## Uso de la Aplicación

1. Accede a la aplicación a través de la URL
2. Ingresa la contraseña para autenticarte
3. Arrastra y suelta archivos PDF o DOCX
4. Haz clic en "Procesar CVs"
5. Espera a que se complete el procesamiento
6. Descarga los resultados en Excel o CSV

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir los cambios que te gustaría hacer.

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.
