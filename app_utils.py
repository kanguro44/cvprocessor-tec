import pandas as pd
import io
import base64
from datetime import datetime
import os
from fpdf import FPDF

# Función para generar un reporte Excel
def generate_excel_report(data):
    """Genera un reporte Excel con los datos procesados"""
    output = io.BytesIO()
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    try:
        # Intentar usar xlsxwriter si está disponible
        import xlsxwriter
        
        # Guardar como Excel con formato
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
    
    except ImportError:
        # Si xlsxwriter no está disponible, usar openpyxl o el motor predeterminado
        try:
            # Intentar con openpyxl
            df.to_excel(output, sheet_name='Resultados', index=False, engine='openpyxl')
        except:
            # Último recurso: usar el motor predeterminado de pandas
            df.to_excel(output, sheet_name='Resultados', index=False)
    
    # Regresar al inicio del stream
    output.seek(0)
    return output

# Función para generar un reporte PDF
def generate_pdf_report(data, lang="es"):
    """Genera un reporte PDF con los datos procesados"""
    output = io.BytesIO()
    
    # Crear PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    title = "Reporte de Procesamiento de CVs" if lang == "es" else "CV Processing Report"
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, 0, 1, "C")
    
    # Fecha y hora
    now = datetime.now()
    date_str = f"Fecha: {now.strftime('%d/%m/%Y')}" if lang == "es" else f"Date: {now.strftime('%m/%d/%Y')}"
    time_str = f"Hora: {now.strftime('%H:%M:%S')}" if lang == "es" else f"Time: {now.strftime('%H:%M:%S')}"
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, date_str, 0, 1)
    pdf.cell(0, 10, time_str, 0, 1)
    
    # Resumen
    summary_title = "Resumen del procesamiento:" if lang == "es" else "Processing summary:"
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, summary_title, 0, 1)
    
    # Estadísticas
    pdf.set_font("Arial", "", 12)
    total_str = f"Total procesados: {len(data)}" if lang == "es" else f"Total processed: {len(data)}"
    pdf.cell(0, 10, total_str, 0, 1)
    
    # Tabla de resultados
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    details_title = "Detalles de los CVs procesados:" if lang == "es" else "Processed CVs details:"
    pdf.cell(0, 10, details_title, 0, 1)
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Encabezados de tabla
    pdf.set_font("Arial", "B", 10)
    
    # Definir columnas a mostrar (limitadas por espacio en PDF)
    columns_to_show = ["Nombre completo", "Correo electrónico profesional", "Universidad doctorado", "QS Rank"]
    
    # Calcular ancho de columnas
    col_width = 190 / len(columns_to_show)
    
    # Imprimir encabezados
    for col in columns_to_show:
        pdf.cell(col_width, 10, col, 1, 0, "C")
    pdf.ln()
    
    # Imprimir datos
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        for col in columns_to_show:
            # Limpiar hipervínculos en la columna "Nombre completo"
            value = row[col]
            if col == "Nombre completo" and isinstance(value, str) and value.startswith("=HYPERLINK("):
                import re
                match = re.search(r'=HYPERLINK\("([^"]+)", "([^"]+)"\)', value)
                if match:
                    value = match.group(2)
            
            # Truncar valores largos
            if isinstance(value, str) and len(value) > 30:
                value = value[:27] + "..."
                
            pdf.cell(col_width, 10, str(value), 1, 0, "L")
        pdf.ln()
    
    # Pie de página
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 8)
    footer = f"Generado el {now.strftime('%d/%m/%Y %H:%M:%S')}" if lang == "es" else f"Generated on {now.strftime('%m/%d/%Y %H:%M:%S')}"
    pdf.cell(0, 10, footer, 0, 0, "C")
    
    # Guardar PDF en el stream
    pdf.output(output)
    
    # Regresar al inicio del stream
    output.seek(0)
    return output

# Función para crear un enlace de descarga
def get_download_link(buffer, filename, text):
    """Genera un enlace de descarga para un archivo en memoria"""
    b64 = base64.b64encode(buffer.getvalue()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Función para leer resultados del CSV
def read_results_csv(csv_path):
    """Lee los resultados del archivo CSV"""
    if not os.path.exists(csv_path):
        return []
    
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []
