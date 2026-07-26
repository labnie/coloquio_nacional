#!/usr/bin/env python3
"""
Integra las respuestas del formulario (formulario_registro.html, vía
Apps Script) al mapa de experiencias radiales.

USO MANUAL:
    1. En la Google Sheet de respuestas: Archivo > Descargar > Valores separados por comas (.csv)
    2. Guarda ese archivo como "respuestas_formulario.csv" en esta misma carpeta.
    3. Corre:  python3 actualizar_desde_formulario.py
    4. Revisa el resumen que imprime (nuevas, actualizadas, claves no encontradas).
    5. Corre regenerar_mapa.py y sube los cambios.

USO AUTOMATIZADO:
    Este script también se ejecuta automáticamente desde el flujo de GitHub
    Actions (.github/workflows/actualizar_mapa.yml), que descarga las
    respuestas directamente de la Google Sheet por su API y abre un Pull
    Request con los cambios para tu revisión — ver README.md, sección 6.

El formulario/Apps Script genera estas columnas en la Google Sheet (los
nombres deben coincidir con CSV_COLUMNS abajo si algo cambia):

    - Clave_DGES   (la clave de la escuela; vacía si Tipo=direccion_estatal)
    - Escuela      (nombre de la escuela, o el área/institución escrita a
                     mano cuando Tipo=direccion_estatal)
    - Estado
    - Programa     (nombre del/los programa(s) de radio, puede venir
                     unido con " | " si se reportó más de uno)
    - Contacto     (nombre de quien reporta)
    - Correo       (correo de contacto, opcional)
    - Enlaces      (uno o varios enlaces separados por " | ",
                     ej: "Spotify: https://... | YouTube: https://...")
    - Tipo         ("escuela" o "direccion_estatal" — si la columna no
                     existe todavía en tu Sheet, se trata como "escuela")

Reglas para Tipo=escuela (el caso normal):
    - Si la Clave_DGES ya tiene una experiencia registrada, se AGREGA el nuevo
      programa/contacto/enlaces a lo que ya existía (sin borrar nada).
    - Si la Clave_DGES no tiene experiencia registrada todavía pero SÍ existe
      en el catálogo de escuelas, se crea un punto NUEVO usando la ubicación
      real de esa escuela.
    - Si la Clave_DGES no se encuentra en el catálogo, la respuesta se
      IGNORA y se reporta al final para que la revises a mano (posible
      error de captura).

Reglas para Tipo=direccion_estatal (experiencias que no son de una escuela
específica, ej. la Dirección de Educación Normal de un estado):
    - Se usa una clave sintética "dir-<estado>" (una por estado).
    - El punto se ubica en el centro aproximado del estado, calculado
      automáticamente promediando las coordenadas de las escuelas de ese
      estado — no requiere geocodificar nada a mano.
    - Si ya existe un registro de Dirección Estatal para ese estado, el
      nuevo programa/contacto/enlaces se agregan al existente (mismo punto),
      igual que con las escuelas.
"""
import json
import csv
import re
import sys
import unicodedata
from pathlib import Path

CSV_COLUMNS = {
    "clave": "Clave_DGES",
    "escuela": "Escuela",
    "estado": "Estado",
    "programa": "Programa",
    "contacto": "Contacto",
    "correo": "Correo",
    "enlaces": "Enlaces",
    "tipo": "Tipo",
}

RESPONSES_PATH = Path("respuestas_formulario.csv")
BASE_PATH = Path("data/NormalesdeMxico_1.js")
RADIO_PATH = Path("data/Experiencias_radiales_DGESUM_2.js")


def norm(k):
    return (k or "").strip().rstrip(".").lower()


def slugify_estado(estado):
    """Convierte 'Baja California Sur' en 'dir-baja-california-sur'."""
    s = unicodedata.normalize("NFKD", estado or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return f"dir-{s}"


def load_geojson_var(path):
    content = path.read_text(encoding="utf-8")
    prefix, json_str = content.split("=", 1)
    json_str = json_str.strip()
    had_semicolon = json_str.endswith(";")
    if had_semicolon:
        json_str = json_str[:-1]
    return prefix, json.loads(json_str), had_semicolon


def calcular_centroides_por_estado(base_data):
    """Promedia las coordenadas de las escuelas de cada estado, para poder
    ubicar experiencias de Dirección Estatal sin geocodificar a mano."""
    sumas = {}
    for feat in base_data["features"]:
        estado = feat["properties"].get("Estado") or "Sin estado"
        lon, lat = feat["geometry"]["coordinates"]
        if estado not in sumas:
            sumas[estado] = [0.0, 0.0, 0]
        sumas[estado][0] += lon
        sumas[estado][1] += lat
        sumas[estado][2] += 1
    return {
        estado: (lon_sum / n, lat_sum / n)
        for estado, (lon_sum, lat_sum, n) in sumas.items()
        if n > 0
    }


def merge_listas(actual, nuevo_valor, separador="|"):
    items = [x.strip() for x in (actual or "").split(separador) if x.strip()]
    if nuevo_valor and nuevo_valor not in items:
        items.append(nuevo_valor)
    return f" {separador} ".join(items) if items else None


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

    centroides = calcular_centroides_por_estado(base_data)
    radio_by_key = {norm(f["properties"]["Clave_DGES"]): f for f in radio_data["features"]}

    nuevas, actualizadas, no_encontradas = 0, 0, []
    nuevas_direccion_estatal = 0

    with open(RESPONSES_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tipo = (row.get(CSV_COLUMNS["tipo"], "") or "escuela").strip().lower()
            programa = (row.get(CSV_COLUMNS["programa"], "") or "").strip()
            contacto = (row.get(CSV_COLUMNS["contacto"], "") or "").strip()
            correo = (row.get(CSV_COLUMNS["correo"], "") or "").strip()
            enlaces_raw = (row.get(CSV_COLUMNS["enlaces"], "") or "").strip()
            enlaces_nuevos = [e.strip() for e in enlaces_raw.split("|") if e.strip()]

            # ---------- Caso: Dirección Estatal / área sin escuela específica ----------
            if tipo == "direccion_estatal":
                estado = (row.get(CSV_COLUMNS["estado"], "") or "").strip()
                institucion = (row.get(CSV_COLUMNS["escuela"], "") or "").strip()
                if not estado:
                    no_encontradas.append("(sin estado) " + institucion)
                    continue
                if estado not in centroides:
                    no_encontradas.append(f"(estado '{estado}' sin escuelas de referencia para calcular el centro)")
                    continue

                key = norm(slugify_estado(estado))
                lon, lat = centroides[estado]

                if key in radio_by_key:
                    props = radio_by_key[key]["properties"]
                    props["Pro_ radio"] = merge_listas(props.get("Pro_ radio"), programa)
                    props["Contacto"] = merge_listas(props.get("Contacto"), contacto)
                    if correo and not props.get("Correo-e"):
                        props["Correo-e"] = correo
                    enlaces_actuales = [e.strip() for e in (props.get("Enlaces") or "").split(" <br> ") if e.strip()]
                    for e in enlaces_nuevos:
                        if e not in enlaces_actuales:
                            enlaces_actuales.append(e)
                    props["Enlaces"] = " <br> ".join(enlaces_actuales) if enlaces_actuales else None
                    if institucion:
                        props["Esc_norm_1"] = institucion
                    actualizadas += 1
                else:
                    nueva_feature = {
                        "type": "Feature",
                        "properties": {
                            "municipio": None,
                            "localidad": "Dirección Estatal",
                            "Clave_DGES": slugify_estado(estado),
                            "Esc_norm_1": institucion or f"Dirección de Educación Normal de {estado}",
                            "Estado": estado,
                            "Pro_ radio": programa or None,
                            "Contacto": contacto or None,
                            "Correo-e": correo or None,
                            "Enlaces": " <br> ".join(enlaces_nuevos) if enlaces_nuevos else None,
                        },
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    }
                    radio_data["features"].append(nueva_feature)
                    radio_by_key[key] = nueva_feature
                    nuevas += 1
                    nuevas_direccion_estatal += 1
                continue

            # ---------- Caso normal: escuela específica ----------
            clave_raw = row.get(CSV_COLUMNS["clave"], "").strip()
            key = norm(clave_raw)
            if not key:
                continue
            if key not in base_by_key:
                no_encontradas.append(clave_raw)
                continue

            if key in radio_by_key:
                props = radio_by_key[key]["properties"]
                props["Pro_ radio"] = merge_listas(props.get("Pro_ radio"), programa)
                props["Contacto"] = merge_listas(props.get("Contacto"), contacto)
                if correo and not props.get("Correo-e"):
                    props["Correo-e"] = correo
                enlaces_actuales = [e.strip() for e in (props.get("Enlaces") or "").split(" <br> ") if e.strip()]
                for e in enlaces_nuevos:
                    if e not in enlaces_actuales:
                        enlaces_actuales.append(e)
                props["Enlaces"] = " <br> ".join(enlaces_actuales) if enlaces_actuales else None
                actualizadas += 1
            else:
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

    print(f"Nuevas experiencias agregadas: {nuevas} (de las cuales {nuevas_direccion_estatal} son de Dirección Estatal)")
    print(f"Experiencias existentes actualizadas: {actualizadas}")
    if no_encontradas:
        print(f"\nAVISO: {len(no_encontradas)} respuesta(s) no se pudieron ubicar (revisa a mano):")
        for c in no_encontradas:
            print("  -", c)
    print("\nListo. Revisa data/Experiencias_radiales_DGESUM_2.js antes de hacer git push.")

    # Resumen legible para usarse como cuerpo de un Pull Request automatizado
    resumen_lines = [
        "### Resumen de la actualización",
        "",
        f"- **Nuevas experiencias agregadas:** {nuevas} (de las cuales {nuevas_direccion_estatal} de Dirección Estatal)",
        f"- **Experiencias existentes actualizadas:** {actualizadas}",
    ]
    if no_encontradas:
        resumen_lines.append(f"- **Respuestas no ubicadas ({len(no_encontradas)}):** revisar a mano")
        resumen_lines.extend(f"  - `{c}`" for c in no_encontradas)
    else:
        resumen_lines.append("- **Respuestas no ubicadas:** ninguna")
    Path("resumen_actualizacion.md").write_text("\n".join(resumen_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
