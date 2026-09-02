# Feed Intent Classifier

Proyecto para clasificar publicaciones del feed de LinkedIn como `vacante` o
`no_vacante`, con una salida intermedia para revisión humana.

## Estado actual

El repositorio contiene el scaffold inicial y la configuración Docker. La
lógica de etiquetado, entrenamiento, evaluación y carga del modelo se agregará
en etapas posteriores.

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

