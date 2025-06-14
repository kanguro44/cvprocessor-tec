# Despliegue en la Nube - Procesador de CVs

Esta guía explica cómo desplegar la aplicación en Streamlit Cloud para que esté disponible en línea, similar a la versión anterior: https://cvproceappr-tec-xhuxlz3kjaey53qmdmuy8g.streamlit.app/

## Requisitos Previos

- Una cuenta en [Streamlit Cloud](https://streamlit.io/cloud)
- Una cuenta en [GitHub](https://github.com)
- Las credenciales necesarias (Google Cloud, OpenAI)

## Pasos para Desplegar en Streamlit Cloud

### Paso 1: Preparar el Repositorio

1. Sube el código a un repositorio de GitHub:
   - Crea un nuevo repositorio en GitHub
   - Sube todos los archivos del proyecto (excepto los archivos sensibles)

2. Asegúrate de que el archivo `.gitignore` excluya archivos sensibles:
   - `credentials.json`
   - `.streamlit/secrets.toml`
   - Archivos de CVs y datos personales

### Paso 2: Configurar Streamlit Cloud

1. Inicia sesión en [Streamlit Cloud](https://streamlit.io/cloud)

2. Haz clic en "New app"

3. Conecta tu repositorio de GitHub:
   - Selecciona el repositorio donde subiste el código
   - Selecciona la rama principal (normalmente `main`)
   - En "Main file path", ingresa `app_dashboard.py`

4. Configura los secretos:
   - Haz clic en "Advanced settings"
   - En la sección "Secrets", añade el contenido de tu archivo `secrets.toml`
   - También puedes añadir el contenido de `credentials.json` como un secreto JSON

5. Haz clic en "Deploy"

### Paso 3: Verificar el Despliegue

1. Espera a que Streamlit Cloud termine de desplegar la aplicación

2. Una vez desplegada, se te proporcionará una URL para acceder a la aplicación

3. Verifica que la aplicación funcione correctamente:
   - Prueba la autenticación
   - Prueba la carga y procesamiento de CVs
   - Verifica que se pueda acceder a Google Drive y Sheets

## Configuración de Secretos

Para que la aplicación funcione correctamente en la nube, necesitas configurar los siguientes secretos en Streamlit Cloud:

### Secretos de OpenAI

```toml
openai_api_key = "sk-tu-clave-api-openai"
```

### Secretos de Google Cloud

Puedes añadir las credenciales de Google Cloud de dos formas:

1. Como un objeto JSON:
```toml
[gcp_service_account]
type = "service_account"
project_id = "tu-proyecto-id"
private_key_id = "tu-private-key-id"
private_key = "tu-private-key"
client_email = "tu-client-email@tu-proyecto.iam.gserviceaccount.com"
client_id = "tu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/tu-client-email%40tu-proyecto.iam.gserviceaccount.com"
```

2. O como un string codificado en base64:
```toml
gcp_credentials = "tu-json-credentials-codificado-en-base64"
```

### Contraseña de Acceso

```toml
password = "tu-contraseña-de-acceso"
```

## Notas Importantes

- **Seguridad**: Nunca subas archivos de credenciales directamente a GitHub
- **Actualizaciones**: Para actualizar la aplicación, simplemente actualiza el código en GitHub
- **Recursos**: Streamlit Cloud ofrece recursos limitados en su plan gratuito
- **Dominio Personalizado**: Si necesitas un dominio personalizado, considera el plan de pago de Streamlit Cloud

## Solución de Problemas

### Error: "No se pueden cargar las credenciales"

Verifica que hayas configurado correctamente los secretos en Streamlit Cloud.

### Error: "No se puede acceder a Google Drive"

Asegúrate de que las credenciales de Google Cloud tengan los permisos necesarios para acceder a Drive y Sheets.

### Error: "La aplicación se cierra inesperadamente"

Revisa los logs en Streamlit Cloud para identificar el problema.
