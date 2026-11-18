# ImportPredic

Prototipo de software del proyecto de grado **«Modelo predictivo basado en aprendizaje automático
para la estimación del volumen de importación de insumos críticos en la fabricación de
refrigeradores en Colombia»** — Angello André Corredor Rangel, Ingeniería de Sistemas,
Universidad de Investigación y Desarrollo (UDI), Barrancabermeja, 2026.

ImportPredic estima el volumen mensual de importación de cuatro insumos críticos, combinando su
historial con variables macroeconómicas (TRM, IPC, tasa de interés y producción industrial), y
compara cinco modelos de aprendizaje automático con un modelo ARIMA de referencia:

| Partida arancelaria | Insumo |
|---|---|
| 8414.30 | Compresores herméticos para refrigeración |
| 2903.39 | Gases refrigerantes (HFC-134a; desde 2022, subpartidas 2903.41 a 2903.69 del SA 2022) |
| 8537.10 | Tarjetas electrónicas de control |
| 3926.90 | Piezas de plástico técnico |

## Guía rápida para evaluadores

1. Descarga el código con el botón verde **Code → Download ZIP** (o desde *Releases*) y descomprímelo.
2. Instala **Python 3.12** desde [python.org](https://www.python.org/downloads/) marcando
   *Add python.exe to PATH*.
3. En Windows, doble clic en **`INICIAR_IMPORTPREDIC_WINDOWS.bat`**; en macOS,
   `iniciar_importpredic_mac.command`. La primera vez instala las librerías (5 a 10 minutos) y luego
   abre la aplicación en `http://localhost:8501`.
4. Crea una cuenta (la primera cuenta creada queda como administrador).
5. En **Carga de Datos**, sube `data/reales/ImportPredic_datos_reales_2016_2024.csv` (datos reales
   2016-2024) o usa los datos de demostración, y recorre los módulos en orden: Exploración,
   Entrenamiento (con *walk-forward*), Predicción, Evaluación, Interpretabilidad y Reporte.

El asistente de IA es opcional: necesita una llave gratuita de [openrouter.ai/keys](https://openrouter.ai/keys)
en `.streamlit/secrets.toml` (copia `secrets.toml.example` como `secrets.toml`). Sin ella, todo lo demás funciona.

## Resultados con datos reales (resumen)

Con datos de 2016 a 2024 (entrenamiento 2016-2022 y prueba 2023-2024):

| Modelo | RMSE (kg) | MAPE (%) | Mejora del RMSE frente a ARIMA |
|---|---:|---:|---:|
| Random Forest | 394 354 | 10,95 | 14,20 % |
| Ridge | 426 044 | 10,63 | 7,30 % |
| ARIMA (referencia) | 459 612 | 11,27 | — |

Ninguna diferencia fue estadísticamente significativa (Diebold-Mariano: DM = 0,909; p = 0,363). En la
validación *walk-forward*, Ridge redujo el RMSE en un 25,17 % en promedio, pero al usar el valor FOB del
mes anterior la ventaja cayó por debajo del 6 %. El análisis completo está en el documento final del proyecto.

## Características

- **Interfaz futurista** con paleta neón (cyan/magenta/verde/morado), fondo oscuro y una
  escena 3D en Three.js (grid infinito, esfera holográfica, anillos orbitales, partículas).
- **5 algoritmos de Machine Learning** (XGBoost, Gradient Boosting, Random Forest, Ridge,
  Lasso) comparados automáticamente contra un modelo **ARIMA** de referencia.
- **Validación temporal estricta** (sin mezcla aleatoria de fechas).
- **Pruebas de hipótesis estadísticas**: Shapiro-Wilk, Diebold-Mariano, t-test/Wilcoxon.
- **Interpretabilidad con SHAP** (TreeExplainer / LinearExplainer): importancia global,
  summary plot y waterfall individual.
- **Pronósticos a futuro** con bandas de confianza del 95% y recomendaciones automáticas.
- **Exportación** de resultados en PDF, Excel, CSV y del modelo entrenado (.joblib).
- **Cuentas de usuario y base de datos**: cada corrida queda guardada en la cuenta de quien la hizo.

## Datos

- **Datos reales:** `scripts/descargar_datos_reales.py` (o `DESCARGAR_DATOS_REALES_WINDOWS.bat`) descarga
  las importaciones por subpartida de UN Comtrade (estadísticas oficiales reportadas por el DANE), la TRM
  de la Superintendencia Financiera, la tasa de política monetaria del Banco de la República y el IPC y la
  producción industrial del Banco Mundial. El archivo depurado que se usó en el proyecto es
  `data/reales/ImportPredic_datos_reales_2016_2024.csv`.
- **Datos de demostración:** `src/data/sample_generator.py` genera un conjunto sintético 2015-2024 para
  probar el sistema sin conexión.

Estructura mínima de un archivo propio (CSV o XLSX):

```
fecha, partida_arancelaria, volumen_importacion_kg, valor_fob_usd,
trm_peso_dolar, ipc_variacion_mensual, tasa_interes_referencia, ipi_manufacturero
```

## Novedades de la versión 2.0

- **Base de datos** (SQLAlchemy): SQLite en local sin instalar nada, PostgreSQL en la nube
  cambiando una sola variable (`DATABASE_URL`). Corridas, métricas por modelo, pronósticos,
  historial del asistente, uso de IA y auditoría quedan en tablas relacionales.
- **Cuentas de usuario**: inicio de sesión obligatorio, contraseñas con *scrypt*, bloqueo
  temporal tras 5 intentos fallidos, cierre de sesión por inactividad y rol administrador.
  Cada usuario solo ve sus propias corridas.
- **API key protegida**: ya no está en el código; se lee en el servidor desde
  `.streamlit/secrets.toml` o variables de entorno. Límite de consultas a la IA por usuario
  y por hora.
- **Integridad de datos**: los objetos guardados (modelos, scaler…) se firman con HMAC-SHA256
  y se verifican antes de cargarse.
- **Rigor metodológico**: el escalado se ajusta solo con el periodo de entrenamiento (antes se
  filtraba información del periodo de prueba) y la opción *walk-forward* ahora sí se ejecuta.
- **Historial comparativo**: compara métricas y pronósticos de varias corridas lado a lado.
- **Panel de administración**: usuarios, uso de la IA y bitácora de auditoría.
- **Pruebas automatizadas** (`pytest`), incluida una que falla si alguien vuelve a pegar una
  API key en el código.

## Instalación y ejecución (local)

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar secretos (una sola vez)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
#   -> pon tu OPENROUTER_API_KEY y una APP_SECRET_KEY propia:
python -c "import secrets; print(secrets.token_urlsafe(48))"
#   -> deja DATABASE_URL comentado para usar SQLite local

# 4. Ejecutar
streamlit run app.py
```

La primera cuenta que se registre queda como **administrador**. Si cierras el registro
(`ALLOW_REGISTRATION = false`), el administrador puede crear cuentas desde la página
*Administración*, o desde consola con `python -m scripts.crear_admin`.

### Configuración disponible

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `OPENROUTER_API_KEY` | Key del asistente de IA (solo vive en el servidor) | — (IA desactivada) |
| `APP_SECRET_KEY` | Firma de los datos guardados en la BD. **Obligatoria en producción** | Se genera en `data/.secret_key` (solo desarrollo) |
| `APP_ENV` | `development` o `production` | `development` |
| `DATABASE_URL` | Conexión a PostgreSQL | SQLite en `data/importpredic.db` |
| `ALLOW_REGISTRATION` | Permitir que cualquiera cree cuenta | `true` |
| `AI_MAX_REQUESTS_PER_HOUR` | Consultas a la IA por usuario y hora | `40` |
| `SESSION_TIMEOUT_MINUTES` | Cierre de sesión por inactividad | `60` |

## Despliegue en la nube (Streamlit Community Cloud + PostgreSQL)

1. Crea una base de datos PostgreSQL gratuita (Supabase, Neon o Railway) y copia su cadena de
   conexión con el formato `postgresql+psycopg2://usuario:clave@host:5432/db?sslmode=require`.
2. Sube el proyecto a GitHub (el `.gitignore` ya excluye `.env`, `secrets.toml` y la BD local).
3. En share.streamlit.io crea la app apuntando a `app.py`.
4. En **Settings → Secrets** pega el contenido de `.streamlit/secrets.toml.example` con tus
   valores reales, `APP_ENV = "production"` y la línea `DATABASE_URL` descomentada.

Las tablas se crean solas en el primer arranque. En SQLite local los datos persisten en
`data/importpredic.db`; en Streamlit Cloud el disco **no** es permanente, por eso allí se
debe usar PostgreSQL.

## Modelo de datos

```mermaid
erDiagram
    usuarios ||--o{ corridas : "tiene"
    usuarios ||--o{ mensajes_ia : "escribe"
    usuarios ||--o{ uso_ia : "consume"
    usuarios ||--o{ auditoria : "genera"
    corridas ||--o{ resultados_modelos : "compara"
    corridas ||--o{ pronosticos : "proyecta"
    corridas ||--o{ artefactos : "guarda"
    corridas |o--o{ mensajes_ia : "contexto"

    usuarios { int id PK  string username UK  string password_hash  string rol  bool activo  int intentos_fallidos  datetime bloqueado_hasta }
    corridas { int id PK  int usuario_id FK  string nombre  int n_filas  date fecha_inicio  date fecha_fin  json partidas  string mejor_modelo  float rmse  float mejora_vs_arima  bool hipotesis_confirmada }
    resultados_modelos { int id PK  int corrida_id FK  string modelo  float mae  float rmse  float r2  float mape  float mejora_vs_arima  bool es_mejor }
    pronosticos { int id PK  int corrida_id FK  date fecha  float prediccion  float limite_inferior  float limite_superior }
    artefactos { int id PK  int corrida_id FK  string clave  blob contenido  string firma  string huella }
    mensajes_ia { int id PK  int usuario_id FK  int corrida_id FK  string pagina  string rol  text contenido }
    uso_ia { int id PK  int usuario_id FK  string pagina  string tipo  bool exito  datetime creado_en }
    auditoria { int id PK  int usuario_id FK  string accion  string detalle  datetime creado_en }
```

## Seguridad

| Riesgo | Medida |
|---|---|
| API key visible en el código | Se lee de `st.secrets`/entorno; `.gitignore`; prueba automática que detecta keys pegadas |
| Abuso del saldo de la API | Login obligatorio + límite de consultas por usuario/hora + registro en `uso_ia` |
| Ver datos de otra persona | Toda consulta de corridas filtra por `usuario_id` (probado en `tests/test_repository.py`) |
| Contraseñas filtradas | Hash *scrypt* con sal; nunca se guardan en texto plano |
| Fuerza bruta | Bloqueo 15 min tras 5 intentos; mensaje genérico; tiempo de respuesta constante |
| Manipulación de la BD → ejecución de código (pickle) | Firma HMAC-SHA256 verificada antes de deserializar |
| Inyección de HTML en el chat | Mensajes del usuario escapados antes de mostrarse |
| Archivos gigantes o malformados | Límite de 25 MB, 500 000 filas y 200 columnas por archivo |
| Filtración de errores internos | `showErrorDetails = false`; errores de la IA registrados en el log del servidor |

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Migrar el historial de la versión 1.x

Si tenías corridas en `data/history/*.joblib`, regístrate en la app y luego ejecuta:

```bash
python -m scripts.migrar_historial --usuario TU_USUARIO
```

## Contexto académico

- **Universidad:** Universidad de Investigación y Desarrollo (UDI) — Barrancabermeja
- **Programa:** Ingeniería de Sistemas — Línea de investigación: Sistemas de Información (Grupo Gidsaw)
- **Director:** Marino Rodríguez Palacios · **Codirector:** Andrés Sneyder Salom Díaz
- **Autor:** Angello André Corredor Rangel
- **Objetivo:** Reducir en al menos 15% el RMSE frente al modelo ARIMA de referencia.

## Notas técnicas

- El dataset sintético es solo para fines demostrativos; para resultados académicos válidos,
  reemplázalo con datos reales exportados de la DIAN, el DANE y el Banco de la República.
- Los grids de hiperparámetros completos (`PARAM_GRIDS` en `config/settings.py`) están
  disponibles para una búsqueda exhaustiva fuera de la interfaz; dentro de la app se usan
  parámetros por defecto razonables para mantener tiempos de respuesta interactivos.
