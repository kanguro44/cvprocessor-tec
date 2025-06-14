# Procesador de CVs

Aplicación para procesar CVs académicos con análisis y visualización de datos.

## Descripción

Esta aplicación permite:

- Cargar y procesar CVs en formato PDF o DOCX
- Extraer información relevante utilizando IA
- Buscar universidades en el ranking QS
- Determinar áreas de conocimiento
- Visualizar datos en un dashboard interactivo
- Exportar resultados a Google Sheets

## Despliegue

Esta aplicación está diseñada para ser desplegada en Streamlit Cloud.

### Requisitos

- Una cuenta en [Streamlit Cloud](https://streamlit.io/cloud)
- Una cuenta en [GitHub](https://github.com)
- Las credenciales necesarias (Google Cloud, OpenAI)

### Pasos para Desplegar

1. Sube este repositorio a GitHub
2. Conéctalo a Streamlit Cloud
3. Configura los secretos necesarios
4. ¡Listo!

Para instrucciones detalladas, consulta el archivo [README_NUBE.md](README_NUBE.md).

## Configuración

La aplicación requiere las siguientes credenciales:

- Clave de API de OpenAI
- Credenciales de Google Cloud (Service Account)
- Contraseña de acceso

Estas credenciales deben configurarse como secretos en Streamlit Cloud.

## Tecnologías Utilizadas

- Python
- Streamlit
- OpenAI
- Google Cloud (Drive, Sheets)
- Plotly
- Pandas

## Autor

Desarrollado por GlobalEdJobs
