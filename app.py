from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

# Diccionario maestro con la ortografía oficial para el reporte final
DICCIONARIO_ESTACIONES = {
    "HVA": "Hermilio Valdizán",
    "OVA": "Óvalo Santa Anita",
    "EVT": "Evitamiento",
    "MSA": "Mercado Santa Anita",
    "COL": "Colectora Industrial"
}

# Base de datos masiva de errores OCR y de dedo comunes cometidos por los operadores o escáneres de fotos
MAPEO_ERRORES_ESTACIONES = {
    # Errores para Hermilio Valdizán
    "HVA": "HVA", "HV4": "HVA", "HBA": "HVA", "HA4": "HVA", "HVA1": "HVA",
    "HERMILIO": "HVA", "VALDIZAN": "HVA", "VALDISAN": "HVA", "VALDI": "HVA", 
    "HERM1L1O": "HVA", "BALDIZAN": "HVA", "HERMILIO VALDI": "HVA", "HERMILIO VALDIZAN": "HVA",
    
    # Errores para Óvalo Santa Anita
    "OVA": "OVA", "OV4": "OVA", "OBA": "OVA", "0VA": "OVA", "OA4": "OVA",
    "OVALO": "OVA", "SANTA ANITA": "OVA", "STA ANITA": "OVA", "STA. ANITA": "OVA", 
    "OVALO SANTA ANITA": "OVA", "OVALO STA ANITA": "OVA", "SANTA ANTA": "OVA",
    
    # Errores para Evitamiento
    "EVT": "EVT", "EVT2": "EVT", "EBT": "EVT", "EV1TAM1ENTO": "EVT", "EVITA": "EVT",
    "EVITAMIENTO": "EVT", "EVITAM1ENT0": "EVT", "EBITAMIENTO": "EVT",
    
    # Errores para Mercado Santa Anita
    "MSA": "MSA", "M5A": "MSA", "MBA": "MSA", "MERCADO": "MSA", 
    "MERCADO SANTA ANITA": "MSA", "MERCADO STA ANITA": "MSA",
    
    # Errores para Colectora Industrial
    "COL": "COL", "C0L": "COL", "COLECTORA": "COL", "COLECT0RA": "COL", 
    "COLECTORA INDUSTRIAL": "COL", "C0LECT0RA 1NDUSTR1AL": "COL"
}

def normalizar_texto_ocr(linea):
    """
    Esta función actúa como un filtro limpiador que repara los peores errores 
    de reconocimiento de la foto antes de hacer los cálculos matemáticos.
    """
    # Convertir todo a mayúsculas para unificar la lectura
    linea_alta = linea.upper().strip()
    
    # 1. Reparar variantes erróneas de W400 (W4oo, W40o, W4o0, W4OO, WA00, V400, M400, etc.)
    linea_alta = re.sub(r"\b[WVA0-9][4A][0O0oQ]{2}\b", "W400", linea_alta)
    
    # 2. Reparar variantes de la palabra clave CDV (Cdv, CDV, Cav, Cdb, C6v, C0v, Cdvv, etc.)
    linea_alta = re.sub(r"\b(CDV|CDVV|CAV|CDB|C6V|C0V|CD8|COV)\b", "CDV", linea_alta)
    
    # 3. Corregir palabras del sistema críticas que el OCR daña recurrentemente
    reemplazos = {
        "LNDICACION": "INDICACION",
        "1NDICACION": "INDICACION",
        "INDLCAC1ON": "INDICACION",
        "INDLCACLON": "INDICACION",
        "DESLLZAMLENTO": "DESLIZAMIENTO",
        "DESLISAMIENTO": "DESLIZAMIENTO",
        "DESLIZAM1ENT0": "DESLIZAMIENTO",
        "DETECTAD0": "DETECTADO",
        "DETECTAD": "DETECTADO",
        "TRBN": "TREN",
        "TREN ": "TREN"
    }
    for error, correccion in reemplazos.items():
        linea_alta = linea_alta.replace(error, correccion)
        
    return linea_alta

def extraer_datos_turno(linea):
    """
    Analiza la línea limpia de forma elástica. Extrae los datos sin importar 
    el orden ni la separación de las palabras en el bloc de notas.
    """
    linea_limpia = normalizar_texto_ocr(linea)
    
    # Filtro de seguridad: validamos si la línea contiene rastros de la alarma estudiada
    if not any(k in linea_limpia for k in ["DESLIZ", "DESLIS", "SLIZ", "W400", "CDV", "CARRERA", "TID"]):
        return None, None, None, None

    # ==========================================
    # 1. EXTRACCIÓN INTELIGENTE DEL TREN
    # ==========================================
    num_tren = None
    nombre_tren_mostrar = ""
    
    # Caso A: Estructura cruda del sistema (W400 228)
    match_w400 = re.search(r"W400\s+(\d{3})", linea_limpia)
    # Caso B: Formato abreviado manual (T28, T29, T-28, T029)
    match_t = re.search(r"\bT-?(\d{2,3})\b|T(\d{2,3})", linea_limpia)
    # Caso C: Redacción textual (Tren 28)
    match_tren_palabra = re.search(r"TREN\s+(\d{2,3})", linea_limpia)
    
    if match_w400:
        cod_tren = match_w400.group(1)
        num_tren = int(cod_tren[-2:])
        nombre_tren_mostrar = f"Tren {num_tren} (Cód {cod_tren})"
    elif match_tren_palabra:
        num_tren = int(match_tren_palabra.group(1))
        nombre_tren_mostrar = f"Tren {num_tren}"
    elif match_t:
        # Extraer el grupo numérico capturado
        val = match_t.group(1) or match_t.group(2)
        num_tren = int(val[-2:])
        nombre_tren_mostrar = f"Tren {num_tren}"
    else:
        # Último recurso: si el OCR se comió la "T" o el "W400" pero dejó el código del tren suelto (228, 229, 214)
        match_suelto = re.search(r"\b(2\d{2})\b", linea_limpia)
        if match_suelto:
            cod_tren = match_suelto.group(1)
            num_tren = int(cod_tren[-2:])
            nombre_tren_mostrar = f"Tren {num_tren} (Cód {cod_tren})"

    # ==========================================
    # 2. EXTRACCIÓN INTELIGENTE DEL CDV
    # ==========================================
    cdv = None
    # Busca la estructura clásica: CDV 2301 o CDV 2307A
    match_cdv = re.search(r"CDV\s*([A-Z0-9]{4}[A-Z]?)", linea_limpia)
    
    if not match_cdv:
        # Si no dice la palabra CDV, busca un número aislado de 4 dígitos (con letras opcionales de vía como A, B)
        match_cdv = re.search(r"\b(\d{4}[A-Z]?)\b", linea_limpia)
        
    if match_cdv:
        cdv = match_cdv.group(1)
        # Corrige el error crítico del OCR que confunde un cero por una letra O dentro del número de vía (ej: 23O1 -> 2301)
        cdv = cdv.replace("O", "0") 

    # ==========================================
    # 3. EXTRACCIÓN INTELIGENTE DE LA ESTACIÓN
    # ==========================================
    estacion_oficial = "Vía Principal" # Nombre base si no se logra extraer ninguna sigla conocida
    
    for variacion, sigla in MAPEO_ERRORES_ESTACIONES.items():
        if variacion in linea_limpia:
            estacion_oficial = DICCIONARIO_ESTACIONES.get(sigla)
            break

    # Si logramos rescatar los dos datos vitales (Tren y Vía), la lectura es exitosa
    if num_tren is not None and cdv is not None:
        return num_tren, cdv, estacion_oficial, nombre_tren_mostrar
        
    return None, None, None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    reporte = None
    texto_ingresado = ""
    texto_resumen = ""

    if request.method == 'POST':
        texto_ingresado = request.form.get('texto_alarmas', '').strip()
        if texto_ingresado:
            total = 0
            trenes = Counter()
            cdvs = Counter()
            resumen_detallado = {}
            trenes_unicos = set()

            for linea in texto_ingresado.split('\n'):
                if not linea.strip():
                    continue
                
                num_tren, cdv, estacion, nombre_mostrar = extraer_datos_flexibles(linea)
                
                if num_tren is not None and cdv is not None:
                    total += 1
                    trenes_unicos.add(num_tren)
                    trenes[nombre_mostrar] += 1
                    
                    asociacion = f"{cdv} (Tren {num_tren})"
                    cdvs[asociacion] += 1
                    
                    if num_tren not in resumen_detallado:
                        resumen_detallado[num_tren] = Counter()
                    resumen_detallado[num_tren][(cdv, estacion)] += 1
            
            # --- Generación del Texto Limpio y Formateado para el informe ---
            if total > 0:
                lista_trenes = " y ".join(str(t) for t in sorted(trenes_unicos))
                
                texto_resumen = f"'ALARMAS DE DESLIZAMIENTO DETECTADO ON - VIA PRINCIPAL\n"
                texto_resumen += f"Durante el servicio comercial se registraron un total de {total} alarmas de deslizamiento en los trenes {lista_trenes}.\n"
                
                for tren in sorted(resumen_detallado.keys()):
                    for (c, est), cant in resumen_detallado[tren].most_common():
                        # Asegura el prefijo de dos dígitos (01, 05, 12) para mantener el formato limpio
                        texto_resumen += f"Tren {tren}, se registraron {cant:02d} deslizamiento en el CdV {c} - {est}\n"

            reporte = {
                'total': total,
                'trenes': trenes.most_common(),
                'cdvs': cdvs.most_common()
            }

    return render_template('index.html', reporte=reporte, texto_ingresado=texto_ingresado, texto_resumen=texto_resumen)

# Función puente para mantener la compatibilidad con nombres anteriores
def extraer_datos_flexibles(linea):
    return extraer_datos_flexibles_internal(linea)

def extraer_datos_flexibles_internal(linea):
    return extraer_datos_flexibles(linea)

extraer_datos_flexibles = extraer_datos_flexibles
extraer_datos_flexibles_internal = extraer_datos_flexibles

if __name__ == '__main__':
    app.run(debug=True)