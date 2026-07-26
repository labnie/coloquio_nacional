#!/usr/bin/env python3
"""
Descarga las respuestas de la Google Sheet de experiencias radiales
directamente por su API (sin necesidad de exportar el CSV a mano) y las
guarda como respuestas_formulario.csv, listo para actualizar_desde_formulario.py.

Se usa automáticamente desde GitHub Actions (ver
.github/workflows/actualizar_mapa.yml), pero también puedes correrlo tú
mismo en tu computadora si prefieres no depender del flujo automatizado.

REQUISITOS (una sola vez, ver README.md sección 6 para el paso a paso):
    1. Una cuenta de servicio de Google Cloud con la API de Google Sheets
       habilitada, y su archivo de credenciales en JSON.
    2. Haber compartido la Google Sheet de respuestas con el correo de esa
       cuenta de servicio (como lector, "Viewer").
    3. Dos variables de entorno al ejecutar este script:
       - GOOGLE_SERVICE_ACCOUNT_JSON: el contenido completo del archivo de
         credenciales (como texto/JSON), no la ruta a un archivo.
       - SHEET_ID: el ID de la Google Sheet (la parte de la URL entre
         /d/ y /edit, ej: https://docs.google.com/spreadsheets/d/ESTE_ID/edit).

Instalar dependencias:
    pip install gspread google-auth --break-system-packages
"""
import csv
import json
import os
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    sys.exit(
        "Faltan dependencias. Instala con:\n"
        "    pip install gspread google-auth --break-system-packages"
    )

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
OUTPUT_PATH = "respuestas_formulario.csv"


def main():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.environ.get("SHEET_ID")

    if not creds_json:
        sys.exit("Falta la variable de entorno GOOGLE_SERVICE_ACCOUNT_JSON.")
    if not sheet_id:
        sys.exit("Falta la variable de entorno SHEET_ID.")

    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError:
        sys.exit("GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON válido.")

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    try:
        sheet = client.open_by_key(sheet_id).sheet1
    except gspread.exceptions.APIError as e:
        sys.exit(f"No se pudo abrir la Google Sheet. ¿Está compartida con la cuenta de servicio? Detalle: {e}")

    rows = sheet.get_all_records()

    if not rows:
        print("La Google Sheet no tiene respuestas todavía. No se generó ningún archivo.")
        # Aun así, escribe un CSV vacío con encabezados para que el resto del
        # flujo no falle por falta de archivo.
        rows = []

    fieldnames = list(rows[0].keys()) if rows else [
        "Fecha", "Clave_DGES", "Escuela", "Estado", "Programa", "Contacto", "Correo", "Enlaces", "Tipo"
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Listo. {len(rows)} fila(s) descargada(s) de la Google Sheet a {OUTPUT_PATH}.")


if __name__ == "__main__":
    main()
