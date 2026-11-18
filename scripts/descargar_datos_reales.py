"""
scripts/descargar_datos_reales.py
Descarga datos REALES y arma el archivo que ImportPredic recibe en
"Carga de datos". No modifica la base de datos ni la configuración.

    python -m scripts.descargar_datos_reales

Fuentes (todas públicas y sin registro):
  - Importaciones mensuales por subpartida (kg netos y valor FOB en USD):
    UN Comtrade, con los datos que Colombia reporta a la ONU a través
    del DANE (reporterCode 170, socio = Mundo).
  - TRM: Superintendencia Financiera, en datos.gov.co (conjunto 32sa-8pi3).
  - Tasa de política monetaria: Banco de la República (servicio SDMX).
  - IPC e índice de producción industrial: Banco Mundial (Global Economic
    Monitor) y, como respaldo, OECD vía FRED.

Nota sobre la subpartida 2903.39: desde el 1 de enero de 2022 Colombia usa
la VII Enmienda del Sistema Armonizado (SA 2022), en la que la 2903.39 dejó
de existir y su contenido pasó a las subpartidas 2903.41 a 2903.69 (HFC,
HFO y derivados bromados o yodados). Para conservar una serie comparable,
desde 2022 se suman esas subpartidas.

Resultado en data/reales/:
  datos_reales_importpredic.csv   -> el que se sube a la app
  datos_reales_2015_2024.csv      -> mismo archivo recortado a 2015-2024
  importaciones_detalle.csv       -> una fila por mes y subpartida (auditoría)
  variables_macro.csv             -> variables macro con su fuente
  fuentes_y_registro.txt          -> qué fuente respondió y qué faltó
"""
import datetime as dt
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "reales"
OUT.mkdir(parents=True, exist_ok=True)

ANIO_INICIO = 2015
HOY = dt.date.today()
UA = {"User-Agent": "ImportPredic/2.0 (proyecto de grado UDI; python urllib)"}

PARTIDAS = {
    "8414.30": ["841430"],
    "2903.39": ["290339",  # SA 2012 / SA 2017
                "290341", "290342", "290343", "290344", "290345", "290346", "290347", "290348", "290349",
                "290351", "290359", "290361", "290369"],  # SA 2022 (desde 2022)
    "8537.10": ["853710"],
    "3926.90": ["392690"],
}
CODIGO_A_PARTIDA = {c: p for p, cs in PARTIDAS.items() for c in cs}

registro = []


def log(texto):
    print(texto, flush=True)
    registro.append(texto)


def http_get(url, params=None, accept=None, intentos=5, espera=4):
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params, safe=",:'$()")
    headers = dict(UA)
    if accept:
        headers["Accept"] = accept
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            ultimo = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(espera * (i + 1))
                continue
            raise
        except Exception as e:  # red caída, timeout
            ultimo = e
            time.sleep(espera * (i + 1))
    raise ultimo


# ---------------------------------------------------------------------------
# 1. Importaciones (UN Comtrade, datos reportados por el DANE)
# ---------------------------------------------------------------------------
COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/M/HS"


def _comtrade(periodos):
    params = {
        "reportercode": "170", "flowCode": "M", "period": ",".join(periodos),
        "cmdCode": ",".join(CODIGO_A_PARTIDA), "partnerCode": "0", "partner2Code": "0",
        "customsCode": "C00", "motCode": "0", "breakdownMode": "classic",
        "includeDesc": "false", "maxRecords": "500",
    }
    data = json.loads(http_get(COMTRADE, params).decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:200])
    return data.get("data") or []


def descargar_importaciones():
    log("\n[1/4] Importaciones mensuales (UN Comtrade / DANE)...")
    filas = []
    for anio in range(ANIO_INICIO, HOY.year + 1):
        periodos = [f"{anio}{m:02d}" for m in range(1, 13) if dt.date(anio, m, 1) <= HOY]
        try:
            filas += _comtrade(periodos)
        except Exception as e:  # algunos servidores limitan varios periodos por consulta
            log(f"   {anio}: consulta anual falló ({e}); se pide mes por mes")
            for p in periodos:
                try:
                    filas += _comtrade([p])
                except Exception as e2:
                    log(f"   {p}: sin respuesta ({e2})")
                time.sleep(1.5)
        meses = sorted({str(f.get("period")) for f in filas if str(f.get("period", "")).startswith(str(anio))})
        log(f"   {anio}: {len(meses)} mes(es) con datos")
        time.sleep(1.5)

    if not filas:
        raise RuntimeError("UN Comtrade no devolvió datos. Revisa tu conexión e inténtalo de nuevo en unos minutos.")

    df = pd.DataFrame(filas)
    for col, val in (("partnerCode", 0), ("partner2Code", 0), ("motCode", 0)):
        if col in df:
            df = df[df[col].isin([val, str(val)]) | df[col].isna()]
    if "customsCode" in df:
        df = df[df["customsCode"].isin(["C00"]) | df["customsCode"].isna()]
    if "flowCode" in df:
        df = df[df["flowCode"] == "M"]
    df["cmdCode"] = df["cmdCode"].astype(str)
    df = df[df["cmdCode"].isin(CODIGO_A_PARTIDA)]
    df = df.drop_duplicates(subset=["period", "cmdCode"])

    def num(col):
        return pd.to_numeric(df[col], errors="coerce") if col in df else pd.Series(float("nan"), index=df.index)

    kg = num("netWgt")
    qty, unidad = num("qty"), num("qtyUnitCode")
    kg = kg.where(kg > 0, qty.where(unidad == 8))
    fob = num("fobvalue")
    cif = num("cifvalue").where(num("cifvalue") > 0, num("primaryValue"))
    det = pd.DataFrame({
        "fecha": pd.to_datetime(df["period"].astype(str), format="%Y%m"),
        "subpartida_6d": df["cmdCode"],
        "partida_arancelaria": df["cmdCode"].map(CODIGO_A_PARTIDA),
        "clasificacion": df.get("classificationCode", pd.Series("", index=df.index)),
        "peso_neto_kg": kg, "valor_fob_usd": fob, "valor_cif_usd": cif,
    }).sort_values(["partida_arancelaria", "fecha", "subpartida_6d"])
    det.to_csv(OUT / "importaciones_detalle.csv", index=False)

    agg = det.groupby(["partida_arancelaria", "fecha"]).agg(
        volumen_importacion_kg=("peso_neto_kg", lambda s: s.sum(min_count=1)),
        valor_fob_usd=("valor_fob_usd", lambda s: s.sum(min_count=1)),
        valor_cif_usd=("valor_cif_usd", lambda s: s.sum(min_count=1)),
    ).reset_index()
    sin_fob = agg["valor_fob_usd"].isna() | (agg["valor_fob_usd"] <= 0)
    if sin_fob.any():
        log(f"   Aviso: {int(sin_fob.sum())} mes(es) sin valor FOB; se usó el valor CIF reportado")
        agg.loc[sin_fob, "valor_fob_usd"] = agg.loc[sin_fob, "valor_cif_usd"]
    return agg.drop(columns="valor_cif_usd")


# ---------------------------------------------------------------------------
# 2. Variables macroeconómicas
# ---------------------------------------------------------------------------
def _mensual(serie):
    serie = serie.dropna().sort_index()
    return serie.groupby(serie.index.to_period("M")).mean().rename_axis("mes")


def trm_superfinanciera():
    url = "https://www.datos.gov.co/resource/32sa-8pi3.json"
    params = {"$select": "valor,vigenciadesde,vigenciahasta",
              "$where": f"vigenciahasta >= '{ANIO_INICIO - 1}-12-01T00:00:00'",
              "$order": "vigenciadesde", "$limit": "50000"}
    d = pd.DataFrame(json.loads(http_get(url, params)))
    d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
    d["desde"] = pd.to_datetime(d["vigenciadesde"]).dt.normalize()
    d["hasta"] = pd.to_datetime(d["vigenciahasta"]).dt.normalize()
    dias = []
    for r in d.itertuples():  # la TRM rige todos los días calendario de su vigencia
        for f in pd.date_range(r.desde, r.hasta, freq="D"):
            dias.append((f, r.valor))
    s = pd.Series(dict(dias))
    return _mensual(s)


BANREP = "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data/ESTAT,{df},1.0/all/ALL/"


def banrep_sdmx(dataflow):
    xml = http_get(BANREP.format(df=dataflow), {"startPeriod": str(ANIO_INICIO - 1), "endPeriod": str(HOY.year + 1)},
                   accept="application/xml")
    raiz = ET.fromstring(xml)
    obs = {}
    for o in raiz.iter():
        if not o.tag.endswith("}Obs"):
            continue
        fecha = valor = None
        for h in o:
            if h.tag.endswith("ObsDimension"):
                fecha = h.get("value")
            elif h.tag.endswith("ObsValue"):
                valor = h.get("value")
        if fecha and valor not in (None, "", "NaN"):
            f = fecha.replace("-", "")
            obs[pd.to_datetime(f[:8] if len(f) >= 8 else f + "01", format="%Y%m%d")] = float(valor.replace(",", "."))
    if not obs:
        raise RuntimeError("respuesta sin observaciones")
    return _mensual(pd.Series(obs))


def banco_mundial_gem(indicador):
    url = f"https://api.worldbank.org/v2/country/COL/indicator/{indicador}"
    params = {"source": "15", "format": "json", "frequency": "M",
              "date": f"{ANIO_INICIO - 1}M01:{HOY.year}M12", "per_page": "2000"}
    data = json.loads(http_get(url, params).decode("utf-8"))
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        raise RuntimeError(str(data)[:200])
    s = {pd.to_datetime(x["date"].replace("M", "-") + "-01"): x["value"] for x in data[1] if x.get("value") is not None}
    if not s:
        raise RuntimeError("serie vacía")
    return _mensual(pd.Series(s, dtype=float))


def fred(serie):
    raw = http_get("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": serie, "cosd": f"{ANIO_INICIO - 1}-01-01"})
    d = pd.read_csv(io.BytesIO(raw))
    d.columns = ["fecha", "valor"]
    d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
    return _mensual(pd.Series(d["valor"].values, index=pd.to_datetime(d["fecha"])))


def primera_que_funcione(nombre, opciones):
    for etiqueta, funcion in opciones:
        try:
            s = funcion()
            log(f"   {nombre}: {etiqueta} -> {s.index.min()} a {s.index.max()} ({len(s)} meses)")
            return s, etiqueta
        except Exception as e:
            log(f"   {nombre}: {etiqueta} no respondió ({str(e)[:120]})")
    return None, "sin fuente"


def descargar_macro():
    log("\n[2/4] Variables macroeconómicas...")
    trm, f_trm = primera_que_funcione("TRM", [
        ("Superfinanciera (datos.gov.co)", trm_superfinanciera),
        ("Banco de la República (SDMX)", lambda: banrep_sdmx("DF_TRM_DAILY_HIST")),
    ])
    tasa, f_tasa = primera_que_funcione("Tasa de política", [
        ("Banco de la República (SDMX)", lambda: banrep_sdmx("DF_CBR_DAILY_HIST")),
        ("OECD vía FRED, tasa interbancaria", lambda: fred("COLIRSTCI01STM")),
    ])
    ipc_var, f_ipc = None, "sin fuente"
    ipc_idx, f_idx = primera_que_funcione("IPC (índice)", [
        ("Banco Mundial GEM (CPTOTNSXN)", lambda: banco_mundial_gem("CPTOTNSXN")),
    ])
    if ipc_idx is not None:
        ipc_var, f_ipc = (ipc_idx.pct_change() * 100).dropna(), f_idx + ", variación mensual calculada"
    if ipc_var is None or ipc_var.index.max() < pd.Period(f"{HOY.year - 1}-01", "M"):
        alt, f_alt = primera_que_funcione("IPC (variación)", [("OECD vía FRED (COLCPALTT01GPM)", lambda: fred("COLCPALTT01GPM"))])
        if alt is not None and (ipc_var is None or alt.index.max() > ipc_var.index.max()):
            ipc_var, f_ipc = alt, f_alt
    ipi, f_ipi = primera_que_funcione("Producción industrial", [
        ("Banco Mundial GEM (IPTOTNSKD)", lambda: banco_mundial_gem("IPTOTNSKD")),
        ("Banco Mundial GEM (IPTOTSAKD)", lambda: banco_mundial_gem("IPTOTSAKD")),
        ("OECD vía FRED (COLPRMNTO01IXOBM)", lambda: fred("COLPRMNTO01IXOBM")),
    ])
    if ipi is not None:  # índice base 2015 = 100 para que sea legible
        base = ipi[(ipi.index >= pd.Period("2015-01", "M")) & (ipi.index <= pd.Period("2015-12", "M"))].mean()
        if base and base == base:
            ipi = ipi / base * 100

    macro = pd.DataFrame({
        "trm_peso_dolar": trm, "ipc_variacion_mensual": ipc_var,
        "tasa_interes_referencia": tasa, "ipi_manufacturero": ipi,
    })
    macro.index = macro.index.to_timestamp()
    macro = macro.rename_axis("fecha").reset_index()
    fuentes = {"trm_peso_dolar": f_trm, "ipc_variacion_mensual": f_ipc,
               "tasa_interes_referencia": f_tasa, "ipi_manufacturero": f_ipi}
    return macro, fuentes


# ---------------------------------------------------------------------------
def main():
    print("=" * 66)
    print(" DESCARGA DE DATOS REALES - ImportPredic")
    print("=" * 66)
    imp = descargar_importaciones()
    macro, fuentes = descargar_macro()

    log("\n[3/4] Uniendo y revisando...")
    ultimo = imp.groupby("partida_arancelaria")["fecha"].max().min()  # último mes con las 4 partidas
    meses = pd.date_range(f"{ANIO_INICIO}-01-01", ultimo, freq="MS")
    base = pd.MultiIndex.from_product([sorted(PARTIDAS), meses], names=["partida_arancelaria", "fecha"]).to_frame(index=False)
    df = base.merge(imp, on=["partida_arancelaria", "fecha"], how="left").merge(macro, on="fecha", how="left")
    macro_cols = list(fuentes)
    df = df.sort_values(["partida_arancelaria", "fecha"])
    faltan_macro = {c: int(df.drop_duplicates("fecha")[c].isna().sum()) for c in macro_cols}
    df[macro_cols] = df.groupby("partida_arancelaria")[macro_cols].transform(lambda s: s.ffill().bfill())
    cols = ["fecha", "partida_arancelaria", "volumen_importacion_kg", "valor_fob_usd"] + macro_cols
    df = df[cols]
    df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
    for c in cols[2:]:
        df[c] = pd.to_numeric(df[c], errors="coerce").round(4 if c == "ipc_variacion_mensual" else 2)

    df.to_csv(OUT / "datos_reales_importpredic.csv", index=False)
    df[df["fecha"] <= "2024-12-31"].to_csv(OUT / "datos_reales_2015_2024.csv", index=False)
    macro.to_csv(OUT / "variables_macro.csv", index=False)

    log("\n[4/4] Resumen")
    log(f"   Periodo: {meses.min():%Y-%m} a {meses.max():%Y-%m} ({len(meses)} meses)")
    for p, g in df.groupby("partida_arancelaria"):
        vacios = int(g["volumen_importacion_kg"].isna().sum())
        log(f"   {p}: promedio {g['volumen_importacion_kg'].mean():,.0f} kg/mes; meses sin dato: {vacios}")
    for c, f in fuentes.items():
        extra = f" (meses rellenados con el valor anterior: {faltan_macro[c]})" if faltan_macro[c] else ""
        log(f"   {c}: {f}{extra}")
    (OUT / "fuentes_y_registro.txt").write_text("\n".join(registro), encoding="utf-8")
    print("\n" + "=" * 66)
    print(" Listo. Archivo para subir a ImportPredic:")
    print(f"   {OUT / 'datos_reales_2015_2024.csv'}")
    print(" (y la versión con todos los meses disponibles: datos_reales_importpredic.csv)")
    print("=" * 66)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        (OUT / "fuentes_y_registro.txt").write_text("\n".join(registro + [f"ERROR: {e}"]), encoding="utf-8")
        print(f"\nERROR: {e}")
        sys.exit(1)
