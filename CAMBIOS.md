# ImportPredic — Registro de cambios v2.0

## 1. Hallazgos del análisis de la versión 1.x

### Seguridad (críticos)
1. **API key de OpenRouter escrita en el código** (`src/ai/openrouter_client.py`). Cualquier
   persona con acceso al código (o al repositorio) podía usarla y gastar el saldo.
2. **Otra API key en `.env` y en `.env.example`**. El archivo `.example` es justamente el que se
   comparte y se sube a GitHub.
3. **Historial global sin usuarios**: todas las corridas se guardaban en `data/history/` y, al
   abrir la app, se restauraba automáticamente la última corrida *de cualquier persona*. Con la
   app publicada, un visitante veía los datos, modelos y resultados de otro.
4. **Deserialización insegura**: los `.joblib` (pickle) se cargaban sin verificar su origen; un
   archivo manipulado podía ejecutar código en el servidor.
5. **Sin control de acceso ni límite de uso** de la IA: cualquiera podía consumir la key.
6. La interfaz le pedía al usuario **editar el código fuente para pegar la key**.
7. El texto escrito por el usuario en el chat se insertaba como HTML sin escapar.
8. Sin límites de tamaño/filas en los archivos subidos.

### Metodología / correctitud
9. **Fuga de información en el escalado**: el `MinMaxScaler` se ajustaba con TODO el dataset
   (incluido el periodo de prueba) antes de separar train/test, lo que hace las métricas de
   test levemente optimistas.
10. **La opción "Walk-forward (5 splits)" no hacía nada**: se mostraba en la interfaz pero el
    código siempre ejecutaba hold-out.
11. Al procesar un dataset nuevo, el modelo, pronósticos y pruebas del dataset **anterior**
    seguían en sesión y se guardaban mezclados en la corrida nueva.
12. El contexto enviado a la IA en Entrenamiento leía una clave inexistente (`RMSE_ARIMA`), así
    que el asistente siempre recibía `0` como RMSE de ARIMA.
13. `models_saved/` era una carpeta global sobrescrita por el último entrenamiento de cualquiera.
14. Evaluación e Interpretabilidad recalculaban y guardaban en disco en cada interacción.

### Calidad de código
15. Las ~15 líneas de arranque se repetían en las 10 páginas.
16. Carpeta `tests/` vacía.

## 2. Cambios realizados

| # | Cambio | Archivos |
|---|---|---|
| 1-2, 6 | Key eliminada del código; lectura desde `st.secrets`/entorno; `.env` borrado; `.env.example` y `secrets.toml.example` sin secretos; `.gitignore` | `config/secrets.py`, `src/ai/openrouter_client.py`, `.gitignore` |
| 3 | Base de datos con usuarios: cada corrida pertenece a su dueño; todas las consultas filtran por `usuario_id` | `src/db/*`, `src/data/persistence.py` |
| 3, 5 | Login/registro, scrypt, bloqueo tras 5 intentos, expiración por inactividad, roles, revalidación de cuenta cada minuto | `src/auth/*`, `components/page_setup.py` |
| 4 | Artefactos firmados con HMAC-SHA256 y verificados antes de cargarse | `src/db/repository.py`, `src/auth/security.py` |
| 5 | Límite de consultas a la IA por usuario/hora y registro en `uso_ia`; solo se aceptan ids de modelo de la lista blanca | `src/ai/assistant.py`, `src/ai/openrouter_client.py` |
| 7 | Escape HTML de los mensajes del usuario; longitud máxima de pregunta | `components/ai_panel.py` |
| 8 | Límite de 25 MB / 500 000 filas / 200 columnas; detección de separador `;` | `src/data/loader.py`, `.streamlit/config.toml` |
| 9 | El scaler se ajusta solo con el periodo de entrenamiento | `src/data/preprocessor.py`, `pages/04_entrenamiento.py` |
| 10 | Walk-forward real con ventana expansiva (re-escalado y re-entrenamiento por pliegue) | `src/models/model_selector.py` |
| 11 | Al procesar datos nuevos o re-entrenar se limpian los resultados dependientes | `src/data/persistence.py` |
| 12 | Corregido el RMSE de ARIMA enviado a la IA | `pages/04_entrenamiento.py` |
| 13 | Modelo guardado en la corrida del usuario + botón de descarga `.joblib` | `src/utils/serializer.py` |
| 14 | Pruebas estadísticas y SHAP se guardan solo cuando cambian; artefactos sin cambios no se reescriben | `pages/06_*`, `pages/07_*`, `src/db/repository.py` |
| 15 | `setup_page()` común para todas las páginas | `components/page_setup.py` |
| 16 | 16 pruebas automatizadas | `tests/` |

### Funcionalidades nuevas
- **Historial**: buscar, cargar, renombrar y eliminar (con confirmación) corridas; **comparar**
  hasta 6 corridas (métricas, RMSE por modelo, pronósticos superpuestos, exportar CSV).
- **Historial del chat de IA** persistente por página y por corrida.
- **Panel de administración**: KPIs, gestión de usuarios, uso de la IA y bitácora de auditoría.
- **Inicio** con resumen personal (corridas, hipótesis confirmadas, mejor modelo).
- Scripts `crear_admin` y `migrar_historial` (importa corridas de la v1).

## 3. Recomendaciones pendientes (no aplicadas a propósito)
- **Lags iniciales con *backfill***: en `create_temporal_features` los primeros 12 meses rellenan
  sus rezagos con valores posteriores (`bfill`), de modo que, por ejemplo, el `lag_1` de la
  primera fila es el propio valor objetivo. Afecta solo a filas de entrenamiento, pero lo
  riguroso es descartar esas filas (`dropna`). No se cambió porque altera los resultados que ya
  puedas tener documentados; es una línea si decides hacerlo.
- El intervalo de confianza del pronóstico usa ±1,96·RMSE constante en todo el horizonte; en la
  práctica la incertidumbre crece con el horizonte (se puede mencionar como limitación).
