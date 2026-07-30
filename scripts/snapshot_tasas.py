#!/usr/bin/env python3
"""
Mantiene al dia historial/tasas.json: las tasas libres de riesgo con las que
index.html calcula Sharpe y Sortino.

Dos series, mismo formato: una lista ordenada de pares [fecha, TNA en %],
donde cada tasa rige desde su fecha hasta el par siguiente.

  ars -> tasa de pesos a 1 dia.
         Primaria: RIX del BCRA (variable 150, "pases entre terceros a 1 dia"),
         que es el promedio ponderado por monto de la rueda REPO del MAE.
         Relleno: cierre de la caucion a 1 dia en pesos de BYMA, SOLO para las
         ruedas que el BCRA todavia no publico. El BCRA publica con uno o dos
         dias de atraso, asi que sin este relleno los ultimos dias del periodo
         quedarian siempre sin tasa. Cuando el BCRA publica esa fecha, la RIX
         pisa al relleno: es promedio ponderado y no un precio suelto.

  usd -> Fed Funds, limite inferior del rango objetivo (DFEDTARL en FRED).
         Cambia un punado de veces por ano; el script solo agrega un escalon
         nuevo cuando el valor efectivamente cambio.

Pensado para correr en el mismo GitHub Action que el snapshot de precios.
Es defensivo a proposito: si una fuente falla, deja la serie como estaba y
sigue con la otra. Solo escribe el archivo si algo cambio de verdad.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVO = REPO_ROOT / "historial" / "tasas.json"

BCRA_RIX = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/150"
BYMA_CAUCIONES = ("https://open.bymadata.com.ar/vanoms-be-core/rest/api/"
                  "bymadata/free/cauciones")
FRED_DFEDTARL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARL"

UA = {"User-Agent": "Mozilla/5.0"}
# Cuantos dias hacia atras se le vuelven a pedir al BCRA en cada corrida. Es
# barato y cubre el caso de que el BCRA publique o corrija una fecha vieja.
DIAS_REVISION = 45


def hoy_ars():
    return (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d")


def get_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers=dict(UA))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def traer_rix(desde, hasta):
    """{fecha: tasa} de la RIX del BCRA. Devuelve {} si la fuente falla."""
    try:
        d = get_json(f"{BCRA_RIX}?desde={desde}&hasta={hasta}&limit=3000")
        det = d["results"][0]["detalle"]
        return {x["fecha"]: round(float(x["valor"]), 2) for x in det
                if isinstance(x.get("valor"), (int, float))}
    except Exception as e:
        print(f"AVISO: no se pudo traer la RIX del BCRA: {e}")
        return {}


def traer_caucion(hoy):
    """
    Caucion en pesos del plazo mas corto que haya operado, en TNA %.

    Se usa el vwap (promedio ponderado por monto) y no el ultimo precio: en la
    caucion el ultimo print del dia suele estar varios puntos arriba del resto
    de la rueda, asi que tomarlo sesgaria la tasa hacia arriba.

    El endpoint no dice a que fecha corresponde lo que devuelve, y en un feriado
    puede contestar con la rueda anterior. Por eso se exige que el contrato
    elegido venza DESPUES de hoy: si vence hoy o antes, el dato es viejo y se
    descarta en vez de guardarlo con la fecha equivocada.
    """
    try:
        filas = get_json(BYMA_CAUCIONES, data=b"{}")
    except Exception as e:
        print(f"AVISO: no se pudo traer la caucion de BYMA: {e}")
        return None
    cand = []
    for x in filas:
        if not str(x.get("symbol", "")).startswith("PESOS-"):
            continue
        if not (x.get("tradeVolume", 0) > 0 and x.get("vwap", 0) > 0):
            continue
        venc = str(x.get("maturityDate", ""))
        if not venc or venc <= hoy:
            continue
        cand.append((x.get("daysToMaturity", 999), venc, x["vwap"], x["symbol"]))
    if not cand:
        print("AVISO: BYMA no devolvio ninguna caucion en pesos con volumen y "
              "vencimiento futuro (feriado, o rueda sin operar)")
        return None
    cand.sort()
    _, _, vwap, sym = cand[0]
    tasa = round(vwap * 100, 2)
    print(f"  caucion BYMA {sym}: {tasa}% TNA")
    return tasa


def traer_fed_funds():
    """
    Escalon vigente de DFEDTARL como (fecha_en_que_empezo_a_regir, valor).
    None si la fuente falla.

    No alcanza con mirar el ultimo valor: si se mira solo eso, el escalon queda
    fechado el dia en que el script lo detecto y no el dia en que entro en
    vigencia, y basta con que el Action se saltee las corridas de una semana
    para que queden varios dias calculados con la tasa anterior. Por eso se
    retrocede por la serie mientras el valor sea el mismo: el primer dia de esa
    meseta es la fecha efectiva real, la corrida en que se detecte.

    Los headers no son decorativos: con solo User-Agent, FRED acepta la
    conexion y despues nunca manda el cuerpo (la lectura se cuelga hasta el
    timeout). Con Accept y Connection: close responde en decimas de segundo.
    Probado.
    """
    headers = dict(UA, Accept="text/csv,*/*", Connection="close")
    try:
        req = urllib.request.Request(FRED_DFEDTARL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            lineas = r.read().decode("utf-8").strip().splitlines()
    except Exception as e:
        print(f"AVISO: no se pudo traer DFEDTARL de FRED: {e}")
        return None
    obs = []
    for linea in lineas[1:]:
        fecha, _, valor = linea.partition(",")
        try:
            obs.append((fecha.strip(), round(float(valor), 4)))
        except ValueError:
            continue   # "." = dato no disponible
    if not obs:
        return None
    valor = obs[-1][1]
    i = len(obs) - 1
    while i > 0 and obs[i - 1][1] == valor:
        i -= 1
    return obs[i][0], valor


def main():
    if not ARCHIVO.exists():
        print(f"ERROR: falta {ARCHIVO}. Este script actualiza el archivo, no lo "
              f"crea de cero (la serie historica se cargo a mano).")
        return
    doc = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    hoy = hoy_ars()
    cambios = []

    # ── ARS ───────────────────────────────────────────────────────────────
    ars = doc.setdefault("ars", {})
    serie = {f: v for f, v in ars.get("pasos", [])}
    relleno = set(ars.get("relleno", []))

    desde = (datetime.strptime(hoy, "%Y-%m-%d")
             - timedelta(days=DIAS_REVISION)).strftime("%Y-%m-%d")
    rix = traer_rix(desde, hoy)
    print(f"  RIX del BCRA: {len(rix)} ruedas entre {desde} y {hoy}")
    for f, v in rix.items():
        # La RIX manda siempre: si esa fecha la habia puesto la caucion, la pisa.
        if serie.get(f) != v or f in relleno:
            if f in relleno:
                relleno.discard(f)
                cambios.append(f"{f}: caucion -> RIX {v}%")
            else:
                cambios.append(f"{f}: RIX {v}%")
            serie[f] = v

    if hoy not in serie:
        # El BCRA todavia no publico hoy: se tapa el agujero con la caucion.
        cau = traer_caucion(hoy)
        if cau is not None:
            serie[hoy] = cau
            relleno.add(hoy)
            cambios.append(f"{hoy}: caucion {cau}% (relleno, sin RIX todavia)")

    if cambios:
        ars["pasos"] = [[f, serie[f]] for f in sorted(serie)]
        ars["relleno"] = sorted(relleno)

    # ── USD ───────────────────────────────────────────────────────────────
    usd = doc.setdefault("usd", {})
    pasos_usd = usd.get("pasos", [])
    ff = traer_fed_funds()
    if ff and pasos_usd:
        fecha_ff, valor_ff = ff
        if valor_ff != pasos_usd[-1][1] and fecha_ff > pasos_usd[-1][0]:
            pasos_usd.append([fecha_ff, valor_ff])
            usd["pasos"] = pasos_usd
            cambios.append(f"Fed Funds: nuevo escalon {fecha_ff} = {valor_ff}%")

    # ── escritura ─────────────────────────────────────────────────────────
    if not cambios:
        print("Sin novedades: no se escribe nada.")
        return
    doc["actualizado"] = hoy
    texto = (json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
             .replace('],"', '],\n"').replace('},"', '},\n"'))
    ARCHIVO.write_text(texto, encoding="utf-8")
    print(f"\nOK - {len(cambios)} cambio(s), {len(doc['ars']['pasos'])} ruedas en "
          f"pesos, {len(doc['usd']['pasos'])} escalones en dolares "
          f"({ARCHIVO.stat().st_size / 1024:.0f} KB)")
    for c in cambios[-8:]:
        print(f"  {c}")


if __name__ == "__main__":
    main()
