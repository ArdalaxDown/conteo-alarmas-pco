from flask import Flask, render_template, request
import re
from collections import Counter

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    reporte = None
    texto_ingresado = ""

    if request.method == 'POST':
        texto_ingresado = request.form.get('texto_alarmas', '').strip()
        if texto_ingresado:
            # Expresión regular para extraer código de tren y Cdv
            patron = re.compile(r"W400\s+(\d{3}).*?en.*?\s([A-Z0-9]+):\s*Indicación De Deslizamiento")
            
            total = 0
            trenes = Counter()
            cdvs = Counter()

            for linea in texto_ingresado.split('\n'):
                if "Indicación De Deslizamiento" in linea or "Indicacion De Deslizamiento" in linea:
                    match = patron.search(linea)
                    if match:
                        total += 1
                        cod_tren = match.group(1)
                        cdv = match.group(2)
                        
                        # Convertir código a número de tren (ej. 228 -> 28)
                        num_tren = int(cod_tren[-2:]) 
                        trenes[f"Tren {num_tren} (Cód {cod_tren})"] += 1
                        
                        # --- EL CAMBIO ESTÁ AQUÍ ---
                        # Guardamos el Cdv y el tren juntos en el mismo texto
                        asociacion = f"{cdv} (Tren {num_tren})"
                        cdvs[asociacion] += 1
            
            # Pasamos los datos estructurados al frontend
            reporte = {
                'total': total,
                'trenes': trenes.most_common(),
                'cdvs': cdvs.most_common()
            }

    return render_template('index.html', reporte=reporte, texto_ingresado=texto_ingresado)

if __name__ == '__main__':
    app.run(debug=True)