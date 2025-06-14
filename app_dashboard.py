"""
Procesador de CVs - Versión con Dashboard
Una aplicación mejorada para procesar CVs académicos con análisis y visualización de datos
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
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from collections import Counter

# Importar funciones esenciales del procesador original
from procesar_drive_cvs import (
    extract_text_from_pdf, extract_text_from_docx,
    extract_basic_data_gpt, match_university_qs, get_qs_list_from_google_sheets,
    upload_file_to_drive, make_hyperlink, export_to_sheets, determine_knowledge_area,
    SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME, 
    QS_GOOGLE_SHEET_ID, QS_TAB_NAME, GOOGLE_DRIVE_FOLDER_ID, OUTPUT_CSV
)

# Configuración de la página
st.set_page_config(
    page_title="Procesador de CVs",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Estilos personalizados
def load_css():
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
        .dashboard-card {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .metric-card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
            text-align: center;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #2196F3;
        }
        .metric-label {
            font-size: 1rem;
            color: #616161;
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
        .filter-container {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f9f9f9;
            margin-bottom: 1rem;
        }
        .dark-mode {
            background-color: #121212;
            color: #e0e0e0;
        }
        .dark-mode .dashboard-card, .dark-mode .metric-card {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        .dark-mode .metric-value {
            color: #64b5f6;
        }
        .dark-mode .metric-label {
            color: #b0bec5;
        }
        .dark-mode .filter-container {
            background-color: #1e1e1e;
        }
        .dark-mode .upload-box {
            background-color: #1e1e1e;
            border-color: #424242;
        }
        .dark-mode .stProgress > div > div {
            background-color: #64b5f6;
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
        self.all_results = []  # Almacena todos los resultados históricos
    
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
                            "Area": "No encontrado",
                            "QS Rank": "No encontrado",
                            "Fecha de procesamiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        # Extraer datos básicos con GPT
                        self.progress = file_progress + (progress_per_file * 0.6)
                        self.add_log(f"Analizando datos de {filename} con IA...")
                        data = extract_basic_data_gpt(cv_text, filename)
                        
                        # Buscar universidad en ranking QS
                        self.progress = file_progress + (progress_per_file * 0.7)
                        if self.qs_list:
                            self.add_log(f"Buscando universidad en ranking QS...")
                            match_qs = match_university_qs(data.get("Universidad doctorado", ""), self.qs_list)
                            data["Universidad doctorado"] = match_qs["Universidad doctorado"]
                            data["QS Rank"] = match_qs["QS Rank"]
                        
                        # Determinar el área de conocimiento
                        self.progress = file_progress + (progress_per_file * 0.8)
                        self.add_log(f"Determinando área de conocimiento...")
                        area = determine_knowledge_area(cv_text, data.get("Subject", ""), data.get("Universidad doctorado", ""))
                        data["Area"] = area
                        
                        # Añadir fecha de procesamiento
                        data["Fecha de procesamiento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
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
                
                # Añadir a resultados históricos
                self.all_results.extend(self.results)
            
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
    
    def get_all_results(self):
        """Obtiene todos los resultados históricos"""
        return self.all_results

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
    elif file_type == "json":
        json_str = df.to_json(orient='records')
        b64 = base64.b64encode(json_str.encode()).decode()
        filename = f"resultados_cvs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Descargar JSON</a>'
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
    
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    if 'view' not in st.session_state:
        st.session_state.view = "upload"  # Opciones: upload, results, dashboard
    
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            "area": "Todas",
            "pais": "Todos",
            "universidad": "Todas",
            "qs_rank_min": "",
            "qs_rank_max": ""
        }

# Función para crear gráficos
def create_charts(df):
    """Crea gráficos para el dashboard"""
    charts = {}
    
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        return charts
    
    # Distribución por área
    if "Area" in df.columns:
        area_counts = df["Area"].value_counts().reset_index()
        area_counts.columns = ["Area", "Cantidad"]
        
        # Filtrar "No encontrado" para el gráfico
        area_counts = area_counts[area_counts["Area"] != "No encontrado"]
        
        if not area_counts.empty:
            charts["area_chart"] = px.pie(
                area_counts, 
                values="Cantidad", 
                names="Area", 
                title="Distribución por Área de Conocimiento",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
    
    # Distribución por país
    if "País de residencia o nacionalidad" in df.columns:
        pais_counts = df["País de residencia o nacionalidad"].value_counts().reset_index()
        pais_counts.columns = ["País", "Cantidad"]
        
        # Filtrar "No encontrado" para el gráfico
        pais_counts = pais_counts[pais_counts["País"] != "No encontrado"]
        
        # Mostrar solo los 10 países más comunes
        if len(pais_counts) > 10:
            otros_count = pais_counts.iloc[10:]["Cantidad"].sum()
            pais_counts = pais_counts.iloc[:10]
            pais_counts = pd.concat([pais_counts, pd.DataFrame([{"País": "Otros", "Cantidad": otros_count}])])
        
        if not pais_counts.empty:
            charts["pais_chart"] = px.bar(
                pais_counts, 
                x="País", 
                y="Cantidad", 
                title="Distribución por País",
                color="Cantidad",
                color_continuous_scale="Viridis"
            )
    
    # Distribución por ranking QS
    if "QS Rank" in df.columns:
        # Convertir a numérico donde sea posible
        df_qs = df.copy()
        df_qs["QS Rank Num"] = pd.to_numeric(df_qs["QS Rank"], errors="coerce")
        
        # Crear rangos de ranking
        bins = [0, 50, 100, 200, 500, 1000, float('inf')]
        labels = ["Top 50", "51-100", "101-200", "201-500", "501-1000", "1000+"]
        
        df_qs["QS Range"] = pd.cut(df_qs["QS Rank Num"], bins=bins, labels=labels)
        qs_counts = df_qs["QS Range"].value_counts().reset_index()
        qs_counts.columns = ["Rango QS", "Cantidad"]
        
        if not qs_counts.empty:
            charts["qs_chart"] = px.bar(
                qs_counts, 
                x="Rango QS", 
                y="Cantidad", 
                title="Distribución por Ranking QS",
                color="Rango QS",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
    
    # Tendencia temporal (si hay fecha de procesamiento)
    if "Fecha de procesamiento" in df.columns:
        df_time = df.copy()
        df_time["Fecha"] = pd.to_datetime(df_time["Fecha de procesamiento"]).dt.date
        time_counts = df_time.groupby("Fecha").size().reset_index()
        time_counts.columns = ["Fecha", "Cantidad"]
        
        if len(time_counts) > 1:
            charts["time_chart"] = px.line(
                time_counts, 
                x="Fecha", 
                y="Cantidad", 
                title="Tendencia de Procesamiento",
                markers=True
            )
    
    # Relación entre Área y Ranking QS
    if "Area" in df.columns and "QS Rank" in df.columns:
        df_area_qs = df.copy()
        df_area_qs["QS Rank Num"] = pd.to_numeric(df_area_qs["QS Rank"], errors="coerce")
        
        # Filtrar valores no encontrados
        df_area_qs = df_area_qs[(df_area_qs["Area"] != "No encontrado") & (~df_area_qs["QS Rank Num"].isna())]
        
        if not df_area_qs.empty:
            area_qs_avg = df_area_qs.groupby("Area")["QS Rank Num"].mean().reset_index()
            area_qs_avg.columns = ["Area", "Ranking QS Promedio"]
            
            charts["area_qs_chart"] = px.bar(
                area_qs_avg, 
                x="Area", 
                y="Ranking QS Promedio", 
                title="Ranking QS Promedio por Área",
                color="Area",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
    
    return charts

# Función para mostrar métricas
def show_metrics(df):
    """Muestra métricas clave en el dashboard"""
    # Verificar que el DataFrame no esté vacío
    if df.empty:
        st.info("No hay datos disponibles para mostrar métricas.")
        return
    
    # Crear fila de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    # Total de CVs procesados
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{len(df)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">CVs Procesados</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Número de países representados
    with col2:
        paises = df["País de residencia o nacionalidad"].unique()
        paises = [p for p in paises if p != "No encontrado"]
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{len(paises)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Países</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Número de universidades
    with col3:
        universidades = df["Universidad doctorado"].unique()
        universidades = [u for u in universidades if u != "No encontrado"]
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{len(universidades)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Universidades</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Porcentaje con LinkedIn
    with col4:
        linkedin_count = len(df[df["LinkedIn URL"] != "No encontrado"])
        linkedin_percent = int((linkedin_count / len(df)) * 100) if len(df) > 0 else 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{linkedin_percent}%</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Con LinkedIn</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Función para aplicar filtros
def apply_filters(df, filters):
    """Aplica filtros al DataFrame"""
    filtered_df = df.copy()
    
    # Filtrar por área
    if filters["area"] != "Todas":
        filtered_df = filtered_df[filtered_df["Area"] == filters["area"]]
    
    # Filtrar por país
    if filters["pais"] != "Todos":
        filtered_df = filtered_df[filtered_df["País de residencia o nacionalidad"] == filters["pais"]]
    
    # Filtrar por universidad
    if filters["universidad"] != "Todas":
        filtered_df = filtered_df[filtered_df["Universidad doctorado"] == filters["universidad"]]
    
    # Filtrar por rango QS
    if filters["qs_rank_min"] and filters["qs_rank_max"]:
        # Convertir a numérico donde sea posible
        filtered_df["QS Rank Num"] = pd.to_numeric(filtered_df["QS Rank"], errors="coerce")
        # Aplicar filtro de rango
        min_rank = int(filters["qs_rank_min"])
        max_rank = int(filters["qs_rank_max"])
        filtered_df = filtered_df[(filtered_df["QS Rank Num"] >= min_rank) & (filtered_df["QS Rank Num"] <= max_rank)]
    
    return filtered_df

# Función para mostrar filtros
def show_filters(df):
    """Muestra controles de filtro para el DataFrame"""
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.subheader("Filtros")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por área
        areas = ["Todas"] + sorted(df["Area"].unique().tolist())
        st.session_state.filters["area"] = st.selectbox("Área de conocimiento", areas, index=areas.index(st.session_state.filters["area"]) if st.session_state.filters["area"] in areas else 0)
        
        # Filtro por país
        paises = ["Todos"] + sorted([p for p in df["País de residencia o nacionalidad"].unique() if p != "No encontrado"])
        st.session_state.filters["pais"] = st.selectbox("País", paises, index=paises.index(st.session_state.filters["pais"]) if st.session_state.filters["pais"] in paises else 0)
    
    with col2:
        # Filtro por universidad
        universidades = ["Todas"] + sorted([u for u in df["Universidad doctorado"].unique() if u != "No encontrado"])
        st.session_state.filters["universidad"] = st.selectbox("Universidad", universidades, index=universidades.index(st.session_state.filters["universidad"]) if st.session_state.filters["universidad"] in universidades else 0)
        
        # Filtro por rango QS
        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.filters["qs_rank_min"] = st.text_input("QS Rank Min", value=st.session_state.filters["qs_rank_min"])
        with col_b:
            st.session_state.filters["qs_rank_max"] = st.text_input("QS Rank Max", value=st.session_state.filters["qs_rank_max"])
    
    st.markdown('</div>', unsafe_allow_html=True)

# Función para mostrar la vista de carga
def show_upload_view():
    """Muestra la vista de carga de archivos"""
    processor = st.session_state.processor
    status = processor.get_status()
    
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
                    st.rerun()
        
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
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Forzar actualización cada 2 segundos
        time.sleep(2)
        st.rerun()

# Función para mostrar la vista de resultados
def show_results_view():
    """Muestra la vista de resultados"""
    processor = st.session_state.processor
    
    if processor.results:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.subheader(f"Procesamiento completado: {len(processor.results)} archivos procesados")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Crear DataFrame
        df = pd.DataFrame(processor.results)
        
        # Mostrar filtros
        show_filters(df)
        
        # Aplicar filtros
        filtered_df = apply_filters(df, st.session_state.filters)
        
        # Mostrar tabla de resultados
        st.dataframe(filtered_df, use_container_width=True)
        
        # Botones para descargar reportes
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Descargar Excel", key="excel", use_container_width=True):
                st.markdown(get_download_link(filtered_df, "excel"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Descargar CSV", key="csv", use_container_width=True):
                st.markdown(get_download_link(filtered_df, "csv"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Descargar JSON", key="json", use_container_width=True):
                st.markdown(get_download_link(filtered_df, "json"), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="download-button">', unsafe_allow_html=True)
            if st.button("Ver Dashboard", key="dashboard", use_container_width=True):
                st.session_state.view = "dashboard"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No hay resultados disponibles. Procesa algunos CVs primero.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Volver a la pantalla de carga", key="back_to_upload", use_container_width=True):
                st.session_state.view = "upload"
                st.rerun()

# Función para mostrar la vista de dashboard
def show_dashboard_view():
    """Muestra la vista de dashboard con gráficos y métricas"""
    processor = st.session_state.processor
    
    # Verificar si hay resultados
    if not processor.results:
        st.info("No hay datos disponibles para el dashboard. Procesa algunos CVs primero.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Volver a la pantalla de carga", key="back_to_upload", use_container_width=True):
                st.session_state.view = "upload"
                st.rerun()
        return
    
    # Crear DataFrame
    df = pd.DataFrame(processor.results)
    
    # Mostrar filtros
    show_filters(df)
    
    # Aplicar filtros
    filtered_df = apply_filters(df, st.session_state.filters)
    
    # Mostrar métricas
    show_metrics(filtered_df)
    
    # Crear gráficos
    charts = create_charts(filtered_df)
    
    # Mostrar gráficos
    if charts:
        col1, col2 = st.columns(2)
        
        # Distribución por área
        if "area_chart" in charts:
            with col1:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.plotly_chart(charts["area_chart"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Distribución por país
        if "pais_chart" in charts:
            with col2:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.plotly_chart(charts["pais_chart"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        
        # Distribución por ranking QS
        if "qs_chart" in charts:
            with col3:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.plotly_chart(charts["qs_chart"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Relación entre Área y Ranking QS
        if "area_qs_chart" in charts:
            with col4:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.plotly_chart(charts["area_qs_chart"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Tendencia temporal
        if "time_chart" in charts:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.plotly_chart(charts["time_chart"], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No hay suficientes datos para generar gráficos con los filtros actuales.")
    
    # Botones de navegación
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("Volver a Resultados", key="back_to_results", use_container_width=True):
            st.session_state.view = "results"
            st.rerun()
    
    with col3:
        if st.button("Exportar Dashboard (PDF)", key="export_dashboard", use_container_width=True):
            st.info("Funcionalidad de exportación a PDF en desarrollo.")

# Función principal
def main():
    """Función principal de la aplicación"""
    # Inicializar estado
    init_session_state()
    
    # Cargar estilos CSS
    load_css()
    
    # Aplicar modo oscuro si está activado
    if st.session_state.dark_mode:
        st.markdown('<div class="dark-mode">', unsafe_allow_html=True)
    
    # Verificar autenticación
    if not check_password():
        st.stop()  # No continuar si la contraseña es incorrecta
    
    # Barra lateral
    with st.sidebar:
        st.image("https://www.globaledjobs.com/wp-content/uploads/2023/06/cropped-logo-globaledjobs-1.png", width=150)
        st.title("Procesador de CVs")
        
        # Navegación
        st.subheader("Navegación")
        if st.button("📤 Cargar CVs", use_container_width=True):
            st.session_state.view = "upload"
            st.rerun()
        
        if st.button("📋 Ver Resultados", use_container_width=True):
            st.session_state.view = "results"
            st.rerun()
        
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.view = "dashboard"
            st.rerun()
        
        # Configuración
        st.subheader("Configuración")
        dark_mode = st.checkbox("Modo Oscuro", value=st.session_state.dark_mode)
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()
        
        # Información
        st.subheader("Información")
        st.info("Versión 2.0.0")
        st.info("Desarrollado por GlobalEdJobs")
    
    # Título de la aplicación
    st.markdown('<div class="title-box"><h1>Procesador de CVs</h1></div>', unsafe_allow_html=True)
    
    # Mostrar la vista correspondiente
    if st.session_state.view == "upload":
        show_upload_view()
    elif st.session_state.view == "results":
        show_results_view()
    elif st.session_state.view == "dashboard":
        show_dashboard_view()
    
    # Mostrar logs en un área colapsable
    processor = st.session_state.processor
    status = processor.get_status()
    
    if status["log_messages"]:
        with st.expander("Registro de procesamiento", expanded=False):
            for msg in status["log_messages"][-15:]:  # Mostrar solo los últimos 15 mensajes
                st.text(msg)
    
    # Cerrar div de modo oscuro si está activado
    if st.session_state.dark_mode:
        st.markdown('</div>', unsafe_allow_html=True)

# Ejecutar la aplicación
if __name__ == "__main__":
    main()
