"""
src/data/sample_generator.py
Genera un dataset sintético mensual (2015-2024) que imita datos integrados
de DIAN, DANE y Banco de la República, para demostrar el sistema sin
requerir los archivos oficiales reales.
"""
import numpy as np
import pandas as pd

from config.settings import INSUMOS_CRITICOS, FECHA_INICIO, FECHA_FIN


def generate_sample_dataset(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fechas = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="MS")
    partidas = list(INSUMOS_CRITICOS.keys())

    rows = []
    for partida in partidas:
        base = rng.uniform(80_000, 260_000)
        trend = rng.uniform(300, 1200)
        season_amp = rng.uniform(0.08, 0.22)
        noise_scale = rng.uniform(0.05, 0.12)

        trm = 2400.0
        ipi = 98.0
        for i, fecha in enumerate(fechas):
            month = fecha.month
            year = fecha.year

            # Macro variable evolution (random walk with drift)
            trm += rng.normal(6, 35)
            trm = max(1700, trm)
            ipc_var = rng.normal(0.4, 0.35)
            tasa_interes = np.clip(4.0 + 0.002 * i + rng.normal(0, 0.3), 1.5, 14)
            ipi += rng.normal(0.15, 1.2)
            ipi = max(70, ipi)

            # Pandemic shock (2020) and FX crisis (2022) effects
            shock = 0.0
            if fecha.year == 2020 and fecha.month in (3, 4, 5):
                shock -= 0.35
            if fecha.year == 2022 and fecha.month in (9, 10, 11):
                shock -= 0.15
                trm += 80

            seasonal = 1 + season_amp * np.sin(2 * np.pi * (month / 12))
            trend_component = base + trend * i
            noise = rng.normal(0, noise_scale * trend_component)

            volumen = max(1000, trend_component * seasonal * (1 + shock) + noise)
            valor_fob = volumen * rng.uniform(3.5, 9.0)

            rows.append({
                "fecha": fecha,
                "partida_arancelaria": partida,
                "volumen_importacion_kg": round(volumen, 2),
                "valor_fob_usd": round(valor_fob, 2),
                "trm_peso_dolar": round(trm, 2),
                "ipc_variacion_mensual": round(ipc_var, 3),
                "tasa_interes_referencia": round(tasa_interes, 2),
                "ipi_manufacturero": round(ipi, 2),
            })

    df = pd.DataFrame(rows).sort_values(["partida_arancelaria", "fecha"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    import os
    from config.settings import SAMPLE_DATA_PATH
    df = generate_sample_dataset()
    os.makedirs(os.path.dirname(SAMPLE_DATA_PATH), exist_ok=True)
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    print(f"Dataset de muestra generado: {SAMPLE_DATA_PATH} ({len(df)} filas)")
