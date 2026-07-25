#!/usr/bin/env python3
"""
Snapshot diario de precios de TODO el universo de bonos, letras, acciones y
CEDEARs de BYMA (se excluyen ONs por ahora, para no sobrecargar el archivo).

Guarda el precio de cada especie, cada dia - no solo un punado de benchmarks.
La idea: este archivo es 100% informacion publica de mercado (no dice nada
sobre que tiene cualquier persona en su cartera). El dashboard, corriendo en
el navegador del usuario, cruza esto contra sus propios movimientos privados
(que viven en su gist) para reconstruir el valor historico de SU cartera y
compararlo contra estos mismos benchmarks - sin que ese cruce quede expuesto
en ningun lado publico.

Pensado para correr como GitHub Action despues del cierre de BYMA.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paneles a archivar. "on" (Obligaciones Negociables) queda afuera a proposito:
# son ~600 especies mas y no se usan para los benchmarks de referencia.
PANEL_URL = {
    "bono":   "https://data912.com/live/arg_bonds",
    "letra":  "https://data912.com/live/arg_notes",
    "accion": "https://data912.com/live/arg_stocks",
    "cedear": "https://data912.com/live/arg_cedears",
}

REPO_ROOT = Path(__file__).resolve().parent.parent
HIST_DIR = REPO_ROOT / "historial"


def fetch_panel(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    out = {}
    for row in data:
        c = row.get("c")
        if isinstance(c, (int, float)) and c > 0:
            out[row["symbol"]] = c
    return out


def main():
    snapshot = {}
    total = 0
    for panel_id, url in PANEL_URL.items():
        try:
            panel = fetch_panel(url)
            snapshot[panel_id] = panel
            total += len(panel)
            print(f"  {panel_id:8} {len(panel)} especies con precio")
        except Exception as e:
            print(f"AVISO: no se pudo traer el panel '{panel_id}': {e}")
            snapshot[panel_id] = {}

    if total == 0:
        print("ERROR: no se obtuvo ningun dato. No se escribe nada.")
        return

    hoy_ars = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d")
    anio = hoy_ars[:4]

    HIST_DIR.mkdir(exist_ok=True)
    archivo = HIST_DIR / f"{anio}.json"

    historial = {}
    if archivo.exists():
        historial = json.loads(archivo.read_text())

    historial[hoy_ars] = snapshot
    archivo.write_text(json.dumps(historial, separators=(",", ":")))

    kb = archivo.stat().st_size / 1024
    print(f"\nOK - snapshot del {hoy_ars} guardado en historial/{anio}.json "
          f"({total} especies - archivo del anio: {kb:.0f} KB - {len(historial)} dias acumulados)")


if __name__ == "__main__":
    main()
