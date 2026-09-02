"""Punto de entrada inicial para la aplicación de etiquetado.
pantalla para cargar y etiquetar publicaciones del feed
"""

import hashlib
import json
from pathlib import Path

import streamlit as st

from config import LABELS_DIR,RAW_DATA_DIR

LABELS_FILE = LABELS_DIR / "labels.json"

def calculate_post_id(description:str,author_profile:str) -> str:
    """Genera un identificador único para una publicación del feed de linkedin."""
    content = description + author_profile
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def read_json_file(file_path:Path) -> list[dict]:
    """Lee un archivo JSON y devuelve sus publicaciones."""
    try:
        with file_path.open("r", encoding="utf-8") as file:
            content = json.load(file)

        if isinstance(content, list):
            return content

        if isinstance(content,dict):
            posts = content.get("posts", content.get('data',[])) 

            if isinstance(posts,list):
                return posts

    except (OSError, json.JSONDecodeError) as error:
        st.warning(f"No se pudo leer {file_path.name}: {error}")

    return []


def load_feed_posts(raw_data_dir:Path) -> list[dict]:
    """Busca y combina publicaciones del feed de LinkedIn. como los archivos 
    pueden traer ofertas de empleo de linkedin y get on board aca solo dejamos los
    posts de linkedin que estan en el feed
    """
    posts_by_id = {}

    for file_path in sorted(raw_data_dir.glob("*.json")):
        posts = read_json_file(file_path)

        for post in posts:
            if not isinstance(post, dict):
                continue

            if post.get("fuente") != "linkedin_feed":
                continue

            description  = str(post.get("descripcion", "")).strip()
            author_profile = str(post.get("autor_perfil", "")).strip()

            if not description:
                continue

            post_id = calculate_post_id(description,author_profile)

            normalized_post = {
                **post,
                "post_id": post_id,
                "descripcion": description,
                "autor_perfil": author_profile,
            }

            posts_by_id[post_id] = normalized_post

    return list(posts_by_id.values())


def load_labels(labels_file: Path) -> dict:
    """Carga las etiquetas guardadas anteriormente."""
    if not labels_file.exists():
        return {}

    try:
        with labels_file.open("r", encoding="utf-8") as file:
            content = json.load(file)
        return content if isinstance(content, dict) else {}  

    except (OSError, json.JSONDecodeError) as error:
        st.warning(f"No se pudieron leer las etiquetas: {error}")
        return {}

def save_labels(labels: dict, labels_file: Path) -> None:
    """Guarda las etiquetas en un archivo JSON."""

    labels_file.parent.mkdir(parents=True, exist_ok=True)

    with labels_file.open("w", encoding="utf-8") as file:
        json.dump(labels, file, ensure_ascii=False, indent=2)

def create_label(post: dict, label: str, source: str) -> dict:     
    """Construye el registro de una etiqueta."""
    return {
        "post_id": post["post_id"],
        "label": label,
        "origen_etiqueta": source,
        "descripcion": post["descripcion"],
        "autor_perfil": post["autor_perfil"],
    }

def apply_automatic_labels(posts: list[dict], labels: dict) -> bool:
    """Etiqueta automáticamente las publicaciones con tarjeta de empleo.
    como algunas publicaciones del feed linkedin tienen una tarjeta de empleo,
    cuando se hace la extraccion ya biene marcada con una etiqueta aca lo que hacemos
    es convertir esa etiqueta en una de empleo 
    """
    labels_changed = False

    for post in posts:
        post_id = post["post_id"]
        has_job_card = post.get("tiene_tarjeta_empleo", False)

        if has_job_card and post_id not in labels:
            labels[post_id] = create_label(
                post,
                label="vacante",
                source="tarjeta_empleo",
            )
            labels_changed = True

    return labels_changed

## punto de entrada
def main() -> None:
    """Muestra la aplicación de etiquetado."""
    st.set_page_config(
        page_title="Etiquetador del feed",
        page_icon="🧭",
    )

    st.title("Etiquetador de publicaciones del feed")

    posts = load_feed_posts(RAW_DATA_DIR)
    labels = load_labels(LABELS_FILE)

    if apply_automatic_labels(posts, labels):
        save_labels(labels, LABELS_FILE)

    ## devuelve un arreglo de los post que no se pudieron etiquetar automaticamente
    # con la funcion apply_automatic_labels()
    pending_posts = [post for post in posts if post["post_id"] not in labels]

    st.metric("Publicaciones pendientes", len(pending_posts))

    if not pending_posts:
        st.success("No hay publicaciones pendientes de etiquetar.")
        return

    post = pending_posts[0]
    description = post["descripcion"]
    #  Tomamos los primeros 120 caracteres como título
    title = description.splitlines()[0][:120]

    st.subheader(title)
    st.caption(f"Autor: {post['autor_perfil'] or 'No disponible'}")
    st.write(description)

    first_column, second_column = st.columns(2)

    with first_column:
        if st.button("Vacante", use_container_width=True):
            labels[post["post_id"]] = create_label(
                post,
                label="vacante",
                source="humano",
            )
            save_labels(labels, LABELS_FILE)
            st.rerun()

    with second_column:
        if st.button("No es vacante", use_container_width=True):
            labels[post["post_id"]] = create_label(
                post,
                label="no_vacante",
                source="humano",
            )
            save_labels(labels, LABELS_FILE)
            st.rerun()

if __name__ == "__main__":
    main()
