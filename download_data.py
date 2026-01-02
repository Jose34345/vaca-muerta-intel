import requests
import os

def descargar_csv():
    # URL oficial de la Secretaría de Energía (Capítulo IV - Producción 2024 como ejemplo)
    # Nota: En 2026, cambiaremos el año al último disponible.
    url = "http://datos.energia.gob.ar/dataset/c5967a00-349c-493e-9097-f50f75990f1d/resource/2039e10f-2172-4d2b-a010-090956903271/download/produccin-de-pozos-de-gas-y-petrleo-2024.csv"
    
    archivo_destino = "produccion_vaca_muerta.csv"
    
    if not os.path.exists(archivo_destino):
        print("Descargando datos reales de la Secretaría de Energía... (puede tardar)")
        response = requests.get(url)
        with open(archivo_destino, 'wb') as f:
            f.write(response.content)
        print("Descarga completada.")
    else:
        print("El archivo ya existe localmente.")

if __name__ == "__main__":
    descargar_csv()