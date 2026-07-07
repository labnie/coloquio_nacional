#!/usr/bin/env python3
"""
Integra las respuestas del Google Form (exportadas como CSV desde la Google
Sheet) al mapa de experiencias radiales.

USO:
    1. En la Google Sheet de respuestas: Archivo > Descargar > Valores separados por comas (.csv)
    2. Guarda ese archivo como "respuestas_formulario.csv" en esta misma carpeta.
    3. Corre:  python3 actualizar_desde_formulario.py
    4. Revisa el resumen que imprime (nuevas, actualizadas, claves no encontradas).
    5. Si todo se ve bien, sube (git push) los cambios en data/Experiencias_radiales_DGESUM_2.js

El formulario debe tener estas preguntas (los nombres de columna deben
coincidir; ajusta CSV_COLUMNS abajo si tu formulario usa otros títulos):

    - Clave_DGES        (la clave de su escuela; ver catalogo_escuelas.csv)
    - Nombre_programa   (nombre del programa/podcast de radio)
    - Contacto          (nombre de quien reporta)
    - Correo_e          (correo de contacto, opcional)
    - Enlaces           (uno o varios enlaces separados por " | ",
                          ej: "Spotify: https://... | YouTube: https://...")

Reglas:
    - Si la Clave_DGES ya tiene una experiencia registrada, se AGREGA el nuevo
      programa/contacto/enlaces a lo que ya existía (sin borrar lo anterior).
    - Si la Clave_DGES no tiene experiencia registrada todavía pero SÍ existe
      en el catálogo de escuelas (259 normales), se crea un punto NUEVO en el
      mapa usando la ubicación real de esa escuela.
    - Si la Clave_DGES no se encuentra en el catálogo, la respuesta se
      IGNORA y se reporta al final para que la revises a mano (posible
      error de captura).
"""
import json
import csv
import sys
from pathlib import Path
from collections import OrderedDict

CSV_COLUMNS = {
    "clave": "Clave_DGES",
    "programa": "Nombre_programa",
    "contacto": "Contacto",
    "correo": "Correo_e",
    "enlaces": "Enlaces",
}

RESPONSES_PATH = Path("respuestas_formulario.csv")
BASE_PATH = Path("data/NormalesdeMxico_1.js")
RADIO_PATH = Path("data/Experiencias_radiales_DGESUM_2.js")


def norm(k):
    return (k or "").strip().rstrip(".").lower()


def load_geojson_var(path):
    content = path.read_text(encoding="utf-8")
    prefix, json_str = content.split("=", 1)
    json_str = json_str.strip()
    had_semicolon = json_str.endswith(";")
    if had_semicolon:
        json_str = json_str[:-1]
    return prefix, json.loads(json_str), had_semicolon


def main():
    if not RESPONSES_PATH.exists():
        sys.exit(f"No encuentro {RESPONSES_PATH}. Exporta la Sheet de respuestas primero.")
    if not BASE_PATH.exists() or not RADIO_PATH.exists():
        sys.exit("No encuentro los archivos de datos del mapa. Corre esto desde la raíz del sitio.")

    base_prefix, base_data, _ = load_geojson_var(BASE_PATH)
    radio_prefix, radio_data, had_semicolon = load_geojson_var(RADIO_PATH)

    base_by_key = {}
    for feat in base_data["features"]:
        p = feat["properties"]
        base_by_key[norm(p["Clave_DGES"])] = {
            "municipio": p["municipio"],
            "localidad": p["localidad"],
            "Clave_DGES": p["Clave_DGES"],
            "Esc_norm_1": p["Esc_norm_1"],
            "Estado": p["Estado"],
            "coords": feat["geometry"]["coordinates"],
        }

    radio_by_key = {norm(f["properties"]["Clave_DGES"]): f for f in radio_data["features"]}

    nuevas, actualizadas, no_encontradas = 0, 0, []

    with open(RESPONSES_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clave_raw = row.get(CSV_COLUMNS["clave"], "").strip()
            key = norm(clave_raw)
            if not key:
                continue
            if key not in base_by_key:
                no_encontradas.append(clave_raw)
                continue

            programa = (row.get(CSV_COLUMNS["programa"], "") or "").strip()
            contacto = (row.get(CSV_COLUMNS["contacto"], "") or "").strip()
            correo = (row.get(CSV_COLUMNS["correo"], "") or "").strip()
            enlaces_raw = (row.get(CSV_COLUMNS["enlaces"], "") or "").strip()
            enlaces_nuevos = [e.strip() for e in enlaces_raw.split("|") if e.strip()]

            if key in radio_by_key:
                # actualizar existente
                props = radio_by_key[key]["properties"]

                progs = [p.strip() for p in (props.get("Pro_ radio") or "").split("|") if p.strip()]
                if programa and programa not in progs:
                    progs.append(programa)
                props["Pro_ radio"] = " | ".join(progs) if progs else None

                contactos = [c.strip() for c in (props.get("Contacto") or "").split("|") if c.strip()]
                if contacto and contacto not in contactos:
                    contactos.append(contacto)
                props["Contacto"] = " | ".join(contactos) if contactos else None

                if correo and not props.get("Correo-e"):
                    props["Correo-e"] = correo

                enlaces_actuales = [e.strip() for e in (props.get("Enlaces") or "").split(" <br> ") if e.strip()]
                for e in enlaces_nuevos:
                    if e not in enlaces_actuales:
                        enlaces_actuales.append(e)
                props["Enlaces"] = " <br> ".join(enlaces_actuales) if enlaces_actuales else None

                actualizadas += 1
            else:
                # crear nueva
                base = base_by_key[key]
                nueva_feature = {
                    "type": "Feature",
                    "properties": {
                        "municipio": base["municipio"],
                        "localidad": base["localidad"],
                        "Clave_DGES": base["Clave_DGES"],
                        "Esc_norm_1": base["Esc_norm_1"],
                        "Estado": base["Estado"],
                        "Pro_ radio": programa or None,
                        "Contacto": contacto or None,
                        "Correo-e": correo or None,
                        "Enlaces": " <br> ".join(enlaces_nuevos) if enlaces_nuevos else None,
                    },
                    "geometry": {"type": "Point", "coordinates": base["coords"]},
                }
                radio_data["features"].append(nueva_feature)
                radio_by_key[key] = nueva_feature
                nuevas += 1

    new_json_str = json.dumps(radio_data, ensure_ascii=False, separators=(",", ":"))
    new_content = radio_prefix + "= " + new_json_str + (";" if had_semicolon else "")
    RADIO_PATH.write_text(new_content, encoding="utf-8")

    print(f"Nuevas experiencias agregadas: {nuevas}")
    print(f"Experiencias existentes actualizadas: {actualizadas}")
    if no_encontradas:
        print(f"\nAVISO: {len(no_encontradas)} respuesta(s) con clave no encontrada en el catálogo (revisa a mano):")
        for c in no_encontradas:
            print("  -", c)
    print("\nListo. Revisa data/Experiencias_radiales_DGESUM_2.js antes de hacer git push.")


if __name__ == "__main__":
    main()
