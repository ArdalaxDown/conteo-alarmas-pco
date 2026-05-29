from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    reporte = None
    texto_ingresado = ""
    texto_resumen = ""

    if request.method == 'POST':
        texto_ingresado = request.form.get('texto_alarmas', '').strip()
        if texto_ingresado:
            # Nueva expresión regular: Captura (1) Tren, (2) Estación, y (3) Cdv
            patron = re.compile(r"W400\s+(\d{3}).*?en\s+(.+?)\s+([A-Z0-9]+):\s*Indicaci[oó]n De Deslizamiento", re.IGNORECASE)
            
            total = 0
            trenes = Counter()
            cdvs = Counter()
            
            # Variables para el texto final
            resumen_detallado = {}
            trenes_unicos = set()

            for linea in texto_ingresado.split('\n'):
                if "Indicación De Deslizamiento" in linea or "Indicacion De Deslizamiento" in linea:
                    match = patron.search(linea)
                    if match:
                        total += 1
                        cod_tren = match.group(1)
                        estacion = match.group(2).strip().title() # Convierte "HERMILIO VALDIZAN" a "Hermilio Valdizan"
                        cdv = match.group(3)
                        
                        num_tren = int(cod_tren[-2:]) 
                        trenes_unicos.add(num_tren)
                        
                        trenes[f"Tren {num_tren} (Cód {cod_tren})"] += 1
                        asociacion = f"{cdv} (Tren {num_tren})"
                        cdvs[asociacion] += 1
                        
                        # Almacenamos los datos para armar el texto final
                        if num_tren not in resumen_detallado:
                            resumen_detallado[num_tren] = Counter()
                        resumen_detallado[num_tren][(cdv, estacion)] += 1
            
            # --- Generar el texto final solicitado ---
            if total > 0:
                # Une los trenes (ej: "28 y 29")
                lista_trenes = " y ".join(str(t) for t in sorted(trenes_unicos))
                
                texto_resumen = f"'ALARMAS DE DESLIZAMIENTO DETECTADO ON - VIA PRINCIPAL\n"
                texto_resumen += f"Durante el servicio comercial se registraron un total de {total} alarmas de deslizamiento en los trenes {lista_trenes}.\n"
                
                for tren in sorted(resumen_detallado.keys()):
                    for (cdv, est), cant in resumen_detallado[tren].most_common():
                        # El :02d formatea el número para que ponga "01" o "05" en vez de "1" o "5"
                        texto_resumen += f"Tren {tren}, se registraron {cant:02d} deslizamiento en el CdV {cdv} - {est}\n"

            # Pasamos los datos a la web
            reporte = {
                'total': total,
                'trenes': trenes.most_common(),
                'cdvs': cdvs.most_common()
            }

    return render_template('index.html', reporte=reporte, texto_ingresado=texto_ingresado, texto_resumen=texto_resumen)

if __name__ == '__main__':
    app.run(debug=True)