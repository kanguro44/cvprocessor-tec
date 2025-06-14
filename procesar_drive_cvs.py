import os
import fitz  # PyMuPDF
import docx
import openai
import re
import json
import pandas as pd
import gspread
import unicodedata
from google.oauth2.service_account import Credentials
from difflib import get_close_matches

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# === Configura aquí tus variables ===
# La clave de API de OpenAI se carga desde .streamlit/secrets.toml
OPENAI_API_KEY = "sk-xxxx"  # Esta clave será reemplazada en tiempo de ejecución
# Intenta cargar la clave desde secrets.toml si está disponible
try:
    import streamlit as st
    if "openai_api_key" in st.secrets:
        OPENAI_API_KEY = st.secrets["openai_api_key"]
        print("Clave de API de OpenAI cargada desde secrets.toml")
except Exception as e:
    print(f"No se pudo cargar la clave de API de OpenAI desde secrets.toml: {e}")
    print("Usando clave de API de OpenAI predeterminada (esto puede no funcionar)")

SERVICE_ACCOUNT_FILE = "credentials.json"
SPREADSHEET_ID = "1ETFM0k1QM07Csk9mcJHy9ZnS0-WkHsrNZDxYVTWxRAA"
SHEET_NAME = "Hoja 1"
QS_GOOGLE_SHEET_ID = "117FMF8RBEzwSLxnqEp7LUg2jZ0iACob9E9mNtvu2Ku4"
QS_TAB_NAME = "QS 2025"
FOLDER_CVS = "BDCandidatos"  # Carpeta donde están los CV
OUTPUT_CSV = "resultados.csv"
GOOGLE_DRIVE_FOLDER_ID = "1cdASLNMmbJ2zyRzy4D9c_eY4yrQ_wns7"  # ID de la carpeta en Drive
GOOGLE_DRIVE_PROCESSED_FOLDER_ID = "1Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd"  # ID de la carpeta en Drive para CVs procesados

openai.api_key = OPENAI_API_KEY

def log(msg):
    print(f"[LOG] {msg}")

def get_qs_list_from_google_sheets(sheet_id, sheet_name, service_json):
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(service_json, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_values()
    qs_list = data[1:]
    return qs_list

def extract_text_from_pdf(path):
    try:
        text = ""
        with fitz.open(path) as doc:
            for page in doc:
                text += page.get_text()
        
        # Verificar si se extrajo texto
        if not text.strip():
            log(f"No se pudo extraer texto del PDF {os.path.basename(path)}, intentando método alternativo...")
            
            # Método alternativo: usar PyPDF2
            try:
                import PyPDF2
                with open(path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(reader.pages)):
                        text += reader.pages[page_num].extract_text() + "\n"
            except Exception as e2:
                log(f"Error con PyPDF2: {e2}")
                
                # Si PyPDF2 falla, intentar con pdfplumber
                try:
                    import pdfplumber
                    with pdfplumber.open(path) as pdf:
                        for page in pdf.pages:
                            text += page.extract_text() or ""
                except Exception as e3:
                    log(f"Error con pdfplumber: {e3}")
        
        log(f"Texto extraído de PDF {os.path.basename(path)} ({len(text)} caracteres)")
        return text
    except Exception as e:
        log(f"Error al leer el PDF '{path}': {e}")
        return ""

def extract_text_from_docx(path):
    try:
        docf = docx.Document(path)
        text = "\n".join([p.text for p in docf.paragraphs])
        log(f"Texto extraído de DOCX {os.path.basename(path)} ({len(text)} caracteres)")
        return text
    except Exception as e:
        log(f"Error al leer el DOCX '{path}': {e}")
        return ""

def clean_phone(phone):
    # Eliminar caracteres no numéricos excepto el signo +
    cleaned = re.sub(r'[^\d\+]', '', phone)
    
    # Verificar si parece un rango de años (como 20072015)
    if re.match(r'^(19|20)\d{2}(19|20)\d{2}$', cleaned):
        return "No encontrado"
    
    # Verificar si es solo un año (como 2007)
    if re.match(r'^(19|20)\d{2}$', cleaned):
        return "No encontrado"
    
    return cleaned

def normalize_str(s):
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode('ascii')

def get_aliases_for_univ(univ):
    d = {
        "tecnologico de monterrey": ["itesm", "tec de monterrey", "monterrey tech", "instituto tecnologico y de estudios superiores de monterrey"],
        "universidad nacional autonoma de mexico": ["unam", "national autonomous university of mexico"],
        "universidad de buenos aires": ["uba", "university of buenos aires"],
        "pontificia universidad catolica de chile": ["puc", "catolica de chile"],
        "universitat de barcelona": ["ub", "university of barcelona"],
        "universidad de los andes": ["uniandes", "univ de los andes"],
    }
    n = normalize_str(univ)
    for key, aliases in d.items():
        if n == key or n in aliases:
            return [key] + aliases
    return [n]

def fallback_regex_email(text):
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else "No encontrado"

def fallback_regex_phone(text):
    # Buscar números de teléfono cerca de palabras clave
    phone_keywords = [
        r"(?i)tel[eé]fono\s*(?:m[oó]vil)?[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)phone\s*(?:number)?[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)contact(?:o)?[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)m[oó]vil[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)celular[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)tel[\s:]*(\+?[\d\s\-\(\)\.]{8,})",
        r"(?i)phone[\s:]*(\+?[\d\s\-\(\)\.]{8,})"
    ]
    
    # Buscar números de teléfono cerca de palabras clave
    for pattern in phone_keywords:
        match = re.search(pattern, text)
        if match:
            phone = clean_phone(match.group(1))
            # Verificar que sea un número de teléfono válido (al menos 8 dígitos)
            if len(re.sub(r'\D', '', phone)) >= 8:
                return phone
    
    # Si no se encuentra con palabras clave, buscar patrones de teléfono comunes
    # pero evitando rangos de años (que suelen tener 4 dígitos - 4 dígitos)
    phone_patterns = [
        # Número internacional con código de país
        r"(?<!\d)(\+\d{1,3}[\s\-]?\d{1,3}[\s\-]?\d{3,}[\s\-]?\d{3,}(?!\d))",
        # Número con paréntesis para código de área
        r"(?<!\d)(\(\d{2,5}\)[\s\-]?\d{3,}[\s\-]?\d{3,}(?!\d))",
        # Número con más de 8 dígitos (para evitar años)
        r"(?<!\d)(\d{3,}[\s\-]?\d{3,}[\s\-]?\d{3,}(?!\d))"
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = clean_phone(match.group(1))
            # Verificar que sea un número de teléfono válido (al menos 8 dígitos)
            if len(re.sub(r'\D', '', phone)) >= 8:
                return phone
    
    # Si no se encuentra ningún patrón, devolver "No encontrado"
    return "No encontrado"

def fallback_regex_linkedin(text):
    match = re.search(r"https?://(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", text)
    return match.group(0) if match else "No encontrado"

def fallback_regex_name(text):
    """Intenta extraer el nombre del CV usando patrones comunes"""
    # Patrones comunes para nombres en CVs
    patterns = [
        r"(?i)curriculum\s+vitae\s+(?:de\s+)?([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})",
        r"(?i)(?:nombre|name)[:]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})",
        r"(?i)^([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})$",  # Línea que solo contiene un nombre
        r"(?i)(?:cv|resume|curriculum)\s+(?:of|de)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})",
        r"(?i)(?:dr\.|ing\.|lic\.|mtro\.)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{2,50})"
    ]
    
    # Buscar en las primeras líneas del texto
    first_lines = "\n".join(text.split("\n")[:20])
    
    for pattern in patterns:
        match = re.search(pattern, first_lines)
        if match:
            name = match.group(1).strip()
            # Limpiar el nombre
            name = re.sub(r'\s+', ' ', name)  # Eliminar espacios múltiples
            name = re.sub(r'[^\w\sáéíóúÁÉÍÓÚñÑ]', '', name)  # Eliminar caracteres especiales
            if len(name) > 3:  # Asegurarse de que el nombre tenga al menos 3 caracteres
                return name
    
    # Si no se encuentra un nombre, extraer el nombre del archivo
    return "No encontrado"

def extract_basic_data_gpt(cv_text, filename=""):
    prompt = """
Extract ONLY the following fields from this academic CV (English or Spanish).
If a field is not found, write 'No encontrado'.
Pay special attention to extracting the full name correctly, it's the most important field.
Look for the name at the beginning of the CV, in headers, or in signature sections.

For the phone number, look for patterns like:
- +52 55 1234 5678
- (123) 456-7890
- 123-456-7890
- 123.456.7890
DO NOT confuse year ranges (like 2007-2015) with phone numbers.
Look for phone numbers near keywords like "teléfono", "phone", "contact", "móvil", "celular".

Return a valid JSON in this format:
{
    "Nombre completo": "...",
    "Correo electrónico profesional": "...",
    "LinkedIn URL": "...",
    "Teléfono": "...",
    "País de residencia o nacionalidad": "...",
    "Universidad doctorado": "...",
    "Subject": "..."
}

Examples:
Nombre completo: Juan Pérez Gómez / María Fernanda Díaz / Dr. Carlos Rodríguez Martínez
Correo electrónico profesional: juan.perez@tec.mx / maria.diaz@unam.mx
LinkedIn URL: https://linkedin.com/in/juanperez
Teléfono: +52 5555555555 (NOT year ranges like 2007-2015)
País de residencia o nacionalidad: México / Spain / Argentina
Universidad doctorado: Tecnológico de Monterrey / Universidad de Buenos Aires
Subject: Ingeniería Química / Chemical Engineering

CV:
""" + cv_text[:6000]

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0
        )
        raw = response.choices[0].message.content
        data = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
    except Exception as e:
        log(f"GPT error: {e} / Respuesta: {raw if 'raw' in locals() else 'No raw'}")
        data = {}
    
    # Fallbacks para casos donde GPT ponga "No encontrado"
    # Nombre: intentar extraer del nombre del archivo si no se encontró
    if not data.get("Nombre completo") or data["Nombre completo"].lower() == "no encontrado":
        # Primero intentar con regex
        name_from_regex = fallback_regex_name(cv_text)
        if name_from_regex != "No encontrado":
            data["Nombre completo"] = name_from_regex
        # Si no funciona, intentar extraer del nombre del archivo
        elif filename:
            # Extraer nombre del archivo (quitar extensión y reemplazar guiones/underscores por espacios)
            name_from_file = os.path.splitext(filename)[0]
            name_from_file = name_from_file.replace("_", " ").replace("-", " ")
            if name_from_file:
                data["Nombre completo"] = name_from_file
    
    # Email
    if not data.get("Correo electrónico profesional") or data["Correo electrónico profesional"].lower() == "no encontrado":
        data["Correo electrónico profesional"] = fallback_regex_email(cv_text)
    
    # Teléfono
    if not data.get("Teléfono") or data["Teléfono"].lower() == "no encontrado":
        data["Teléfono"] = fallback_regex_phone(cv_text)
    else:
        data["Teléfono"] = clean_phone(data["Teléfono"])
    
    # LinkedIn
    if not data.get("LinkedIn URL") or data["LinkedIn URL"].lower() == "no encontrado":
        data["LinkedIn URL"] = fallback_regex_linkedin(cv_text)
    
    # Asegurar que todos los campos existan
    for campo in [
        "Nombre completo", "Correo electrónico profesional", "LinkedIn URL",
        "Teléfono", "País de residencia o nacionalidad", "Universidad doctorado", "Subject"
    ]:
        if campo not in data or not data[campo]:
            data[campo] = "No encontrado"
    
    return data

def match_university_qs(univ_name_cv, qs_list):
    if not univ_name_cv or univ_name_cv.strip().lower() == 'no encontrado':
        return {"Universidad doctorado": "No encontrado", "QS Rank": "No encontrado"}
    
    # Normalizar el nombre de la universidad
    univ_norm = normalize_str(univ_name_cv)
    
    # Buscar aliases conocidos
    aliases = get_aliases_for_univ(univ_norm)
    qs_names_norm = [normalize_str(row[1]) for row in qs_list if len(row) >= 2]
    
    # Método 1: Búsqueda directa por alias
    for alias in aliases:
        if alias in qs_names_norm:
            idx = qs_names_norm.index(alias)
            return {"Universidad doctorado": qs_list[idx][1], "QS Rank": qs_list[idx][0]}
    
    # Método 2: Búsqueda por similitud de texto
    close_matches = get_close_matches(univ_norm, qs_names_norm, n=1, cutoff=0.85)
    if close_matches:
        idx = qs_names_norm.index(close_matches[0])
        return {"Universidad doctorado": qs_list[idx][1], "QS Rank": qs_list[idx][0]}
    
    # Método 3: Usar GPT para razonar sobre la universidad
    # Enviar toda la lista QS para que GPT pueda razonar mejor
    qs_universities = "\n".join([f"{row[1]} ({row[0]})" for row in qs_list[:200] if len(row) >= 2 and row[0] and row[1]])
    
    prompt = f"""
Necesito encontrar la universidad "{univ_name_cv}" en el ranking QS mundial de universidades.

Usa razonamiento paso a paso para identificar la universidad correcta:
1. Considera traducciones del nombre (ej: "Universidad de Barcelona" = "University of Barcelona")
2. Considera acrónimos y abreviaturas (ej: "MIT" = "Massachusetts Institute of Technology")
3. Considera variaciones regionales (ej: "Politécnico de Milán" = "Politecnico di Milano")
4. Considera fusiones o cambios de nombre (ej: "Paris-Saclay" antes era varias universidades separadas)
5. Considera campus específicos vs. sistema universitario completo

Aquí están las primeras 200 universidades del ranking QS (formato: Nombre (Ranking)):
{qs_universities}

Razona paso a paso para encontrar la universidad "{univ_name_cv}" en esta lista.
Si encuentras una coincidencia, devuelve el nombre exacto como aparece en la lista y su ranking.
Si no encuentras una coincidencia después de un análisis exhaustivo, responde "No encontrado".

Responde SOLO en este formato JSON:
{{
  "Razonamiento": "Tu razonamiento paso a paso aquí",
  "Universidad doctorado": "Nombre exacto de la universidad como aparece en la lista",
  "QS Rank": "Número de ranking"
}}
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # Usar GPT-4o para mejor razonamiento
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0
        )
        raw = response.choices[0].message.content
        data = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        log(f"Razonamiento para encontrar '{univ_name_cv}': {data.get('Razonamiento', 'No proporcionado')}")
        
        if data.get("Universidad doctorado", "").strip().lower() != "no encontrado":
            return {
                "Universidad doctorado": data.get("Universidad doctorado", "No encontrado"),
                "QS Rank": data.get("QS Rank", "No encontrado")
            }
    except Exception as e:
        log(f"Error en GPT para encontrar universidad: {e}")
    
    # Si GPT-4o falla, intentar con GPT-3.5 y chunks más pequeños como fallback
    for chunk in chunk_list(qs_list, 40):
        qs_chunk = "\n".join([f"{row[1]} ({row[0]})" for row in chunk if len(row) >= 2 and row[0] and row[1]])
        prompt = f"""
Lista: Nombres oficiales de universidades con su ranking QS (entre paréntesis).
Dada la universidad extraída de un CV: "{univ_name_cv}", identifica el nombre oficial y el QS Rank. 
Usa razonamiento para encontrar coincidencias incluso si el nombre no es exacto.
Considera traducciones, acrónimos, y variaciones regionales.
Si no hay match, pon "No encontrado".

Lista QS:
{qs_chunk}

Universidad extraída del CV:
{univ_name_cv}

Responde SOLO este JSON:
{{
  "Universidad doctorado": "...",
  "QS Rank": "..."
}}
"""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0
            )
            raw = response.choices[0].message.content
            data = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
            if data.get("Universidad doctorado", "").strip().lower() != "no encontrado":
                return data
        except Exception as e:
            log(f"GPT QS match error: {e}")
            continue
    
    return {"Universidad doctorado": "No encontrado", "QS Rank": "No encontrado"}

def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# === NUEVA PARTE: subir archivos a Google Drive y hacer públicos ===
def check_file_exists_in_drive(filename, drive_folder_id, creds_path):
    """Verifica si un archivo ya existe en Google Drive y devuelve su ID si existe"""
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    # Buscar el archivo por nombre en la carpeta específica
    query = f"name='{filename}' and '{drive_folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        return files[0].get('id')
    return None

def upload_file_to_drive(filepath, filename, drive_folder_id, creds_path):
    """Sube archivo a Google Drive y devuelve la URL pública. Si el archivo ya existe, devuelve su URL."""
    # Verificar si el archivo ya existe en Drive
    existing_file_id = check_file_exists_in_drive(filename, drive_folder_id, creds_path)
    
    if existing_file_id:
        # Si el archivo ya existe, devolver su URL
        url = f"https://drive.google.com/file/d/{existing_file_id}/view?usp=sharing"
        log(f"El archivo {filename} ya existe en Drive, usando URL existente")
        return url
    
    # Si no existe, subir el archivo
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': filename,
        'parents': [drive_folder_id]
    }
    media = MediaFileUpload(filepath, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = uploaded.get('id')
    # Hacer el archivo público (cualquiera con el link puede ver)
    service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
    # Obtener link directo
    url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    log(f"Archivo {filename} subido a Drive con éxito")
    return url

def create_folder_in_drive(folder_name, parent_folder_id, creds_path):
    """Crea una carpeta en Google Drive y devuelve su ID"""
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    # Verificar si la carpeta ya existe
    query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    
    if folders:
        # Si la carpeta ya existe, devolver su ID
        return folders[0].get('id')
    
    # Si no existe, crear la carpeta
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def move_file_in_drive(file_id, destination_folder_id, creds_path):
    """Mueve un archivo de una carpeta a otra en Google Drive"""
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    # Obtener las carpetas actuales del archivo
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    
    # Mover el archivo a la nueva carpeta
    file = service.files().update(
        fileId=file_id,
        addParents=destination_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
    
    return file

def get_processed_files_from_drive(processed_folder_id, creds_path):
    """Obtiene la lista de archivos en la carpeta de procesados en Google Drive"""
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    # Listar archivos en la carpeta de procesados
    query = f"'{processed_folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document') and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)", pageSize=1000).execute()
    files = results.get('files', [])
    
    # Obtener solo los nombres de los archivos
    processed_files = [file['name'] for file in files]
    return processed_files

def download_files_from_drive(drive_folder_id, processed_folder_id, local_folder, creds_path, already_processed_files):
    """Descarga solo los archivos PDF y DOCX no procesados de una carpeta de Google Drive a una carpeta local"""
    if not os.path.exists(local_folder):
        os.makedirs(local_folder, exist_ok=True)
        
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    service = build('drive', 'v3', credentials=creds)
    
    # Listar archivos en la carpeta de Drive
    query = f"'{drive_folder_id}' in parents and (mimeType='application/pdf' or mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document') and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    
    if not files:
        log(f"No se encontraron archivos PDF o DOCX en la carpeta de Drive {drive_folder_id}")
        return []
    
    # Eliminar duplicados por nombre de archivo
    unique_files = {}
    for file in files:
        # Si hay archivos con el mismo nombre, quedarse con el más reciente (asumiendo que está primero en la lista)
        if file['name'] not in unique_files:
            unique_files[file['name']] = file
    
    files = list(unique_files.values())
    
    # Filtrar archivos ya procesados
    files_to_download = []
    for file in files:
        if file['name'] not in already_processed_files:
            files_to_download.append(file)
    
    log(f"Se encontraron {len(files_to_download)} archivos nuevos para descargar de Google Drive")
    downloaded_files = []
    
    for file in files_to_download:
        file_id = file['id']
        file_name = file['name']
        local_path = os.path.join(local_folder, file_name)
        
        # Verificar si el archivo ya existe y tiene contenido
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            log(f"El archivo {file_name} ya existe y tiene contenido, omitiendo descarga")
            downloaded_files.append({"path": local_path, "id": file_id})
            continue
        
        try:
            # Descargar el archivo
            log(f"Descargando archivo {file_name}...")
            
            # Método 1: Usando MediaIoBaseDownload
            request = service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    log(f"Descarga {int(status.progress() * 100)}%")
            
            # Verificar que el archivo no esté vacío
            if os.path.getsize(local_path) == 0:
                log(f"El archivo descargado {file_name} está vacío, intentando método alternativo...")
                
                # Método 2: Descarga directa usando requests
                import requests
                url = f"https://drive.google.com/uc?export=download&id={file_id}"
                response = requests.get(url)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # Verificar nuevamente
                if os.path.getsize(local_path) == 0:
                    log(f"No se pudo descargar el archivo {file_name} correctamente")
                    continue
            
            log(f"Archivo {file_name} descargado correctamente ({os.path.getsize(local_path)} bytes)")
            downloaded_files.append({"path": local_path, "id": file_id})
        except Exception as e:
            log(f"Error al descargar el archivo {file_name}: {e}")
    
    return downloaded_files

def process_cv(cv_path, qs_list, drive_folder_id, creds_path):
    log(f"Procesando archivo: {cv_path}")
    filename = os.path.basename(cv_path)
    
    # Verificar si es un archivo de prueba (test_cv)
    if "test_cv" in filename.lower():
        log(f"Omitiendo archivo de prueba: {filename}")
        return None
    
    # Extraer texto del CV
    cv_text = ""
    if cv_path.lower().endswith('.pdf'):
        cv_text = extract_text_from_pdf(cv_path)
    elif cv_path.lower().endswith('.docx'):
        cv_text = extract_text_from_docx(cv_path)
    else:
        log(f"Formato de archivo no soportado: {cv_path}")
        return None
    
    # Si no se pudo extraer texto, usar el nombre del archivo como fallback
    if not cv_text.strip():
        log(f"Advertencia: Archivo con poco o ningún texto extraíble: {cv_path}. Usando nombre de archivo como fallback.")
        # Crear datos básicos a partir del nombre del archivo
        name_from_file = os.path.splitext(filename)[0]
        name_from_file = name_from_file.replace("_", " ").replace("-", " ")
        
        # Crear un conjunto mínimo de datos
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
        
        # Subir CV a Google Drive y guardar el link
        drive_url = upload_file_to_drive(cv_path, filename, drive_folder_id, creds_path)
        data["CV Link"] = drive_url
        data["CV FileName"] = filename
        
        log(f"Resultado para {filename} (usando fallback): {json.dumps(data, ensure_ascii=False)}")
        return data
    
    # Pasar el nombre del archivo para ayudar con la extracción del nombre
    data = extract_basic_data_gpt(cv_text, filename)
    
    # Buscar universidad en QS
    match_qs = match_university_qs(data.get("Universidad doctorado", ""), qs_list)
    data["Universidad doctorado"] = match_qs["Universidad doctorado"]
    data["QS Rank"] = match_qs["QS Rank"]
    
    # Asegurar que no hay valores vacíos
    for k in data:
        if not data[k]:
            data[k] = "No encontrado"
    
    # Subir CV a Google Drive y guardar el link
    drive_url = upload_file_to_drive(cv_path, filename, drive_folder_id, creds_path)
    data["CV Link"] = drive_url
    data["CV FileName"] = filename
    
    log(f"Resultado para {filename}: {json.dumps(data, ensure_ascii=False)}")
    return data

def process_all_cvs_in_folder(folder_path, qs_list, drive_folder_id, processed_folder_id, creds_path, service_account_file, spreadsheet_id, sheet_name, downloaded_files):
    results = []
    processed_files = set()  # Para evitar procesar duplicados
    
    # Obtener lista de archivos PDF y DOCX
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.pdf', '.docx'))]
    
    # Ordenar archivos para procesar primero los más grandes (suelen tener más información)
    files.sort(key=lambda f: os.path.getsize(os.path.join(folder_path, f)), reverse=True)
    
    # Crear un diccionario para mapear nombres de archivo a IDs de Drive
    file_id_map = {os.path.basename(file["path"]): file["id"] for file in downloaded_files}
    
    for fname in files:
        # Omitir archivos de prueba
        if "test_cv" in fname.lower():
            log(f"Omitiendo archivo de prueba: {fname}")
            continue
        
        # Verificar si ya se procesó un archivo con el mismo nombre base (sin extensión)
        base_name = os.path.splitext(fname)[0].lower()
        if base_name in processed_files:
            log(f"Omitiendo archivo duplicado: {fname}")
            continue
        
        log(f"Procesando {fname}...")
        cv_path = os.path.join(folder_path, fname)
        data = process_cv(cv_path, qs_list, drive_folder_id, creds_path)
        
        if data:
            results.append(data)
            processed_files.add(base_name)
            
            # Mover el archivo en Google Drive a la carpeta de procesados
            if fname in file_id_map:
                try:
                    file_id = file_id_map[fname]
                    move_file_in_drive(file_id, processed_folder_id, creds_path)
                    log(f"Archivo {fname} movido a la carpeta de procesados en Google Drive")
                except Exception as e:
                    log(f"Error al mover el archivo {fname} en Google Drive: {e}")
            
            # Eliminar el archivo local después de procesarlo
            try:
                os.remove(cv_path)
                log(f"Archivo local {fname} eliminado")
            except Exception as e:
                log(f"Error al eliminar el archivo local {fname}: {e}")
    
    log(f"Procesados {len(results)} CVs nuevos.")
    return results

def make_hyperlink(nombre, cv_link):
    # En Google Sheets, para que el hipervínculo funcione correctamente como fórmula,
    # necesitamos usar la función HYPERLINK con el signo igual al principio
    return f'=HYPERLINK("{cv_link}", "{nombre}")'

def get_processed_cvs_from_sheets(service_account_file, spreadsheet_id, sheet_name):
    """Obtiene la lista de CVs ya procesados en Google Sheets"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(service_account_file, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet(sheet_name)
    
    # Obtener todos los datos
    all_data = worksheet.get_all_values()
    
    # Si no hay datos o solo hay encabezados, devolver lista vacía
    if not all_data or len(all_data) <= 1:
        return []
    
    # Obtener el índice de la columna "CV FileName"
    headers = all_data[0]
    try:
        filename_idx = headers.index("CV FileName")
    except ValueError:
        # Si no existe la columna, devolver lista vacía
        return []
    
    # Obtener la lista de nombres de archivo
    processed_files = [row[filename_idx] for row in all_data[1:] if len(row) > filename_idx]
    return processed_files

def export_to_sheets(df, service_account_file, spreadsheet_id, sheet_name):
    """Exporta los resultados a Google Sheets, añadiendo filas nuevas sin borrar las existentes"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(service_account_file, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    
    # Intentar obtener la hoja, si no existe, crearla
    try:
        worksheet = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=sheet_name, rows=1, cols=1)
        log(f"Hoja '{sheet_name}' creada")
    
    # Verificar si la hoja está vacía
    all_values = worksheet.get_all_values()
    is_empty = len(all_values) == 0
    
    # Convertir DataFrame a lista de listas para la actualización
    data_to_add = []
    for _, row in df.iterrows():
        row_values = []
        for value in row:
            row_values.append(value)
        data_to_add.append(row_values)
    
    # Imprimir información de diagnóstico
    log(f"DataFrame original tiene {len(df)} filas")
    
    if is_empty:
        # Si la hoja está vacía, agregar encabezados y datos
        all_data = [df.columns.values.tolist()] + data_to_add
        
        # Actualizar la hoja con todos los datos
        worksheet.update(all_data)
        
        # Actualizar la primera fila para que sea el encabezado
        worksheet.format("1:1", {"textFormat": {"bold": True}})
        
        log(f"Hoja vacía: se agregaron {len(data_to_add)} filas con encabezados")
    else:
        # Si la hoja ya tiene datos, agregar solo las filas nuevas
        headers = all_values[0]
        
        # Verificar que los encabezados coincidan
        if list(df.columns) != headers:
            log("ADVERTENCIA: Los encabezados de la hoja no coinciden con los del DataFrame")
            log(f"Encabezados de la hoja: {headers}")
            log(f"Encabezados del DataFrame: {list(df.columns)}")
            
            # Ajustar el DataFrame para que coincida con los encabezados de la hoja
            df_adjusted = pd.DataFrame(columns=headers)
            for col in headers:
                if col in df.columns:
                    df_adjusted[col] = df[col]
                else:
                    df_adjusted[col] = "No encontrado"
            df = df_adjusted
            
            # Reconstruir data_to_add con el DataFrame ajustado
            data_to_add = []
            for _, row in df.iterrows():
                row_values = []
                for col in headers:
                    row_values.append(row.get(col, "No encontrado"))
                data_to_add.append(row_values)
        
        # Verificar si alguna de las filas ya existe en la hoja (por CV FileName)
        existing_filenames = []
        try:
            filename_col_idx = headers.index("CV FileName")
            existing_filenames = [row[filename_col_idx] for row in all_values[1:] if len(row) > filename_col_idx]
            log(f"Archivos ya existentes en la hoja: {existing_filenames}")
        except ValueError:
            log("ADVERTENCIA: No se encontró la columna 'CV FileName' en la hoja")
            filename_col_idx = -1  # Valor que no causará problemas en comparaciones
        
        # Filtrar filas que ya existen
        filtered_data = []
        filtered_df_indices = []
        
        for i, row_data in enumerate(data_to_add):
            if filename_col_idx >= 0 and len(row_data) > filename_col_idx:
                filename = row_data[filename_col_idx]
                if filename not in existing_filenames:
                    filtered_data.append(row_data)
                    if i < len(df.index):
                        filtered_df_indices.append(df.index[i])
                    log(f"Agregando fila para {filename} (nuevo)")
                else:
                    log(f"Omitiendo fila para {filename} porque ya existe en la hoja")
            else:
                filtered_data.append(row_data)
                if i < len(df.index):
                    filtered_df_indices.append(df.index[i])
                log(f"Agregando fila {i} (sin verificar duplicados)")
        
        # Actualizar data_to_add y df
        data_to_add = filtered_data
        if filtered_df_indices:
            df = df.loc[filtered_df_indices]
        else:
            df = pd.DataFrame()  # DataFrame vacío si no hay índices
        
        log(f"Después de filtrar, quedan {len(data_to_add)} filas para agregar")
        
        # Agregar las filas nuevas al final
        if data_to_add:
            try:
                # Usar batch_update para mayor eficiencia
                worksheet.append_rows(data_to_add)
                log(f"Se agregaron {len(data_to_add)} filas nuevas a la hoja existente")
            except Exception as e:
                log(f"Error al agregar filas: {e}")
                # Intentar método alternativo
                success_count = 0
                try:
                    for i, row_data in enumerate(data_to_add):
                        row_num = len(all_values) + i + 1  # +1 porque las filas empiezan en 1
                        worksheet.insert_row(row_data, row_num)
                        success_count += 1
                        log(f"Fila {i+1}/{len(data_to_add)} agregada individualmente")
                except Exception as e2:
                    log(f"Error al agregar filas individualmente: {e2}")
                log(f"Se agregaron {success_count} filas individualmente")
        else:
            log("No hay filas nuevas para agregar a la hoja")
    
    # Ahora, actualizar específicamente la columna de nombres con fórmulas
    if len(df) > 0:
        # Obtener todos los valores actualizados
        all_values = worksheet.get_all_values()
        headers = all_values[0]
        
        try:
            nombre_col_idx = headers.index("Nombre completo") + 1  # +1 porque gspread usa índices basados en 1
            
            # Encontrar las filas recién agregadas
            start_row = len(all_values) - len(df) + 1
            
            log(f"Actualizando fórmulas de hipervínculo para {len(df)} filas, comenzando en la fila {start_row}")
            
            # Actualizar las fórmulas de hipervínculo
            for i, (_, row) in enumerate(df.iterrows(), start=start_row):
                nombre = row["Nombre completo"]
                # Extraer el URL del hipervínculo
                if isinstance(nombre, str) and nombre.startswith("=HYPERLINK("):
                    # Extraer URL y texto del hipervínculo
                    import re
                    match = re.search(r'=HYPERLINK\("([^"]+)", "([^"]+)"\)', nombre)
                    if match:
                        url = match.group(1)
                        text = match.group(2)
                        # Crear la fórmula sin comillas simples
                        formula = f'=HYPERLINK("{url}", "{text}")'
                        # Actualizar la celda directamente
                        try:
                            worksheet.update_cell(i, nombre_col_idx, formula)
                            log(f"Actualizada fórmula de hipervínculo en fila {i}, columna {nombre_col_idx}")
                        except Exception as e:
                            log(f"Error al actualizar hipervínculo en fila {i}: {e}")
        except ValueError:
            log("ADVERTENCIA: No se encontró la columna 'Nombre completo' en la hoja")

def main():
    log("Descargando lista QS desde Google Sheets...")
    qs_list = get_qs_list_from_google_sheets(QS_GOOGLE_SHEET_ID, QS_TAB_NAME, SERVICE_ACCOUNT_FILE)
    log(f"Universidades QS cargadas: {len(qs_list)}")
    
    # Verificar/crear la carpeta de procesados en Google Drive
    processed_folder_id = GOOGLE_DRIVE_PROCESSED_FOLDER_ID
    if processed_folder_id == "1Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd-Yd":
        # Si no se ha configurado un ID específico, crear la carpeta
        processed_folder_id = create_folder_in_drive("CVs_Procesados", GOOGLE_DRIVE_FOLDER_ID, SERVICE_ACCOUNT_FILE)
        log(f"Carpeta de procesados creada en Google Drive con ID: {processed_folder_id}")
    
    # Obtener lista de CVs ya procesados en Google Sheets y en la carpeta de procesados
    sheets_processed = get_processed_cvs_from_sheets(SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME)
    drive_processed = get_processed_files_from_drive(processed_folder_id, SERVICE_ACCOUNT_FILE)
    
    # Combinar ambas listas para tener todos los archivos ya procesados
    already_processed = list(set(sheets_processed + drive_processed))
    log(f"Se encontraron {len(already_processed)} CVs ya procesados")
    
    # Descargar solo los archivos nuevos de Google Drive a la carpeta local
    log(f"Descargando archivos nuevos de Google Drive a la carpeta local {FOLDER_CVS}...")
    downloaded_files = download_files_from_drive(GOOGLE_DRIVE_FOLDER_ID, processed_folder_id, FOLDER_CVS, SERVICE_ACCOUNT_FILE, already_processed)
    
    if not downloaded_files:
        log("No hay nuevos CVs para procesar. Terminando.")
        return
    
    log("Procesando CVs y subiendo a Google Drive...")
    resultados = process_all_cvs_in_folder(FOLDER_CVS, qs_list, GOOGLE_DRIVE_FOLDER_ID, processed_folder_id, 
                                          SERVICE_ACCOUNT_FILE, SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME,
                                          downloaded_files)
    
    # Si no hay nuevos CVs para procesar, terminar
    if not resultados:
        log("No hay nuevos CVs para procesar. Terminando.")
        return
    
    log("Procesando resultados...")
    df = pd.DataFrame(resultados)
    
    # Imprimir información de diagnóstico
    log(f"DataFrame original tiene {len(df)} filas")
    
    # Hipervínculo: crea columna combinada
    df["Nombre completo"] = df.apply(lambda row: make_hyperlink(row["Nombre completo"], row["CV Link"]), axis=1)
    
    # NUEVA LÓGICA DE DEDUPLICACIÓN:
    # 1. Primero, separar los CVs con email válido de los que no tienen email
    df_con_email = df[df["Correo electrónico profesional"] != "No encontrado"].copy()
    df_sin_email = df[df["Correo electrónico profesional"] == "No encontrado"].copy()
    
    log(f"CVs con email válido: {len(df_con_email)}")
    log(f"CVs sin email: {len(df_sin_email)}")
    
    # 2. Deduplicar los que tienen email por el email (esto es seguro)
    if len(df_con_email) > 0:
        log(f"Antes de deduplicar por email: {len(df_con_email)} filas")
        df_con_email = df_con_email.sort_values("Correo electrónico profesional").drop_duplicates(subset=["Correo electrónico profesional"], keep='first')
        log(f"Después de deduplicar por email: {len(df_con_email)} filas")
    
    # 3. Para los que no tienen email, deduplicar por nombre exacto del archivo CV
    if len(df_sin_email) > 0:
        log(f"Antes de deduplicar por nombre de archivo: {len(df_sin_email)} filas")
        df_sin_email = df_sin_email.sort_values("CV FileName").drop_duplicates(subset=["CV FileName"], keep='first')
        log(f"Después de deduplicar por nombre de archivo: {len(df_sin_email)} filas")
    
    # 4. Combinar ambos DataFrames
    df = pd.concat([df_con_email, df_sin_email])
    log(f"DataFrame combinado tiene {len(df)} filas")
    
    # Guardar y exportar
    log("Guardando resultados en CSV...")
    df.to_csv(OUTPUT_CSV, index=False)
    log(f"Resultados guardados en {OUTPUT_CSV}")
    
    if not df.empty:
        log("Exportando resultados a Google Sheets...")
        log(f"DataFrame final tiene {len(df)} filas para exportar")
        export_to_sheets(df, SERVICE_ACCOUNT_FILE, SPREADSHEET_ID, SHEET_NAME)
        log("Listo. Resultados subidos a Sheets.")

if __name__ == "__main__":
    main()
