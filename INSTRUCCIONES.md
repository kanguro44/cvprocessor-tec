# Instrucciones Rápidas - Procesador de CVs

## Instalación

1. **Instalar Python 3.7 o superior** si no lo tienes instalado
   - Descarga desde [python.org](https://www.python.org/downloads/)

2. **Ejecutar el script de instalación**:
   ```
   python setup.py
   ```
   Este script instalará todas las dependencias necesarias.

3. **Verificar el archivo de credenciales**:
   - Asegúrate de tener el archivo `credentials.json` en la carpeta del proyecto
   - Este archivo es necesario para la integración con Google Drive y Google Sheets

## Ejecución

### Método 1: Usando el script de inicio rápido

Simplemente ejecuta:
```
python run.py
```

Este script abrirá automáticamente tu navegador con la aplicación.

### Método 2: Ejecución manual

```
streamlit run app.py
```

## Uso de la Aplicación

1. **Subir CVs**:
   - Arrastra y suelta archivos PDF o DOCX en el área de carga
   - O haz clic en "Browse files" para seleccionar archivos

2. **Procesar CVs**:
   - Haz clic en el botón "Procesar CVs"
   - Espera a que se complete el procesamiento (se mostrará una barra de progreso)

3. **Ver Resultados**:
   - Una vez completado el procesamiento, se mostrarán los resultados
   - Puedes descargar los resultados en formato Excel o PDF

## Solución de Problemas Comunes

- **Error "ModuleNotFoundError: No module named 'xlsxwriter'"**:
  ```
  pip install xlsxwriter
  ```

- **Error "ModuleNotFoundError: No module named 'streamlit'"**:
  ```
  pip install streamlit
  ```

- **Error al conectar con Google Drive**:
  - Verifica que el archivo `credentials.json` sea válido
  - Asegúrate de que las APIs de Google Drive y Google Sheets estén habilitadas

- **La aplicación se queda "colgada"**:
  - Verifica que todas las dependencias estén correctamente instaladas
  - Asegúrate de que la API de OpenAI esté funcionando (verifica la clave API)

## Contacto

Si tienes problemas o sugerencias, por favor contacta al equipo de desarrollo.
