#!/usr/bin/env python3
"""
Gemelo Digital JDG — web de pruebas (Streamlit Community Cloud).

Chat para probar el gemelo, desplegable gratis desde un repo de GitHub en
Streamlit Community Cloud (instala él las dependencias en su nube).

  - Búsqueda de similitud con numpy sobre los vectores exportados del corpus
    (embeddings.npy + corpus.jsonl), SIN Chroma ni dependencias pesadas.
  - Claves y ajustes desde st.secrets (o variables de entorno en local).
  - Acceso protegido con contraseña (APP_PASSWORD).
  - Registro de cada pregunta/respuesta, descargable en CSV.

Comportamiento idéntico a src/rag/answer.py:
voyage-4 · umbral 0.40 · top_k 6 · Claude Sonnet 5.
"""

import os
import io
import csv
import json
import pathlib
from datetime import datetime, timezone

import numpy as np
import streamlit as st

HERE = pathlib.Path(__file__).resolve().parent
PROMPT_FILE = HERE / "sistema.md"
EMB_FILE = HERE / "embeddings.npy"
CORPUS_FILE = HERE / "corpus.jsonl"          # texto plano (solo en local, opcional)
CORPUS_ENC_FILE = HERE / "corpus.jsonl.enc"  # corpus cifrado (el que va al repo)
LOG_PATH = HERE / "registro.jsonl"

DEFAULT_K = 6
DEFAULT_THRESHOLD = 0.40


def cfg(nombre, defecto=""):
    """Lee de st.secrets primero y, si no, de variables de entorno."""
    try:
        if nombre in st.secrets:
            return str(st.secrets[nombre])
    except Exception:
        pass
    return os.environ.get(nombre, defecto)


VOYAGE_MODEL = cfg("VOYAGE_MODEL", "voyage-4")
CLAUDE_MODEL = cfg("CLAUDE_MODEL", "claude-sonnet-5")
MAX_OUTPUT_TOKENS = int(cfg("MAX_OUTPUT_TOKENS", "3000") or "3000")


# ------------------------------ Carga cacheada --------------------------------

def _leer_corpus_bytes():
    """Devuelve el corpus.jsonl en bytes: texto plano si existe (local), o
    descifrando corpus.jsonl.enc con la clave APP_DATA_KEY de los Secrets."""
    if CORPUS_FILE.exists():
        return CORPUS_FILE.read_bytes()
    clave = cfg("APP_DATA_KEY")
    if not clave:
        raise RuntimeError(
            "Falta APP_DATA_KEY en los Secrets para descifrar el corpus.")
    from cryptography.fernet import Fernet
    return Fernet(clave.encode()).decrypt(CORPUS_ENC_FILE.read_bytes())


@st.cache_resource(show_spinner="Cargando el corpus…")
def cargar_corpus():
    emb = np.load(EMB_FILE)
    textos, metas = [], []
    for line in _leer_corpus_bytes().decode("utf-8").splitlines():
        line = line.strip()
        if line:
            rec = json.loads(line)
            textos.append(rec["text"])
            metas.append(rec["meta"])
    return emb, textos, metas


@st.cache_resource(show_spinner=False)
def voyage_client():
    import voyageai
    return voyageai.Client(api_key=cfg("VOYAGE_API_KEY"))


@st.cache_resource(show_spinner=False)
def anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=cfg("ANTHROPIC_API_KEY"))


# ------------------------------ RAG (numpy) -----------------------------------

def retrieve(question, emb, textos, metas, k=DEFAULT_K, threshold=DEFAULT_THRESHOLD):
    vo = voyage_client()
    q = vo.embed([question], model=VOYAGE_MODEL, input_type="query",
                 truncation=True).embeddings[0]
    q = np.asarray(q, dtype=np.float32)
    n = np.linalg.norm(q)
    if n:
        q = q / n
    sims = emb @ q
    idx = np.argsort(-sims)[:k]
    chunks = []
    for i in idx:
        sim = float(sims[i])
        if sim < threshold:
            continue
        chunks.append({"text": textos[i], "sim": round(sim, 3), "meta": metas[i]})
    return chunks


def build_context(chunks):
    parts, sources, seen = [], [], set()
    for i, c in enumerate(chunks, 1):
        m = c["meta"]
        titulo = m.get("titulo") or m.get("fuente", "")
        tipo = m.get("tipo", "")
        fecha = m.get("fecha", "")
        label = f"[{i}] {titulo}" + (f" ({fecha})" if fecha else "") + f" [{tipo}]"
        parts.append(f"{label}\n{c['text']}")
        doc_id = m.get("doc_id") or titulo
        if doc_id not in seen:
            seen.add(doc_id)
            sources.append({"titulo": titulo, "tipo": tipo, "fecha": fecha,
                            "url": m.get("url", ""), "sim": c["sim"]})
    return "\n\n---\n\n".join(parts), sources


def ask(question, emb, textos, metas, k=DEFAULT_K, threshold=DEFAULT_THRESHOLD):
    chunks = retrieve(question, emb, textos, metas, k=k, threshold=threshold)
    fallback = len(chunks) == 0
    system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

    if fallback:
        sources = []
        user_msg = (f"PREGUNTA: {question}\n\n"
                    "No se han encontrado fragmentos relevantes en el corpus. "
                    "Usa el mensaje de redirección definido en tus instrucciones.")
    else:
        context_block, sources = build_context(chunks)
        user_msg = (f"PREGUNTA: {question}\n\n"
                    f"FRAGMENTOS RECUPERADOS DEL CORPUS (ordenados por relevancia):\n\n{context_block}")

    client = anthropic_client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    answer = "".join(
        b.text for b in message.content if getattr(b, "type", None) == "text"
    ).strip()
    return {"answer": answer, "sources": sources,
            "n_chunks": len(chunks), "fallback": fallback}


# ------------------------------ Registro --------------------------------------

def log_interaction(rec):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def registro_csv_bytes():
    filas = []
    if LOG_PATH.exists():
        with open(LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        filas.append(json.loads(line))
                    except Exception:
                        continue
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["fecha_utc", "pregunta", "respuesta", "fuentes", "n_chunks", "fuera_de_corpus"])
    for r in filas:
        w.writerow([r.get("ts", ""), r.get("pregunta", ""), r.get("respuesta", ""),
                    " | ".join(r.get("fuentes", [])), r.get("n_chunks", ""),
                    "sí" if r.get("fallback") else "no"])
    return buf.getvalue().encode("utf-8-sig")


# ------------------------------ Interfaz --------------------------------------

st.set_page_config(page_title="Gemelo Digital · Javier Díaz-Giménez", page_icon="🧠")


def puerta_contrasena():
    password = cfg("APP_PASSWORD")
    if not password:
        return True
    if st.session_state.get("authed"):
        return True
    st.title("🧠 Gemelo Digital · Javier Díaz-Giménez")
    st.caption("Acceso restringido a las pruebas.")
    intento = st.text_input("Contraseña", type="password")
    if intento:
        if intento == password:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    return False


if not puerta_contrasena():
    st.stop()

emb, textos, metas = cargar_corpus()

st.title("🧠 Gemelo Digital · Javier Díaz-Giménez — *pruebas*")
st.caption(
    "IA entrenada con las publicaciones y grabaciones de Javier Díaz-Giménez. "
    "Responde sobre macroeconomía, pensiones, fiscalidad, mercado laboral y "
    "política económica basándose en su corpus. Es una IA, no el propio Javier. "
    "Las preguntas y respuestas se registran para su revisión."
)

with st.sidebar:
    st.header("Ajustes")
    k = st.slider("Fragmentos a recuperar (k)", 1, 12, DEFAULT_K)
    umbral = st.slider("Umbral de similitud", 0.0, 0.9, DEFAULT_THRESHOLD, 0.05)
    st.divider()
    st.download_button("⬇️ Descargar registro (CSV)", data=registro_csv_bytes(),
                       file_name="registro_gemelo.csv", mime="text/csv")

faltan = [k2 for k2, v in (("VOYAGE_API_KEY", cfg("VOYAGE_API_KEY")),
                           ("ANTHROPIC_API_KEY", cfg("ANTHROPIC_API_KEY"))) if not v]
if faltan:
    st.warning("Faltan claves en los *Secrets* de la app: " + ", ".join(faltan))

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

pregunta = st.chat_input("Escribe tu pregunta para el gemelo…")
if pregunta:
    st.session_state.messages.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        if faltan:
            st.error("No puedo responder: faltan las claves de API.")
        else:
            with st.spinner("Pensando…"):
                try:
                    res = ask(pregunta, emb, textos, metas, k=k, threshold=umbral)
                    salida = res["answer"]
                    if not res["fallback"] and res["sources"]:
                        salida += "\n\n---\n**Fuentes recuperadas del corpus:**\n"
                        for s in res["sources"]:
                            fecha = f" — {s['fecha']}" if s.get("fecha") else ""
                            salida += f"- {s['titulo']} *[{s['tipo']}]*{fecha}  ·  sim={s['sim']}\n"
                    st.markdown(salida)
                    st.session_state.messages.append({"role": "assistant", "content": salida})
                    log_interaction({
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "pregunta": pregunta,
                        "respuesta": res["answer"],
                        "fuentes": [s["titulo"] for s in res["sources"]],
                        "n_chunks": res["n_chunks"],
                        "fallback": res["fallback"],
                    })
                except Exception as e:
                    st.error(f"Error al consultar el gemelo: {type(e).__name__}: {e}")
