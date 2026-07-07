#!/usr/bin/env python3
"""
Actualiza los datos embebidos dentro de mapa_experiencias_radiales.html a
partir de los archivos data/NormalesdeMxico_1.js y
data/Experiencias_radiales_DGESUM_2.js.

Úsalo después de correr actualizar_desde_formulario.py (o de editar los
archivos de datos de cualquier otra forma), para que el mapa autónomo
refleje la información más reciente.

Uso:
    python3 regenerar_mapa.py
"""
import json
import re
import sys
from pathlib import Path

BASE_PATH = Path("data/NormalesdeMxico_1.js")
RADIO_PATH = Path("data/Experiencias_radiales_DGESUM_2.js")
MAPA_PATH = Path("mapa_experiencias_radiales.html")


def load_geojson_var(path):
    content = path.read_text(encoding="utf-8")
    _, json_str = content.split("=", 1)
    json_str = json_str.strip()
    if json_str.endswith(";"):
        json_str = json_str[:-1]
    return json.loads(json_str)


def main():
    for p in (BASE_PATH, RADIO_PATH, MAPA_PATH):
        if not p.exists():
            sys.exit(f"No encuentro {p}. Ejecuta esto desde la raíz del sitio.")

    base_data = load_geojson_var(BASE_PATH)
    radio_data = load_geojson_var(RADIO_PATH)

    base_json = json.dumps(base_data, ensure_ascii=False, separators=(",", ":"))
    radio_json = json.dumps(radio_data, ensure_ascii=False, separators=(",", ":"))

    html = MAPA_PATH.read_text(encoding="utf-8")

    html, n1 = re.subn(
        r"const baseData = \{.*?\};(?=\s*\n)",
        "const baseData = " + base_json.replace("\\", "\\\\") + ";",
        html,
        count=1,
        flags=re.DOTALL,
    )
    html, n2 = re.subn(
        r"const radioData = \{.*?\};(?=\s*\n)",
        "const radioData = " + radio_json.replace("\\", "\\\\") + ";",
        html,
        count=1,
        flags=re.DOTALL,
    )

    if n1 == 0 or n2 == 0:
        sys.exit(
            "No pude encontrar los bloques de datos dentro del HTML "
            "(baseData / radioData). Revisa que no se haya modificado "
            "esa parte del archivo manualmente."
        )

    MAPA_PATH.write_text(html, encoding="utf-8")
    print(f"Listo. Mapa actualizado con {len(base_data['features'])} escuelas "
          f"y {len(radio_data['features'])} experiencias radiales.")


if __name__ == "__main__":
    main()
