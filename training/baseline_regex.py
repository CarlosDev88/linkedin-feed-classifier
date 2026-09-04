"""Evalúa el algoritmo actual contra el dataset etiquetado."""

import re
import unicodedata
from pathlib import Path

import mlflow
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score

from config import (
    CLASS_TO_ID,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    PROCESSED_DATA_DIR,
)
from baseline_rules import (
    CORE,
    PATRONES_CANDIDATO,
    PATRONES_OFERTA,
    PATRONES_RUIDO_SOCIAL,
    SECUNDARIO,
    SENALES_APLICACION,
    SENALES_CONTRATACION,
    UMBRAL_REVISAR,
    UMBRAL_TALVEZ,
    VETO,
)

DATASET_FILE = PROCESSED_DATA_DIR / "dataset_entrenamiento.csv"
PREDICTIONS_FILE = PROCESSED_DATA_DIR / "baseline_regex_predictions.csv"


def normalizar_texto(texto: str | None) -> str:
    """Limpia el texto para poder compararlo con las reglas."""

    if not texto:
        return ""

    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(
        caracter for caracter in texto if not unicodedata.combining(caracter)
    )

    return re.sub(r"\s+", " ", texto).strip().lower()


def contar_patrones(texto: str, patrones: list[str]) -> int:
    """Cuenta cuántos patrones aparecen dentro del texto."""

    return sum(1 for patron in patrones if re.search(patron, texto))


def detectar_intencion(titulo: str, descripcion: str) -> str:
    """Distingue entre oferta, candidato, ruido social o texto dudoso."""

    texto = normalizar_texto(f"{titulo} {descripcion}")

    puntajes = {
        "OFERTA": contar_patrones(texto, PATRONES_OFERTA),
        "CANDIDATO": contar_patrones(texto, PATRONES_CANDIDATO),
        "RUIDO_SOCIAL": contar_patrones(
            texto,
            PATRONES_RUIDO_SOCIAL,
        ),
    }

    maximo = max(puntajes.values())

    if maximo == 0:
        return "INDETERMINADO"

    ganadores = [tipo for tipo, valor in puntajes.items() if valor == maximo]

    if len(ganadores) > 1:
        return "INDETERMINADO"

    return ganadores[0]


def es_vacante(texto: str) -> bool:
    """Comprueba si el texto parece una publicación de empleo."""

    tiene_contratacion = any(senal in texto for senal in SENALES_CONTRATACION)

    tiene_aplicacion = any(senal in texto for senal in SENALES_APLICACION)

    tiene_email = bool(
        re.search(
            r"[\w.+-]+@[\w-]+\.[\w.]+",
            texto,
        )
    )

    tiene_link_corto = "lnkd.in" in texto

    return tiene_contratacion and (tiene_aplicacion or tiene_email or tiene_link_corto)


def extraer_contacto(texto: str) -> tuple[list[str], list[str]]:
    """Extrae correos y enlaces encontrados en la publicación."""

    emails = re.findall(
        r"[\w.+-]+@[\w-]+\.[\w.]+",
        texto,
    )

    links = re.findall(
        r"https?://\S+|lnkd\.in/\S+",
        texto,
    )

    return emails, links


def clasificar_post_feed(descripcion: str) -> dict | None:
    """Aplica las reglas actuales a una publicación del feed."""

    texto = normalizar_texto(descripcion)

    if not es_vacante(texto):
        return None

    intencion = detectar_intencion("", descripcion)

    if intencion in ("CANDIDATO", "RUIDO_SOCIAL"):
        return None

    vetos = [veto for veto in VETO if veto in texto]

    if "angular" in vetos and "react" in texto:
        vetos.remove("angular")

    if vetos:
        return None

    score = sum(peso for palabra, peso in CORE.items() if palabra in texto)

    score += sum(peso for palabra, peso in SECUNDARIO.items() if palabra in texto)

    if score < UMBRAL_TALVEZ:
        return None

    emails, links = extraer_contacto(descripcion)

    decision = "REVISAR" if score >= UMBRAL_REVISAR else "TAL_VEZ"

    return {
        "decision": decision,
        "score": score,
        "emails": emails,
        "links": links,
    }


def load_dataset(dataset_file: Path) -> pd.DataFrame:
    """Lee y valida el CSV construido anteriormente."""

    if not dataset_file.exists():
        raise FileNotFoundError(f"No existe el dataset: {dataset_file}")

    dataset = pd.read_csv(dataset_file)

    required_columns = {
        "post_id",
        "texto",
        "label",
        "label_id",
        "origen_etiqueta",
        "autor_perfil",
    }

    missing_columns = required_columns - set(dataset.columns)

    if missing_columns:
        raise ValueError("Faltan columnas en el dataset: " f"{sorted(missing_columns)}")

    if dataset.empty:
        raise ValueError("El dataset está vacío.")

    dataset["texto"] = dataset["texto"].fillna("").astype(str)
    dataset["label"] = dataset["label"].fillna("").astype(str)
    dataset["origen_etiqueta"] = dataset["origen_etiqueta"].fillna("").astype(str)

    dataset["label_id"] = pd.to_numeric(
        dataset["label_id"],
        errors="raise",
    ).astype(int)

    valid_ids = set(CLASS_TO_ID.values())

    if not set(dataset["label_id"]).issubset(valid_ids):
        raise ValueError(f"Los label_id deben pertenecer a {valid_ids}.")

    labels_esperadas = dataset["label"].map(CLASS_TO_ID)

    if not labels_esperadas.equals(dataset["label_id"]):
        raise ValueError("label y label_id no coinciden en alguna fila.")

    return dataset


def predecir_fila(fila: pd.Series) -> int:
    """Convierte una publicación en 0 o 1 usando el algoritmo actual."""

    origen = str(fila["origen_etiqueta"])
    texto = str(fila["texto"])

    if origen == "tarjeta_empleo":
        return 1

    resultado = clasificar_post_feed(texto)

    return int(resultado is not None)


def calcular_metricas(
    valores_reales: list[int],
    valores_predichos: list[int],
) -> dict[str, float | int]:
    """Calcula las métricas principales del baseline."""

    matriz = confusion_matrix(
        valores_reales,
        valores_predichos,
        labels=[0, 1],
    )

    tn, fp, fn, tp = matriz.ravel()

    return {
        "total": len(valores_reales),
        "verdaderos_negativos": int(tn),
        "falsos_positivos": int(fp),
        "falsos_negativos": int(fn),
        "verdaderos_positivos": int(tp),
        "precision": float(
            precision_score(
                valores_reales,
                valores_predichos,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                valores_reales,
                valores_predichos,
                zero_division=0,
            )
        ),
    }


def calcular_metricas_por_origen(
    dataset: pd.DataFrame,
) -> dict[str, dict[str, float | int]]:
    """Calcula resultados separados según el origen de la etiqueta."""

    resultados = {}

    for origen, grupo in dataset.groupby("origen_etiqueta"):
        resultados[str(origen)] = calcular_metricas(
            grupo["label_id"].tolist(),
            grupo["prediccion_regex"].tolist(),
        )

    return resultados


def guardar_predicciones(
    dataset: pd.DataFrame,
    predictions_file: Path,
) -> None:
    """Guarda las etiquetas reales y las predicciones del baseline."""

    columnas = [
        "post_id",
        "label",
        "label_id",
        "origen_etiqueta",
        "prediccion_regex",
    ]

    predicciones = dataset[columnas].copy()

    predicciones["acierto"] = (
        predicciones["label_id"] == predicciones["prediccion_regex"]
    )

    predictions_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    predicciones.to_csv(
        predictions_file,
        index=False,
        encoding="utf-8",
    )


def guardar_en_mlflow(
    dataset: pd.DataFrame,
    metricas: dict[str, float | int],
    metricas_por_origen: dict[str, dict[str, float | int]],
) -> None:
    """Guarda los resultados para consultarlos después en MLflow."""

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name="baseline-regex"):
        mlflow.log_param(
            "algoritmo",
            "reglas_actuales_feed_filter",
        )

        mlflow.log_param(
            "registros",
            len(dataset),
        )

        mlflow.log_param(
            "umbral_revisar",
            UMBRAL_REVISAR,
        )

        mlflow.log_param(
            "umbral_talvez",
            UMBRAL_TALVEZ,
        )

        metricas_mlflow = {
            clave: float(valor) for clave, valor in metricas.items() if clave != "total"
        }

        mlflow.log_metrics(metricas_mlflow)

        for origen, valores in metricas_por_origen.items():
            nombre_origen = re.sub(
                r"[^a-zA-Z0-9_]+",
                "_",
                origen,
            )

            metricas_origen = {
                f"{nombre_origen}_{clave}": float(valor)
                for clave, valor in valores.items()
                if clave != "total"
            }

            mlflow.log_metrics(metricas_origen)


def main() -> None:
    """Ejecuta la evaluación completa del baseline."""

    dataset = load_dataset(DATASET_FILE)

    dataset["prediccion_regex"] = dataset.apply(
        predecir_fila,
        axis=1,
    )

    metricas = calcular_metricas(
        dataset["label_id"].tolist(),
        dataset["prediccion_regex"].tolist(),
    )

    metricas_por_origen = calcular_metricas_por_origen(dataset)

    guardar_predicciones(
        dataset,
        PREDICTIONS_FILE,
    )

    guardar_en_mlflow(
        dataset,
        metricas,
        metricas_por_origen,
    )

    print(f"Dataset leído: {DATASET_FILE}")
    print(f"Predicciones guardadas en: {PREDICTIONS_FILE}")
    print(f"Registros evaluados: {metricas['total']}")
    print(f"Precision: {metricas['precision']:.4f}")
    print(f"Recall: {metricas['recall']:.4f}")

    print("\nMatriz de confusión:")
    print(f"Verdaderos negativos: " f"{metricas['verdaderos_negativos']}")
    print(f"Falsos positivos: " f"{metricas['falsos_positivos']}")
    print(f"Falsos negativos: " f"{metricas['falsos_negativos']}")
    print(f"Verdaderos positivos: " f"{metricas['verdaderos_positivos']}")

    print("\nResultados por origen:")

    for origen, valores in metricas_por_origen.items():
        print(f"\n{origen}")
        print(f"  Registros: {valores['total']}")
        print(f"  Precision: {valores['precision']:.4f}")
        print(f"  Recall: {valores['recall']:.4f}")


if __name__ == "__main__":
    main()
