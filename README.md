# Feed Intent Classifier

Proyecto para clasificar publicaciones del feed de LinkedIn como `vacante` o
`no_vacante`, con una salida intermedia para revisión humana.

## Estado actual

El repositorio contiene el scaffold inicial, la configuración Docker, el
etiquetado manual y la construcción del dataset de entrenamiento.

### Punto de partida: baseline de reglas

El algoritmo actual de expresiones regulares fue evaluado contra el dataset
etiquetado el 4 de septiembre de 2026.

- Registros evaluados: `226`
- Vacantes reales: `60`
- No vacantes reales: `166`
- Precision: `100%`
- Recall: `43.33%`
- Verdaderos negativos: `166`
- Falsos positivos: `0`
- Verdaderos positivos: `26`
- Falsos negativos: `34`

La línea base es muy precisa, pero demasiado estricta: no genera falsos
positivos, aunque deja fuera muchas vacantes reales. En las publicaciones
etiquetadas manualmente obtuvo un recall de `26.09%`; las publicaciones con
tarjeta de empleo obtuvieron un recall de `100%` porque se consideran vacantes
automáticamente.

Estos resultados son nuestro punto de comparación. El objetivo inicial del
entrenamiento será subir el recall hasta, al menos, `75%`, aceptando una
reducción controlada de la precision.

El dataset utilizado se encuentra en:

```text
data/processed/dataset_entrenamiento.csv
```

Las predicciones de esta evaluación se guardan en:

```text
data/processed/baseline_regex_predictions.csv
```

El siguiente paso es revisar los `34` falsos negativos y después comparar esta
línea base contra un modelo TF-IDF y, posteriormente, contra los modelos de
embeddings definidos en la configuración.

## Preparar el entorno

1. Copiar `.env.example` como `.env`.
2. Configurar `HOST_SCRAPER_PATH` con la ruta absoluta de la carpeta local
   `Descargas/JobTracker`.
3. Levantar los servicios:

```bash
docker compose up --build
```

La aplicación Streamlit queda disponible en `http://localhost:8501` y la API
en `http://localhost:8000/health`.

Para abrir MLflow bajo demanda:

```bash
docker compose run --rm -p 5000:5000 app mlflow ui --host 0.0.0.0
```
