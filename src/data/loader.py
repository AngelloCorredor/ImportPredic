"""
src/data/loader.py
Carga y validación básica de archivos CSV/Excel subidos por el usuario.

FIX v1.3.1: Excel convierte automáticamente códigos como "8414.30" a
float (8414.3), perdiendo el cero final y rompiendo el filtro por
partida arancelaria (0 filas procesadas). Se normaliza la columna
partida_arancelaria a texto con 2 decimales sin importar el tipo
con el que haya llegado desde el archivo.
"""
import pandas as pd


REQUIRED_COLUMNS = [
    "fecha", "partida_arancelaria", "volumen_importacion_kg", "valor_fob_usd",
    "trm_peso_dolar", "ipc_variacion_mensual", "tasa_interes_referencia", "ipi_manufacturero",
]


def _normalizar_partida_arancelaria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza la columna partida_arancelaria a texto con formato consistente.

    Excel/pandas frecuentemente convierte códigos tipo "8414.30" a float
    (8414.3), perdiendo el cero final. Esto rompe cualquier filtro que
    compare contra los códigos oficiales definidos en config/settings.py
    (INSUMOS_CRITICOS), ya que "8414.30" != 8414.3 en una comparación
    de tipos mixtos con .isin().

    Esta función reconstruye el formato "NNNN.NN" sin importar si la
    columna llegó como float, int o string.
    """
    if "partida_arancelaria" not in df.columns:
        return df

    def _format_codigo(valor):
        if pd.isna(valor):
            return valor
        if isinstance(valor, (int, float)):
            # Reconstruir con 2 decimales: 8414.3 -> "8414.30"
            return "{:.2f}".format(float(valor))
        # Ya es string: asegurar 2 decimales si tiene formato numérico
        texto = str(valor).strip()
        try:
            return "{:.2f}".format(float(texto))
        except ValueError:
            return texto  # No es numérico, dejar como está

    df["partida_arancelaria"] = df["partida_arancelaria"].apply(_format_codigo)
    return df


MAX_FILE_MB = 25
MAX_ROWS = 500_000
MAX_COLS = 200


def load_file(uploaded_file) -> pd.DataFrame:
    """Carga un archivo CSV o Excel subido vía st.file_uploader.

    v2.0: valida tamaño, filas y columnas antes de aceptar el archivo, para
    que un archivo gigante o malformado no deje sin memoria al servidor.
    """
    name = uploaded_file.name.lower()
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_FILE_MB * 1024 * 1024:
        raise ValueError(f"El archivo supera el límite de {MAX_FILE_MB} MB.")
    if name.endswith(".csv"):
        # dtype=str en partida_arancelaria evita que pandas la infiera como float
        df = pd.read_csv(uploaded_file, dtype={"partida_arancelaria": str},
                         nrows=MAX_ROWS + 1, sep=None, engine="python")
    elif name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, nrows=MAX_ROWS + 1, engine="openpyxl")
    else:
        raise ValueError("Formato no soportado. Use CSV o XLSX.")
    if len(df) > MAX_ROWS:
        raise ValueError(f"El archivo tiene más de {MAX_ROWS:,} filas; divídelo antes de subirlo.")
    if df.shape[1] > MAX_COLS:
        raise ValueError(f"El archivo tiene más de {MAX_COLS} columnas; revisa que sea el correcto.")
    if df.empty:
        raise ValueError("El archivo está vacío.")
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # FIX crítico: normalizar partida_arancelaria sin importar cómo llegó
    df = _normalizar_partida_arancelaria(df)

    return df


def validate_columns(df: pd.DataFrame) -> dict:
    """Valida que el dataset tenga las columnas mínimas esperadas."""
    present = [c for c in REQUIRED_COLUMNS if c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return {
        "valid": len(missing) == 0,
        "present_columns": present,
        "missing_columns": missing,
        "n_rows": len(df),
        "n_cols": len(df.columns),
    }


def data_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Genera un resumen de completitud por columna."""
    report = pd.DataFrame({
        "columna": df.columns,
        "tipo": [str(t) for t in df.dtypes],
        "nulos": df.isnull().sum().values,
        "% completitud": (100 * (1 - df.isnull().sum() / max(len(df), 1))).round(1).values,
    })
    return report