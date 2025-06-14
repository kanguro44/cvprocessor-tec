"""
Procesador de CVs - Versión Simplificada
Una aplicación minimalista y potente para procesar CVs académicos
"""

import streamlit as st
import pandas as pd
import os
import tempfile
import time
from datetime import datetime
import threading
import queue
import base64
import io

# Importar funciones esenciales del procesador original
from procesar_drive_cvs import (
    extract_text_from_pdf, extract_text_from_docx,
    extract_basic_data_gpt, match_university_qs, get_qs_list_from_google_sheets,
    upload_file_to_drive, make_hyperlink, export_to_sheets,
    SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME, 
    QS_GOOGLE_SHEET_ID, QS_TAB_NAME, GOOGLE_DRIVE_FOLDER_ID, OUTPUT_CSV
)

# Configuración de la página
st.set_page_config(
    page_title="Procesador de CVs",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Función de autenticación
def check_password():
    """Retorna `True` si el usuario tiene la contraseña correcta."""
    def password_entered():
        # Verificar si la clave "password" existe en los secretos
        if "password" not in st.secrets:
            st.error("Error: La clave 'password' no está configurada en los secretos de Streamlit.")
            st.info("Administrador: Verifica la configuración de secretos en Streamlit Cloud.")
            st.code("""
# Ejemplo de configuración de secretos:
password = "cvprocessor2025"
            """)
            st.session_state["password_correct"] = False
            return
            
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardar la contraseña
        else:
            st.session_state["password_correct"] = False

    # Mostrar formulario de login
    st.markdown('<div style="text-align: center; padding: 2rem; max-width: 400px; margin: 0 auto;">', unsafe_allow_html=True)
    st.image("https://www.globaledjobs.com/wp-content/uploads/2023/06/cropped-logo-globaledjobs-1.png", width=200)
    st.markdown("### Procesador de CVs")
    st.markdown("Ingresa la contraseña para acceder a la aplicación")
    
    if "password_correct" not in st.session_state:
        # Primera ejecución, mostrar input para contraseña
        st.text_input(
            "Contraseña", type="password", on_change=password_entered, key="password"
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta
        st.text_input(
            "Contraseña", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Contraseña incorrecta")
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    else:
        # Contraseña correcta
        return True

# Verificar autenticación
if not check_password():
    st.stop()  # No continuar si la contraseña es incorrecta

# Estilos personalizados
st.markdown("""
<style>
    .main {
        background-color: #f5f5f5;
    }
    .stProgress > div > div {
        background-color: #4CAF50;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e8f5e9;
        border-left: 0.5rem solid #4CAF50;
        margin-bottom: 1rem;
    }
    .processing-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e3f2fd;
        border-left: 0.5rem solid #2196F3;
        margin-bottom: 1rem;
    }
    .upload-box {
        padding: 2rem;
        border-radius: 0.5rem;
        background-color: #fafafa;
        border: 2px dashed #9e9e9e;
        margin-bottom: 1rem;
        text-align: center;
    }
    .title-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #37474f;
        color: white;
        margin-bottom: 1rem;
        text-align: center;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.3rem;
    }
    .cancel-button>button {
        background-color: #f44336;
    }
    .download-button>button {
        background-color: #2196F3;
    }
</style>
""", unsafe_allow_html=True)

# Clase para procesar CVs
class CVProcessor:
    def __init__(self):
        self.queue = queue.Queue()
        self.results = []
        self.processing = False
        self.progress = 0
        self.current_file = ""
        self.log_messages = []
        self.success_count = 0
        self.error_count = 0
        self.stop_requested = False
        self.qs_list = []
    
    def add_log(self, message):
        """Añade un mensaje al registro de logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append(f"[{timestamp}] {message}")
        print(f"[{timestamp}] {message}")  # También imprimir en consola
    
    def process_files(self, files):
        """Procesa una lista de archivos"""
        if self.processing:
            return False
        
        # Iniciar procesamiento en un hilo separado
        self.processing = True
        self.progress = 0
        self.current_file = ""
        self.results = []
        self.success_count = 0
        self.error_count = 0
        self.stop_requested = False
        
        thread = threading.Thread(target=self._process_thread, args=(files,))
        thread.daemon = True
        thread.start()
        
        return True
    
    def _process_thread(self, files):
        """Función que se ejecuta en el hilo de procesamiento"""
        try:
            # Cargar lista QS
            self.progress = 5
            self.add_log("Cargando lista de universidades QS...")
            try:
                self.qs_list = get_qs_list_from_google_sheets(QS_GOOGLE_SHEET_ID, QS_TAB_NAME, SERVICE_ACCOUNT_FILE)
                self.add_log(f"Universidades QS cargadas: {len(self.qs_list)}")
            except Exception as e:
                self.add_log(f"Error al cargar lista QS: {str(e)}. Continuando sin ranking QS.")
                self.qs_list = []
            
            # Procesar archivos
            results = []
            total_files = len(files)
            
            # Calcular progreso por archivo (reservamos 10% para inicio y 10% para final)
            progress_per_file = 80 / max(total_files, 1)
            
            for i, file in enumerate(files):
                if self.stop_requested:
                    self.add_log("Procesamiento cancelado por el usuario")
                    break
                
                # Actualizar progreso
                file_progress = 10 + (i * progress_per_file)
                self.progress = file_progress
                
                # Obtener nombre del archivo
                filename = os.path.basename(file)
                self.current_file = filename
                self.add_log(f"Procesando {filename}...")
                
                try:
                    # Extraer texto del CV
                    self.progress = file_progress + (progress_per_file * 0.3)
                    cv_text = ""
                    if file.lower().endswith('.pdf'):
                        cv_text = extract_text_from_pdf(file)
                    elif file.lower().endswith('.docx'):
                        cv_text = extract_text_from_docx(file)
                    else:
                        self.add_log(f"Formato de archivo no soportado: {file}")
                        self.error_count += 1
                        continue
                    
                    # Si no se pudo extraer texto, usar el nombre del archivo
                    if not cv_text.strip():
                        self.add_log(f"Advertencia: No se pudo extraer texto de {filename}. Usando nombre como fallback.")
                        name_from_file = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
                        data = {
                            "Nombre completo": name_from_file,
                            "Correo electrónico profesional": "No encontrado",
                            "LinkedIn URL": "No encontrado",
                            "Teléfono": "No encontrado",
                            "País de residencia o nacionalidad": "No encontrado",
                            "Universidad doctorado": "No encontrado",
                            "Subject": "No encontrado",
                            "QS Rank": "No encontrado"
                        }
                    else:
                        # Extraer datos básicos con GPT
                        self.progress = file_progress + (progress_per_file * 0.6)
                        self.add_log(f"Analizando datos de {filename} con IA...")
                        data = extract_basic_data_gpt(cv_text, filename)
                        
                        # Buscar universidad en ranking QS
                        self.progress = file_progress + (progress_per_file * 0.8)
                        if self.qs_list:
                            self.add_log(f"Buscando universidad en ranking QS...")
                            match_qs = match_university_qs(data.get("Universidad doctorado", ""), self.qs_list)
                            data["Universidad doctorado"] = match_qs["Universidad doctorado"]
                            data["QS Rank"] = match_qs["QS Rank"]
                    
                    # Asegurar que no hay valores vacíos
                    for k in data:
                        if not data[k]:
                            data[k] = "No encontrado"
                    
                    # Subir CV a Google Drive
                    self.progress = file_progress + (progress_per_file * 0.9)
                    try:
                        self.add_log(f"Subiendo {filename} a Google Drive...")
                        drive_url = upload_file_to_drive(file, filename, GOOGLE_DRIVE_FOLDER_ID, SERVICE_ACCOUNT_FILE)
                        data["CV Link"] = drive_url
                    except Exception as e:
                        self.add_log(f"Error al subir a Drive: {str(e)}. Continuando sin link.")
                        data["CV Link"] = "Error al subir"
                    
                    data["CV FileName"] = filename
                    
                    # Añadir a resultados
                    results.append(data)
                    self.success_count += 1
                    self.add_log(f"Procesamiento exitoso para {filename}")
                    
                except Exception as e:
                    self.add_log(f"Error al procesar {filename}: {str(e)}")
                    self.error_count += 1
                
                # Actualizar progreso al final del procesamiento de este archivo
                self.progress = 10 + ((i + 1) * progress_per_file)
            
            # Procesar resultados
            if results:
                self.progress = 90
                self.add_log(f"Procesados {len(results)} CVs. Preparando resultados...")
                
                # Crear DataFrame
                df = pd.DataFrame(results)
                
                # Hipervínculo: crea columna combinada
                df["Nombre completo"] = df.apply(lambda row: make_hyperlink(row["Nombre completo"], row["CV Link"]), axis=1)
                
                # Deduplicar por correo electrónico
                if len(df) > 1:
                    self.add_log("Eliminando duplicados...")
                    # Separar los que tienen email de los que no
                    df_con_email = df[df["Correo electrónico profesional"] != "No encontrado"].copy()
                    df_sin_email = df[df["Correo electrónico profesional"] == "No encontrado"].copy()
                    
                    # Deduplicar los que tienen email
                    if len(df_con_email) > 0:
                        df_con_email = df_con_email.drop_duplicates(subset=["Correo electrónico profesional"], keep='first')
                    
                    # Deduplicar los que no tienen email por nombre de archivo
                    if len(df_sin_email) > 0:
                        df_sin_email = df_sin_email.drop_duplicates(subset=["CV FileName"], keep='first')
                    
                    # Combinar ambos DataFrames
                    df = pd.concat([df_con_email, df_sin_email])
                
                # Guardar resultados
                self.progress = 95
                self.add_log("Guardando resultados...")
                
                # Guardar en CSV local
                try:
                    df.to_csv(OUTPUT_CSV, index=False)
                    self.add_log(f"Resultados guardados en {OUTPUT_CSV}")
                except Exception as e:
                    self.add_log(f"Error al guardar CSV: {str(e)}")
                
                # Exportar a Google Sheets
                try:
                    self.add_log("Exportando a Google Sheets...")
                    export_to_sheets(df, SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME)
                    self.add_log("Resultados exportados a Google Sheets")
                except Exception as e:
                    self.add_log(f"Error al exportar a Sheets: {str(e)}")
                
                # Guardar resultados en memoria
                self.results = df.to_dict('records')
            
            # Finalizar
            self.progress = 100
            self.add_log("Procesamiento completado")
            
        except Exception as e:
            self.add_log(f"Error en el procesamiento: {str(e)}")
            self.progress = 100
        
        finally:
            self.processing = False
    
    def stop_processing(self):
        """Detiene el procesamiento"""
        if self.processing:
            self.stop_requested = True
            return True
        return False
    
    def get_status(self):
        """Obtiene el estado actual del procesamiento"""
        return {
            "processing": self.processing,
            "progress": self.progress,
            "current_file": self.current_file,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "log_messages": self.log_messages.copy()
        }

# Función para generar enlace de descarga
def get_download_link(df, file_type="csv"):
    """Genera un enlace de descarga para un DataFrame"""
    if file_type == "csv":
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        filename = f"resultados_cvs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Descargar CSV</a>'
    elif file_type == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Resultados', index=False)
            # Dar formato a la hoja
            workbook = writer.book
            worksheet = writer.sheets['Resultados']
            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            # Aplicar formato a encabezados
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            # Ajustar ancho de columnas
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_width)
        
        b64 = base64.b64encode(output.getvalue()).decode()
        filename = f"resultados_cvs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Descargar Excel</a>'
    else:
        return ""
    
    return href

# Inicializar estado de la sesión
def init_session_state():
    """Inicializa el estado de la sesión"""
    if 'processor' not in st.session_state:
        st.session_state.processor = CVProcessor()
    
    if 'update_counter' not in st.session_state:
        st.session_state.update_counter = 0

# Función principal
def main():
    """Función principal de la aplicación"""
    # Inicializar estado
    init_session_state()
    
    # Título de la aplicación
    st.markdown('<div class="title-box"><h1>Procesador de CVs</h1></div>', unsafe_allow_html=True)
    
    # Obtener estado actual
    processor = st.session_state.processor
    status = processor.get_status()
    
    # Área de carga de archivos
    if not status["processing"]:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Arrastra y suelta archivos PDF o DOCX aquí",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.update_counter}"
        )
        
        if uploaded_files:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Procesar CVs", key=f"process_{st.session_state.update_counter}", use_container_width=True):
                    # Guardar archivos temporalmente
                    temp_dir = tempfile.mkdtemp()
                    temp_files = []
                    
                    for uploaded_file in uploaded_files:
                        # Crear ruta temporal
                        temp_file = os.path.join(temp_dir, uploaded_file.name)
                        
                        # Guardar archivo
                        with open(temp_file, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        temp_files.append(temp_file)
                    
                    # Iniciar procesamiento
                    processor.process_files(temp_files)
                    st.session_state.update_counter += 1
                    st.rerun()  # Usar st.rerun() en lugar de st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Mostrar progreso si está procesando
    if status["processing"]:
        st.markdown('<div class="processing-box">', unsafe_allow_html=True)
        st.subheader("Procesando archivos...")
        
        # Barra de progreso
        st.progress(status["progress"] / 100)
        
        # Información del archivo actual
        if status["current_file"]:
            st.write(f"Procesando: {status['current_file']}")
        
        # Botón para cancelar
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="cancel-button">', unsafe_allow_html=True)
            if st.button("Cancelar procesamiento", key="cancel", use_container_width=True):
                processor.stop_processing()
                st.session_state.update_counter += 1
                st.rerun()  # Usar st.rerun() en lugar de st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Forzar actualización cada 2 segundos
        time.sleep(2)
        st.rerun()  # Usar st.rerun() en lugar de st.experimental_rerun()
    
    # Mostrar resultados si ha terminado y hay resultados
    elif not status["processing"] and processor.results:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.subheader(f"Procesamiento completado: {status['success_count']} archivos procesados")
        
        if status["error_count"] > 0:
            st.warning(f"{status['error_count']} archivos tuvieron errores. Revisa el registro para más detalles.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Mostrar tabla de resultados
        df = pd.DataFrame(processor.results)
        st.dataframe(df, use_container_width=True)
        
        # Botones para descargar reportes
        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
        
        with col2:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Descargar Excel", key="excel", use_container_width=True):
                st.markdown(get_download_link(df, "excel"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Descargar CSV", key="csv", use_container_width=True):
                st.markdown(get_download_link(df, "csv"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Mostrar logs en un área colapsable
    if status["log_messages"]:
        with st.expander("Registro de procesamiento", expanded=False):
            for msg in status["log_messages"][-15:]:  # Mostrar solo los últimos 15 mensajes
                st.text(msg)

# Ejecutar la aplicación
if __name__ == "__main__":
    main()
