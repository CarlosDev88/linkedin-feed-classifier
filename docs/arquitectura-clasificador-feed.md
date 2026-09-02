# Clasificador de intención del feed — Plano de construcción (v2, post-auditoría)

Proyecto complementario al Job Tracker (mini-ATS). Objetivo: reemplazar, solo para las publicaciones que vienen del feed de LinkedIn, la parte del pipeline que hoy decide "¿esto es una vacante o es ruido?" — por una red neuronal entrenada sobre embeddings de texto, para mejorar el recall de vacantes detectadas.

Esta versión incorpora los hallazgos de una auditoría técnica independiente sobre la v1 del plano. Cada decisión marcada **[AUDITORÍA]** viene de ahí. Se distingue **OBLIGATORIO** (sin esto, el proyecto no puede demostrar que funcionó) de **RECOMENDADO** (mejora la rigurosidad, no bloquea nada) y **OPCIONAL** (mejora eficiencia, decisión de alcance).

## 1. Contexto y problema a resolver

El Job Tracker recibe datos de tres fuentes, vía la extensión `job-scraper-extension`:

- **Get on Board** — siempre es vacante, no requiere clasificación.
- **Sección de empleos de LinkedIn** — siempre es vacante, no requiere clasificación.
- **Feed de LinkedIn** — contenido mixto (vacantes en texto libre, cambios de empresa, propaganda, ruido social). Requiere decidir intención.

Hoy, un único algoritmo basado en palabras clave hace dos trabajos distintos: (1) decidir intención — solo relevante para el feed — y (2) calificar el ajuste de una vacante confirmada contra el perfil de Carlos. El paso (1) es el que falla: el regex no generaliza sobre lenguaje natural ambiguo y se pierden vacantes reales publicadas como texto plano (falsos negativos).

## 2. Alcance

**Sí incluye:** medir el desempeño del algoritmo actual como referencia; recolectar y etiquetar un dataset de posts del feed; entrenar un clasificador binario (vacante / no_vacante) sobre embeddings de texto; evaluar el modelo con foco en recall, comparado estadísticamente contra la referencia; producir el artefacto final e integrarlo como reemplazo del paso (1), únicamente para el feed, con enrutamiento de tres salidas (sección 3).

**No incluye:** tocar Get on Board o la sección de empleos de LinkedIn; tocar el paso (2) de scoring/matching; búsqueda vectorial para el matching perfil↔vacante (idea futura, sección 15); sub-clasificación granular del ruido.

## 3. Arquitectura del pipeline resultante

**[AUDITORÍA — OBLIGATORIO, H-13]** El modelo no es un portero binario. Devuelve una probabilidad y se enruta con dos umbrales, reutilizando el patrón REVISAR que el Job-Tracker ya tiene para lo ambiguo:

```
Get on Board ──────────────────────────────────────┐
                                                     │
LinkedIn (sección empleos) ─────────────────────────┼──► [Paso 2: scoring/matching   ──► Resultados en
                                                     │     por keywords contra perfil]     el Job Tracker
LinkedIn feed ──► [Red neuronal: P(vacante)]        │
                     │                               │
                     ├─ P alta   ──► vacante ─────────┘
                     ├─ P media  ──► cola REVISAR (humano decide)
                     └─ P baja   ──► descartado
```

Por qué este diseño y no el binario original: en un portero binario, un falso negativo se pierde para siempre — el costo de cada error del modelo es máximo, y por eso la v1 exigía 70-80% de recall como condición dura. Con tres salidas, los casos dudosos ya no se pierden, se encolan — baja drásticamente la exigencia sobre el modelo y, de regalo, cada decisión que Carlos tome en REVISAR es una etiqueta nueva para el siguiente reentrenamiento (cierra el ciclo de mejora continua sin trabajo adicional).

**Importante:** este cambio es sobre cómo se usa la probabilidad del modelo en producción (inferencia), no sobre el esquema de etiquetas de entrenamiento. Se sigue entrenando binario, `vacante` / `no_vacante` (sección 5).

## 4. Origen de los datos de entrenamiento

Únicamente el JSON del feed de LinkedIn (`fuente: "linkedin_feed"`). No se usa Get on Board ni la sección de empleos de LinkedIn: su estilo de texto (portal de empleos formal) es distinto al de una vacante anunciada informalmente en el feed, y entrenar con un estilo que el modelo nunca verá en producción genera desajuste entrenamiento/producción sin necesidad.

**Cómo llegan los datos:** el scraper corre en Windows y guarda cada exportación en `Descargas/JobTracker/*.json`. Esa carpeta se monta como volumen de solo lectura dentro del contenedor (sección 7).

**[AUDITORÍA — RECOMENDADO, H-10]** El split de evaluación final se reporta de dos formas: aleatorio (sección 9) y temporal (entrenar con la primera semana de datos, evaluar con la segunda). En producción el modelo siempre ve posts futuros respecto a su entrenamiento — el split temporal mide eso de verdad. Si ambos números divergen mucho, es una señal de que el contenido del feed cambia de forma que el modelo no está capturando.

## 5. Esquema de etiquetas

- **Etiqueta de entrenamiento (binaria):** `vacante` / `no_vacante`. No cambia con el enrutamiento de tres salidas de la sección 3.
- **Atajo gratis:** `tiene_tarjeta_empleo=true` → auto-etiqueta `vacante`, sin revisión humana.
- **Todo lo demás** se etiqueta a mano con la vista de botones (sección 8).
- **Metadato de trazabilidad:** `origen_etiqueta` = `tarjeta_empleo` / `humano` / **`revision_produccion`** (nueva: etiquetas que salen de que Carlos resuelva la cola REVISAR una vez el sistema esté en producción — alimentan reentrenamientos futuros).

**[AUDITORÍA — RECOMENDADO, H-5]** Los positivos por `tarjeta_empleo` son casi todos texto de plantilla autogenerada por LinkedIn (`"Empresa is #hiring"`) — exactamente los casos que ya se detectan sin modelo. Se mantienen en entrenamiento (suman volumen sin hacer daño ahí), pero **el recall se reporta siempre desglosado por origen de etiqueta** (tarjeta vs. humano) — el número de `humano` es el que importa, porque es el que mide si el modelo resuelve el problema real (texto libre ambiguo).

## 6. Baseline: medir antes de construir

**[AUDITORÍA — OBLIGATORIO, H-1]** Sin este número, el proyecto no puede demostrar que mejoró nada, y la meta de recall es arbitraria. Apenas exista el primer lote etiquetado (no al final del proyecto), correr el algoritmo de intención actual (el de palabras clave) sobre ese mismo conjunto y registrar su recall y precisión. Ese resultado es la referencia contra la que se compara todo lo demás — incluida la meta de 70-80%, que puede ajustarse hacia arriba o hacia abajo según lo que arroje esta medición.

**[AUDITORÍA — RECOMENDADO]** Además de un baseline de reglas, correr un **baseline de TF-IDF + regresión logística** sobre el mismo dataset (H-8). Es barato (minutos de cómputo) y, en clasificación de texto corto con pocos cientos de ejemplos, frecuentemente iguala o supera a embeddings + red pequeña. Si gana, es un hallazgo legítimo (menos complejidad en producción); si pierde, cuantifica por qué valió la pena la red — cualquiera de los dos resultados es material directo para el informe de la especialización y evita que "usé una red neuronal" sea una elección sin defensa.

## 7. Infraestructura: Docker

Una sola imagen, un `docker-compose.yml`, volumen de solo lectura hacia `Descargas/JobTracker` vía `.env` (para no exponer la ruta personal de Carlos en GitHub), volumen de caché para el modelo de embeddings.

**[NUEVO — MLflow]** `mlflow` se agrega a `requirements.txt`, en modo de archivo local (sin servidor propio corriendo todo el tiempo): los scripts de `training/` escriben directo a una carpeta `mlruns/` dentro del proyecto (persiste vía el mismo volumen `.:/workspace`, no necesita volumen aparte). Para revisar resultados, se levanta la interfaz solo cuando se necesita: `docker compose run --rm -p 5000:5000 app mlflow ui --host 0.0.0.0`, sin dejar nada corriendo de fondo el resto del tiempo.

**[NUEVO — servicio de API, sección 10]** Se agrega un segundo servicio, `api`, que sí queda corriendo de forma persistente (a diferencia de `app`, que se usa bajo demanda): carga el modelo de producción desde el Model Registry de MLflow y expone `POST /predict`. Es lo único de este proyecto que el Job-Tracker consume.

```yaml
services:
  app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - .:/workspace
      - ${HOST_SCRAPER_PATH}:/data/raw:ro
      - embeddings_cache:/root/.cache
    env_file:
      - .env
    command: streamlit run labeling_app/app.py --server.address=0.0.0.0

  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/workspace
      - embeddings_cache:/root/.cache
    env_file:
      - .env
    command: uvicorn serving.app:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

volumes:
  embeddings_cache:
```

```dockerfile
FROM python:3.12-slim
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
```

## 8. Estructura de carpetas del proyecto

```
feed-intent-classifier/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── config.py
├── requirements.txt
├── data/
│   ├── raw/                        # volumen montado, solo lectura
│   ├── labels/                     # etiquetas humanas + revisión de producción
│   └── processed/
│       └── dataset_entrenamiento.csv
├── mlruns/                          # historial de experimentos (MLflow, modo archivo local)
├── labeling_app/
│   └── app.py
├── training/
│   ├── build_dataset.py            # dedupe exacto + combinar etiquetas
│   ├── generate_embeddings.py      # vectoriza + agrupa casi-duplicados por similitud (orden corregido)
│   ├── baseline_regex.py           # [NUEVO] mide el algoritmo actual sobre el dataset etiquetado
│   ├── baseline_tfidf.py           # [NUEVO] TF-IDF + regresión logística
│   ├── train.py                    # registra el modelo en el Model Registry de MLflow
│   └── evaluate.py                 # PR curve, CV, comparación pareada vs. baseline
├── serving/                         # [NUEVO] API del modelo — sección 10
│   └── app.py                      # FastAPI, endpoint POST /predict
├── tests/
│   └── test_dataset.py
└── notebooks/
    └── exploracion.ipynb
```

## 9. Especificación de cada componente

**`labeling_app/app.py`:** sin cambios respecto a v1 — escanea `data/raw/` en cada carga, calcula id por hash SHA-256 (`descripcion` + `autor_perfil`), separa automático lo que tiene tarjeta, filtra lo ya etiquetado, muestra encabezado (primera línea) + cuerpo completo, dos botones.

**[AUDITORÍA — RECOMENDADO, H-9]** Fase de etiquetado en dos tiempos:
- **Lote 1: etiquetar el 100%** de lo que no tiene tarjeta. Necesario para tener una estimación sin sesgo de la distribución real de clases y un conjunto de evaluación limpio.
- **Lotes siguientes: muestreo por incertidumbre**, una vez exista un primer modelo entrenado — priorizar en la cola los posts donde el modelo está menos seguro (probabilidad cercana al umbral), que es donde cada etiqueta nueva aporta más información.
- **Regla que no se negocia:** el conjunto de evaluación sale siempre del lote 1 (100% etiquetado), nunca del pool muestreado por incertidumbre — de lo contrario las métricas dejan de representar la realidad.

**[AUDITORÍA — OPCIONAL]** Etiquetado asistido por LLM (no es "destilación de conocimiento" en sentido estricto — es *weak supervision*: un modelo grande genera candidatos, un humano los verifica). La vista de Streamlit puede mostrar una etiqueta sugerida por un LLM, y el trabajo de Carlos pasa de decidir desde cero a confirmar/corregir — reduce el tiempo de etiquetado en 60-70% (verificar toma ~3 segundos, decidir desde cero ~12). Sigue haciendo falta la verificación humana en el 100%, o se hereda el mismo problema que tenía el regex (el modelo aprende a imitar los errores del "maestro"). Es una decisión de alcance, no una obligación del proyecto.

**`training/build_dataset.py`:**
- Dedupe exacto por id (hash SHA-256 de `descripcion` + `autor_perfil`, como en v1).
- Combina etiquetas gratis (tarjeta) y humanas, conservando `origen_etiqueta`.
- Produce el texto limpio de cada post, listo para vectorizar. El agrupamiento por casi-duplicados **no va aquí** — necesita los vectores de embeddings, que todavía no existen en este paso (ver `generate_embeddings.py`, orden corregido tras revisión).

**`training/generate_embeddings.py`:**
- **[AUDITORÍA — OBLIGATORIO, H-3]** El modelo por defecto (`paraphrase-multilingual-MiniLM-L12-v2`) trunca a 128 tokens (~450-500 caracteres). Medido sobre datos reales del feed: **52% de los posts supera ese límite** y se corta en silencio. Antes de fijar el modelo, correr el experimento comparativo: entrenar con MiniLM (128 tokens, 384 dim) y con `multilingual-e5-base` (512 tokens, 768 dim — requiere prefijos `"query: "` / `"passage: "` en el texto o pierde rendimiento) y comparar recall. El resultado, sea cual sea, se documenta como una decisión justificada con evidencia, no por defecto.
- **[REFINAMIENTO]** Leer más texto no es automáticamente mejor: cualquiera de los dos modelos comprime el texto completo en un solo vector de tamaño fijo, y si el post es largo y repetitivo (listas de requisitos/beneficios, relleno corporativo), un modelo de contexto largo puede diluir la señal real entre el relleno, no solo "capturarla mejor". Revisando los posts reales, la señal de vacante está casi siempre concentrada en las primeras líneas ("Buscamos...", "We're hiring...", "🚀 Oportunidad..."). Por eso, además de comparar MiniLM vs. e5-base, se controla explícitamente cuánto texto de cada post se vectoriza (ej. quedarse con las primeras N oraciones/caracteres antes de generar el embedding) — así el recorte es una decisión de diseño deliberada y documentada, no un accidente silencioso del modelo elegido.
- **[AUDITORÍA — OBLIGATORIO, H-4 — corregido de orden]** Una vez calculados los vectores, agrupar por **casi-duplicados**: la misma vacante reposteada por distintos reclutadores, o con una redacción ligeramente distinta, no se detecta con hash exacto, pero sí comparando qué tan parecidos son sus vectores. Se agrupan por similitud de embeddings (coseno > 0.95) y se asigna un `grupo_id` a cada post — todo el grupo debe caer del mismo lado de cualquier split de entrenamiento/prueba. Sin esto, el recall medido sale inflado porque el modelo "reconoce" el casi-duplicado en vez de generalizar. Este script entrega, entonces, el dataset final con: texto, vector, etiqueta, `origen_etiqueta` y `grupo_id` — es el único archivo que consume `train.py`.

**`training/baseline_regex.py` [NUEVO]:** corre el algoritmo de intención actual sobre el dataset etiquetado y calcula su recall/precisión — sección 6. Cada corrida se registra como un run de MLflow (sección 13).

**`training/baseline_tfidf.py` [NUEVO]:** TF-IDF + regresión logística sobre el mismo dataset — sección 6. También registrado como run de MLflow.

**`training/train.py`:**
- **[AUDITORÍA — OBLIGATORIO, H-2 + H-4 combinados]** Split y evaluación por **`StratifiedGroupKFold`** (5 folds) — no un holdout único. Un holdout del 20% deja solo ~52 positivos en prueba, con un intervalo de confianza del recall de ±11.8 puntos: **más ancho que toda la banda de meta (70-80%)**, es decir, no permite saber si se cumplió o no. `StratifiedGroupKFold` evalúa sobre todos los positivos disponibles (baja el intervalo a ±5 puntos aprox.) y, al mismo tiempo, respeta los `grupo_id` de casi-duplicados de `build_dataset.py` — un fold no puede tener un pie en entrenamiento y otro en prueba dentro del mismo grupo.
- Entrena el clasificador (MLPClassifier de scikit-learn, o red pequeña en PyTorch/Keras si se prioriza mostrar uso directo de un framework de deep learning en el informe).
- El modelo final que se despliega se reentrena sobre el 100% de los datos una vez que la validación cruzada ya dio una estimación confiable — la validación cruzada es para saber qué tan bueno es el enfoque, no para producir 5 modelos parciales.
- **[NUEVO — MLflow]** Cada combinación que se pruebe (modelo de embeddings × longitud de texto × tipo de clasificador) se registra como un run: parámetros (qué modelo, qué umbral de truncamiento, qué semilla), métricas (recall/precisión por fold), y el modelo entrenado guardado con `mlflow.sklearn.log_model()` (formato propio de MLflow, no `.npz` — ver sección 10) — así elegir "qué modelo usar" se responde comparando runs en la interfaz, no de memoria, y el modelo elegido se promueve directo al Model Registry desde ahí.

**`training/evaluate.py`:**
- **[AUDITORÍA — OBLIGATORIO, H-6]** El umbral no es un dato fijo: se reporta la **curva completa de precisión-recall**, se elige deliberadamente el punto de operación (ej. el umbral más bajo que da ≥75% recall) y se reporta el par (recall, precisión) en ese punto — nunca "el modelo dio 75% de recall" sin decir a qué umbral y con qué precisión asociada.
- Recall desglosado por `origen_etiqueta` (tarjeta vs. humano — sección 5).
- **[AUDITORÍA — RECOMENDADO]** Comparación contra los baselines (regex y TF-IDF) con **test de McNemar** (datos pareados: los tres se evalúan sobre exactamente los mismos posts), no solo comparando números sueltos — da una respuesta con significancia estadística ("la diferencia es real, p<0.05"), no solo "salió más alto".
- Split temporal además del aleatorio (sección 4).
- Veredicto explícito contra la meta, registrado como métrica del run de MLflow (sección 13) — reemplaza el `historial_evaluaciones.csv` manual de la versión anterior del plano.

## 10. Cómo se sirve el modelo: API, no archivo copiado

**[DECISIÓN ACTUALIZADA — reemplaza el enfoque de H-11]** Se descartó copiar un artefacto (`.npz` o pickle) hacia el repo del Job-Tracker. En su lugar, el modelo se expone como un servicio propio con un endpoint HTTP, y el Job-Tracker lo consume por red — el patrón estándar de "modelo servido como API" (consistente con lo visto en clase: Model Registry de MLflow + `load_model()` + endpoint `/predict`).

**Por qué esto es mejor que el archivo compartido y mejor que copiar el artefacto:**
- El modelo entrenado nunca sale del proyecto `feed-intent-classifier` — se sirve desde ahí mismo, con las mismas versiones de librerías con las que se entrenó. Esto resuelve el problema original de H-11 (fragilidad de pickle entre versiones de sklearn/numpy) de raíz, no con un rodeo: como el servicio que carga el modelo vive en el mismo entorno que lo entrenó, cargarlo con `mlflow.pyfunc.load_model()` es seguro, y ya no hace falta el truco de exportar a `.npz` y reimplementar el forward pass a mano.
- El Job-Tracker no necesita instalar `sentence-transformers` ni ninguna dependencia de ML — solo hace una llamada HTTP y recibe una probabilidad. Su imagen de Docker se queda liviana.
- Promover una versión nueva del modelo = cambiar a qué versión del Model Registry apunta el servicio y reiniciarlo. El repositorio del Job-Tracker no se toca nunca, ni su código ni sus archivos — separación real entre los dos proyectos.

**Cómo queda armado:**
- Un nuevo componente `serving/app.py` (FastAPI) dentro de `feed-intent-classifier`, con un único endpoint `POST /predict` que recibe el texto de un post y devuelve la probabilidad de que sea vacante.
- Al arrancar, este servicio carga con `mlflow.pyfunc.load_model()` la versión marcada como "producción" en el Model Registry — la misma que se generó en `train.py`/`evaluate.py`.
- Corre como un segundo servicio dentro del mismo `docker-compose.yml` del proyecto (sección 7), expuesto en un puerto propio.
- El Job-Tracker le hace una petición HTTP a ese endpoint desde su propio backend, justo donde hoy corre la lógica de intención del feed — sustituye esa lógica sin que el Job-Tracker necesite saber cómo está hecho el modelo por dentro.

**Regla de respaldo — decidida, no pendiente.** Si la llamada a `/predict` falla o tarda más de un timeout corto (propuesto: 3-5 segundos), el post se trata como si hubiera caído en la cola REVISAR — nunca se pierde el post ni se bloquea el pipeline, y nunca pasa sin filtro por default. Es la misma filosofía de "ante la duda, revisión humana" que ya rige el resto del diseño (sección 3). Cada falla se registra (log) para poder ver si el servicio se está cayendo seguido.

**Networking entre los dos proyectos — decidido.** Dado que ambos corren en Docker Desktop sobre Windows, el Job-Tracker le habla al servicio `api` a través de `host.docker.internal:8000` (el puerto publicado en el `docker-compose.yml` de este proyecto, sección 7) — no hace falta una red de Docker compartida entre los dos `docker-compose` independientes, que sería más complejidad de la que este caso necesita. La URL completa se define como variable de entorno en el `.env` del Job-Tracker, igual que ya se hace con `HOST_SCRAPER_PATH` en este proyecto.

**Expectativa operativa nueva:** a diferencia de `app` (que se usa bajo demanda), el servicio `api` debe quedar corriendo de forma permanente — el Job-Tracker depende de que esté disponible cada vez que llega un post del feed. Por eso lleva `restart: unless-stopped` en el `docker-compose.yml` (sección 7).

## 11. Flujo de trabajo operativo

**Días 1-3 (arranque):** primeras corridas del scraper, primer lote etiquetado al 100%, **medir el baseline de inmediato** (sección 6) — si el algoritmo actual ya rinde cerca de la meta, se ajusta el objetivo del proyecto antes de invertir dos semanas completas.

**Durante las ~2 semanas de recolección, varias veces al día:** correr el scraper → `docker compose up` → etiquetar en la vista de Streamlit (100% al inicio, luego por incertidumbre) → cerrar cuando se quiera, el progreso persiste.

**Cuando el dataset esté listo:**
1. `docker compose run --rm app python training/build_dataset.py`
2. `docker compose run --rm app python training/generate_embeddings.py`
3. `docker compose run --rm app python training/baseline_regex.py` y `baseline_tfidf.py`
4. `docker compose run --rm app python training/train.py`
5. `docker compose run --rm app python training/evaluate.py`

**Modo sombra, antes de tocar el Job-Tracker:** **[AUDITORÍA — OBLIGATORIO, H-7]** se fija la regla de decisión *antes* de empezar a observar, no después: ventana de tiempo definida (ej. 5 días), comparación contra el algoritmo viejo sobre los posts recién etiquetados de ese período (no sobre el dataset de entrenamiento), y un umbral explícito de corte pactado de antemano (ej. "se reemplaza si el recall del modelo supera al del regex en ≥10 puntos sin que la precisión caiga por debajo de X"). Sin esta regla fijada antes, el resultado se racionaliza después — siempre.

**Integración final:** se marca la versión ganadora como "producción" en el Model Registry de MLflow, se levanta/reinicia el servicio `api` (sección 10) para que la cargue, y el Job-Tracker apunta su llamada HTTP a ese endpoint — con el enrutamiento de tres salidas de la sección 3 decidido del lado del Job-Tracker según la probabilidad que devuelve `/predict`. El repo del Job-Tracker no recibe ningún archivo del modelo.

**En producción — ciclo de mejora continua:** cada decisión que Carlos tome sobre un post en la cola REVISAR se registra con `origen_etiqueta=revision_produccion` y se suma al dataset para el siguiente reentrenamiento. Esto resuelve de forma natural lo que de otro modo sería un problema abierto de mantenimiento (el contenido del feed cambia con el tiempo — nuevos formatos, campañas, ciclos de contratación — y un modelo entrenado una vez y olvidado se degrada).

## 12. Auditoría final: lote de examen nunca visto

**[REFINAMIENTO, a partir de una idea de Carlos]** Aparte de la validación cruzada (que se usa *durante* el desarrollo, para ir ajustando modelo/umbrales/embeddings), se separa desde el primer día un lote fijo de ~500 posts etiquetados a mano que **nunca se usa para entrenar, ni para elegir el modelo, ni para calibrar los umbrales** — ni una sola vez, ni de pasada. Se toca exactamente una vez, al final, cuando el modelo ya está terminado:

- El modelo predice sobre esos 500 posts por primera vez.
- Se compara contra la etiqueta humana de ese mismo lote.
- Ese resultado — y solo ese — es el número que se reporta como resultado final del proyecto (informe académico y post de LinkedIn).
- El mismo lote sirve para correr ahí mismo el baseline de regex y el de TF-IDF (sección 6), dejando los tres métodos comparados sobre exactamente los mismos posts nunca vistos.

Con ~150 positivos esperados en un lote de 500 (a la tasa observada del 22%), el margen de error de la medición baja de ±11.8 puntos (holdout de 52 positivos) a aproximadamente ±7 puntos — más confiable, y más fácil de explicar que la validación cruzada porque no requiere justificar la metodología para que el número se entienda.

**Regla que no se negocia:** este lote se aparta antes de generar embeddings de entrenamiento y antes de aplicar el agrupamiento de casi-duplicados de la sección 9 — ningún casi-duplicado de estos 500 posts puede terminar en el conjunto de entrenamiento, o la auditoría deja de ser válida por la misma razón que motivó H-4.

## 13. Métrica de éxito y seguimiento

- **Principal: recall de la clase `vacante`**, medido con `StratifiedGroupKFold`, en el punto de operación de la curva PR elegido deliberadamente (sección 9). Meta inicial 70-80%, **ajustable una vez se conozca el baseline** (sección 6).
- **Secundaria: precisión**, en ese mismo punto de operación.
- **Comparación contra baselines** (regex y TF-IDF) con test de McNemar.
- **[NUEVO — MLflow, reemplaza el `historial_evaluaciones.csv` manual de la v2 anterior]** Cada corrida (baseline de regex, baseline de TF-IDF, y cada combinación probada de modelo de embeddings/clasificador) se registra como un **run**, combinando dos formas de guardar métricas:
  - **`autolog`** (`mlflow.sklearn.autolog()`) para lo que entrena con scikit-learn (`MLPClassifier`, la regresión logística del baseline TF-IDF) — parámetros del modelo y métricas estándar, sin código adicional.
  - **Logging manual** (`mlflow.log_metric()` / `mlflow.log_param()`) para lo específico del proyecto que `autolog` no conoce: el recall en el punto de operación elegido (la métrica de negocio real, no una genérica), el recall desglosado por `origen_etiqueta`, el resultado del test de McNemar, qué modelo de embeddings y qué longitud de truncamiento se usó, y el veredicto contra la meta de 70-80%.
  - El run guarda también el artefacto entrenado. Esto es lo que responde de forma concreta y comparable "qué modelo usar": se ven todos los experimentos lado a lado en la interfaz de MLflow en vez de tener que recordar o buscar en un archivo qué combinación dio mejor resultado. También sirve para ver la tendencia del recall a lo largo de las 2 semanas de recolección, con el gráfico ya listo para el informe y el post de LinkedIn.
- **Pruebas unitarias (pytest)** sobre la parte determinística (hash, dedupe, agrupamiento de casi-duplicados, combinación de etiquetas) — se prueba lo que es verificable de forma binaria, se mide con métricas lo que no.

## 14. `config.py` — claves a centralizar

- Nombre y versión del modelo de embeddings (bajo evaluación: MiniLM 128 tokens vs. e5-base 512 tokens — sección 9).
- Rutas de datos y modelo.
- Nombres de clases y su mapeo numérico.
- **Dos umbrales de decisión** (alto y bajo, para las tres salidas de la sección 3), no uno solo.
- Umbral de similitud para agrupar casi-duplicados (0.95 propuesto).
- Semilla aleatoria para reproducibilidad.
- Ventana de tiempo y regla de corte del modo sombra (sección 11).
- Nombre del experimento de MLflow y ruta de `mlruns/` (sección 13).
- **[NUEVO]** Nombre del modelo en el Model Registry y qué stage se considera "producción" (sección 10) — usado por `serving/app.py` para saber cuál cargar.
- **[NUEVO]** Comportamiento de respaldo si `/predict` falla o no responde (sección 10) — del lado del Job-Tracker, no de este proyecto, pero se documenta aquí como el contrato que ambos deben respetar.

## 15. Ideas para después (fuera de alcance de esta fase)

- Reemplazar/complementar el scoring por keywords del paso 2 con búsqueda vectorial (embeddings del perfil vs. embeddings de vacante, similitud coseno).
- Sub-clasificación granular del ruido, si el análisis de errores del modelo binario lo justifica.
