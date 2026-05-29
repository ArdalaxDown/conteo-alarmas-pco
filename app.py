from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

# Diccionario inteligente para estaciones
DICCIONARIO_ESTACIONES = {
    "HVA": "Hermilio Valdizán",
    "OVA": "Óvalo Santa Anita",
    "EVT": "Evitamiento",
    "MSA": "Mercado Santa Anita",
    "COL": "Colectora Industrial"
}

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
                linea = linea.strip()
                if not linea:
                    continue
                
                num_tren = None
                estacion = None
                cdv = None
                nombre_tren_mostrar = ""
                
                match_largo = re.search(r"W400\s+(\d{3}).*?en\s+(.+?)\s+([A-Z0-9]+):\s*Indicaci[oó]n", linea, re.IGNORECASE)
                match_corto = re.search(r"T(\d{2,3}).*?Cdv\s+([A-Z0-9]+)\s+.*?Carrera\s+\d+\s+([A-Z]+)", linea, re.IGNORECASE)
                match_simple = re.search(r"T(\d{2,3})\s*-\s*Cdv\s+([A-Z0-9]+)\s*-\s*([A-Z]+)", linea, re.IGNORECASE)
                match_natural = re.search(r"Tren\s+(\d{2,3}).*?cdv\s+([A-Z0-9]+).*?(HVA|OVA|EVT|MSA|COL)", linea, re.IGNORECASE)

                if match_largo:
                    cod_tren = match_largo.group(1)
                    num_tren = int(cod_tren[-2:]) 
                    estacion = match_largo.group(2).strip().title()
                    cdv = match_largo.group(3).upper()
                    nombre_tren_mostrar = f"Tren {num_tren} (Cód {cod_tren})"
                elif match_corto:
                    num_tren = int(match_corto.group(1))
                    cdv = match_corto.group(2).upper()
                    sigla_est = match_corto.group(3).upper()
                    estacion = DICCIONARIO_ESTACIONES.get(sigla_est, sigla_est.title())
                    nombre_tren_mostrar = f"Tren {num_tren}"
                elif match_simple:
                    num_tren = int(match_simple.group(1))
                    cdv = match_simple.group(2).upper()
                    sigla_est = match_simple.group(3).upper()
                    estacion = DICCIONARIO_ESTACIONES.get(sigla_est, sigla_est.title())
                    nombre_tren_mostrar = f"Tren {num_tren}"
                elif match_natural:
                    num_tren = int(match_natural.group(1))
                    cdv = match_natural.group(2).upper()
                    sigla_est = match_natural.group(3).upper()
                    estacion = DICCIONARIO_ESTACIONES.get(sigla_est, sigla_est.title())
                    nombre_tren_mostrar = f"Tren {num_tren}"

                if num_tren is not None and cdv is not None:
                    total += 1
                    trenes_unicos.add(num_tren)
                    trenes[nombre_tren_mostrar] += 1
                    asociacion = f"{cdv} (Tren {num_tren})"
                    cdvs[asociacion] += 1
                    
                    if num_tren not in resumen_detallado:
                        resumen_detallado[num_tren] = Counter()
                    resumen_detallado[num_tren][(cdv, estacion)] += 1
            
            # Formateo del texto para copiar
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