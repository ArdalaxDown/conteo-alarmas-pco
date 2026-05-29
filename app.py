from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

# Diccionario maestro oficial
DICCIONARIO_ESTACIONES = {
    "HVA": "Hermilio Valdizán",
    "OVA": "Óvalo Santa Anita",
    "EVT": "Evitamiento",
    "MSA": "Mercado Santa Anita",
    "COL": "Colectora Industrial"
}

# Diccionario inteligente: Atrapa errores OCR, tildes y abreviaturas
VARIACIONES_ESTACIONES = {
    "HVA": ["HVA", "HV4", "HBA", "HA4", "HERMILIO", "VALDIZAN", "VALDIZÁN", "VALDISAN", "VALDI", "HERM1L1O"],
    "OVA": ["OVA", "OV4", "0VA", "OA4", "OVALO", "ÓVALO", "SANTA ANITA", "STA ANITA", "STA. ANITA", "SANTA ANTA"],
    "EVT": ["EVT", "EVT2", "EBT", "EV1TAM1ENTO", "EVITA", "EVITAMIENTO", "EBITAMIENTO"],
    "MSA": ["MSA", "M5A", "MBA", "MERCADO"],
    "COL": ["COL", "C0L", "COLECTORA", "C0LECT0RA", "INDUSTRIAL", "1NDUSTR1AL"]
}

def buscar_estacion(texto):
    texto_limpio = texto.upper()
    for sigla_correcta, variaciones in VARIACIONES_ESTACIONES.items():
        for var in variaciones:
            if var in texto_limpio:
                return sigla_correcta
    return None

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
                linea = linea.strip().upper()
                if not linea:
                    continue
                
                num_tren = None
                estacion = None
                cdv = None
                nombre_tren_mostrar = ""

                # ==========================================
                # 1. LIMPIEZA PREVIA AL ANÁLISIS (Errores de Foto/OCR)
                # ==========================================
                # Transforma letras "o" mayúsculas en el código W400
                linea = re.sub(r"\b[WVA][4A][0O]{2}\b", "W400", linea)
                # Corrige cualquier variante extraña de CDV
                linea = re.sub(r"\b(CDV|CDVV|CAV|CDB|C0V|COV)\b", "CDV", linea)
                # Corrige palabras que la cámara suele leer mal
                linea = linea.replace("LNDICACION", "INDICACION").replace("1NDICACION", "INDICACION")
                linea = linea.replace("DESLLZAMLENTO", "DESLIZAMIENTO").replace("DESLISAMIENTO", "DESLIZAMIENTO")

                # Filtro rápido para ignorar líneas basura
                if "DESLIZ" not in linea and "W400" not in linea and "CDV" not in linea:
                    continue

                # ==========================================
                # 2. BÚSQUEDA DE PATRONES
                # ==========================================
                # PATRÓN 1: Formato Largo (Sistema) - Soporta múltiples espacios y tildes
                match_largo = re.search(r"W400\s+(\d{2,3}).*?EN\s+(.+?)\s+([A-Z0-9]{4}[A-Z]?):\s*INDICA", linea)
                
                # PATRÓN 2: Formato Corto - Ej: T29 CDV 2301 Carrera 2155 HVA
                match_corto = re.search(r"T(\d{2,3}).*?CDV\s+([A-Z0-9]{4}[A-Z]?).*?(HVA|OVA|EVT|MSA|COL)", linea)
                
                # PATRÓN 3: Formato Simple - Ej: T28 - CDV 2301 - OVA
                match_simple = re.search(r"T(\d{2,3})\s*[-_]?\s*CDV\s+([A-Z0-9]{4}[A-Z]?)\s*[-_]?\s*([A-Z]+)", linea)

                # PATRÓN 4: Natural
                match_natural = re.search(r"TREN\s+(\d{2,3}).*?CDV\s+([A-Z0-9]{4}[A-Z]?).*?([A-ZÁÉÍÓÚ]+)", linea)

                # ==========================================
                # 3. EXTRACCIÓN Y GUARDADO DE DATOS
                # ==========================================
                if match_largo:
                    cod_tren = match_largo.group(1)
                    num_tren = int(cod_tren[-2:])
                    estacion_raw = match_largo.group(2)
                    cdv = match_largo.group(3)
                    
                    sigla_est = buscar_estacion(estacion_raw)
                    estacion = DICCIONARIO_ESTACIONES.get(sigla_est, "Vía Principal")
                    nombre_tren_mostrar = f"Tren {num_tren} (Cód {cod_tren})"

                elif match_corto or match_simple or match_natural:
                    match = match_corto or match_simple or match_natural
                    num_tren = int(match.group(1)[-2:])
                    cdv = match.group(2)
                    
                    # Corrección si la cámara confundió el número 0 del Cdv con la letra O
                    cdv = cdv.replace("O", "0") 
                    
                    sigla_est = buscar_estacion(linea)
                    estacion = DICCIONARIO_ESTACIONES.get(sigla_est, "Vía Principal")
                    nombre_tren_mostrar = f"Tren {num_tren}"

                # Guardar al contador solo si tenemos Tren y Cdv
                if num_tren is not None and cdv is not None:
                    total += 1
                    trenes_unicos.add(num_tren)
                    trenes[nombre_tren_mostrar] += 1
                    
                    asociacion = f"{cdv} (Tren {num_tren})"
                    cdvs[asociacion] += 1
                    
                    if num_tren not in resumen_detallado:
                        resumen_detallado[num_tren] = Counter()
                    resumen_detallado[num_tren][(cdv, estacion)] += 1
            
            # ==========================================
            # 4. GENERACIÓN DEL REPORTE FINAL TEXTUAL
            # ==========================================
            if total > 0:
                lista_trenes = " y ".join(str(t) for t in sorted(trenes_unicos))
                texto_resumen = f"'ALARMAS DE DESLIZAMIENTO DETECTADO ON - VIA PRINCIPAL\n"
                texto_resumen += f"Durante el servicio comercial se registraron un total de {total} alarmas de deslizamiento en los trenes {lista_trenes}.\n"
                for tren in sorted(resumen_detallado.keys()):
                    for (c, est), cant in resumen_detallado[tren].most_common():
                        texto_resumen += f"Tren {tren}, se registraron {cant:02d} deslizamiento en el CdV {c} - {est}\n"

            reporte = {
                'total': total,
                'trenes': trenes.most_common(),
                'cdvs': cdvs.most_common()
            }

    return render_template('index.html', reporte=reporte, texto_ingresado=texto_ingresado, texto_resumen=texto_resumen)

if __name__ == '__main__':
    app.run(debug=True)