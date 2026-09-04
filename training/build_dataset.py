"""Construye el dataset de entrenamiento a partir de las etiquetas guardadas."""

import json
from pathlib import Path

import pandas as pd

from config import CLASS_TO_ID, LABELS_DIR, PROCESSED_DATA_DIR

# de aca leemos las publicaciones etiquetadas previamente
LABELS_FILE = LABELS_DIR / "labels.json"

# aca guardamos ya prosesada la info lista para hacer el entrenamiento
DATASET_FILE = PROCESSED_DATA_DIR / "dataset_entrenamiento.csv"

# el origen de las etiquetas
VALID_LABEL_SOURCES = {
    "tarjeta_empleo",
    "humano",
    "revision_produccion",
}

# columndas que tendra el archivo dataset_entrenamiento.csv
OUTPUT_COLUMNS = [
    "post_id",
    "texto",
    "label",
    "label_id",
    "origen_etiqueta",
    "autor_perfil",
]

def normalize_text(value:object) ->str:
    """Convierte un valor recibido del JSON en texto limpio."""
    if value is None:
        return ""

    return str(value).strip()

def load_label_records(labels_file : Path) -> list[dict]:
    """Lee y valida las etiquetas guardadas en un archivo JSON."""
    if not labels_file.exists():
        # lanza un error
        raise FileNotFoundError(f"No existe el archivo de etiquetas: {labels_file}")

    try:
        with labels_file.open("r", encoding="utf-8") as file:
            content = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"El archivo de etiquetas no contiene un JSON válido: {error}") from error

    if not isinstance(content, dict):
        raise ValueError("El archivo de etiquetas debe contener un objeto JSON.")

    records = []

    for record_key, raw_record in content.items():
        if not isinstance(raw_record,dict):
            raise ValueError(f"La etiqueta {record_key} no tiene un formato válido.")

        post_id = normalize_text(raw_record.get("post_id"))
        expected_post_id = normalize_text(record_key)

        if post_id != expected_post_id:
            raise ValueError(
                f"El post_id de la etiqueta {record_key} " "no coincide con su clave."
            )

        label = normalize_text(raw_record.get("label"))

        if label not in CLASS_TO_ID:
            raise ValueError(f"Etiqueta no válida para {post_id}: {label!r}.")

        description = normalize_text(raw_record.get("descripcion"))

        if not description :
            raise ValueError(f"La publicación {post_id} no tiene descripción.")

        source = normalize_text(raw_record.get("origen_etiqueta"))

        if source not in VALID_LABEL_SOURCES:
            raise ValueError(f"Origen no válido para {post_id}: {source!r}.")

        records.append(
            {
                "post_id": post_id,
                "texto": description,
                "label": label,
                "label_id": CLASS_TO_ID[label],
                "origen_etiqueta": source,
                "autor_perfil": normalize_text(raw_record.get("autor_perfil")),
            }
        )

    return records

# esta funcion toma los registros extraidos de los json etiquetados y devulve y dataframe de pandas
# esto trasforma el json en una estrcutura de datos de talbas y columnas
def build_dataset(records: list[dict]) -> pd.DataFrame:
    """Construye una tabla ordenada y sin publicaciones repetidas."""
    if not records:
        raise ValueError("No hay etiquetas para construir el dataset.")
    # aca tomamos los registros ya parseados en forma de [{...}] y las columnas definidas previamente
    dataset = pd.DataFrame(records, columns=OUTPUT_COLUMNS)

#eliminamos duplicados
    dataset = dataset.drop_duplicates(
        subset=["post_id"],
        keep="first",
    )

#ordenamos el dataset por el id del post
    dataset = dataset.sort_values("post_id")
    dataset = dataset.reset_index(drop=True)
    return dataset

def save_dataset(dataset: pd.DataFrame, dataset_file: Path) -> None:
    """Guarda el dataset en formato CSV."""
    dataset_file.parent.mkdir(parents=True, exist_ok=True)

    dataset.to_csv(
        dataset_file,
        index=False,
        encoding="utf-8",
    )


def main() -> None:
    """Ejecuta todo el proceso de construcción del dataset."""
    records = load_label_records(LABELS_FILE)
    dataset = build_dataset(records)
    save_dataset(dataset, DATASET_FILE)

    print(f"Dataset guardado en: {DATASET_FILE}")
    print(f"Registros: {len(dataset)}")

    print("\nRegistros por etiqueta:")
    print(dataset["label"].value_counts().sort_index().to_string())

    print("\nRegistros por origen:")
    print(dataset["origen_etiqueta"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
