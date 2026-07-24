# Gemelo Digital · Javier Díaz-Giménez — web de pruebas (Streamlit)

Chat para probar el gemelo, desplegable **gratis** en **Streamlit Community
Cloud** desde un repositorio de GitHub. Streamlit instala las dependencias en
su nube: no tienes que instalar nada en ningún servidor.

## Qué contiene

```
webapp-streamlit/
├── streamlit_app.py         ← la app (chat + RAG numpy + registro)
├── requirements.txt         ← streamlit, numpy, voyageai, anthropic
├── sistema.md               ← prompt de sistema del gemelo
├── embeddings.npy           ← vectores del corpus (2.720 × 1024, normalizados)
├── corpus.jsonl             ← texto + metadatos de cada fragmento
├── info.json                ← dimensión y modelo de los vectores
├── .gitignore               ← evita subir claves y el registro
└── .streamlit/
    └── secrets.toml.example ← plantilla de claves (las reales van en la nube)
```

> Comportamiento idéntico a `src/rag/answer.py`: voyage-4 · umbral 0.40 ·
> top_k 6 · Claude Sonnet 5.

## Despliegue en 5 pasos

### 1. Sube estos ficheros a un repositorio de GitHub
Crea un repo nuevo (recomendado **privado**) y sube **el contenido de esta
carpeta** (no la carpeta padre). Lo más simple: en el repo → *Add file* →
*Upload files* → arrastra todos los ficheros, incluida la subcarpeta
`.streamlit/`. Confirma con *Commit*.

Los ficheros del corpus (`embeddings.npy` ~11 MB, `corpus.jsonl` ~7,6 MB) caben
sin problema en un repo normal (límite 100 MB por fichero). **No subas claves**:
el `.gitignore` ya excluye `secrets.toml` y `.env`.

### 2. Entra en Streamlit Community Cloud
Ve a https://share.streamlit.io e inicia sesión **con tu cuenta de GitHub**.
Autoriza el acceso a tus repos cuando lo pida.

### 3. Crea la app
Botón **Create app** / *New app* → *Deploy a public app from GitHub*:
- **Repository:** el repo que acabas de crear.
- **Branch:** `main`.
- **Main file path:** `streamlit_app.py`.

### 4. Añade los secretos (claves)
Antes de desplegar, abre **Advanced settings → Secrets** y pega esto (con tus
valores reales):

```toml
ANTHROPIC_API_KEY = "tu-clave-anthropic"
VOYAGE_API_KEY = "tu-clave-voyage"
VOYAGE_MODEL = "voyage-4"
APP_PASSWORD = "la-contraseña-para-Javier-y-Miguel"
```

(Tus claves de Anthropic y Voyage están en el `.env` del proyecto.)

### 5. Deploy
Pulsa **Deploy**. En un par de minutos tendrás una URL pública
(`https://…streamlit.app`). Ábrela: te pedirá la contraseña; luego lanza una
pregunta del banco (`tests/preguntas.md`) para comprobar. Comparte la URL + la
contraseña con Javier y Miguel.

## Probar en local (opcional)

```bash
cd webapp-streamlit
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y rellena las claves
streamlit run streamlit_app.py
```

## Registro de preguntas y respuestas

Cada interacción se guarda en `registro.jsonl` y se descarga en **CSV** desde el
botón de la barra lateral izquierda.

⚠️ **Importante sobre la persistencia:** el disco de Streamlit Community Cloud es
**efímero** — el registro se conserva mientras la app está activa, pero se
reinicia si Streamlit reinicia o redespliega la app (p. ej. tras un rato de
inactividad). Para una sesión de pruebas, **descarga el CSV al terminar**. Si
quieres un registro central que no se pierda nunca (una hoja de cálculo con todo
lo que pregunten Javier y Miguel), se puede conectar a Google Sheets — dímelo y
lo añado.

## Notas

- Cada consulta gasta API de pago (Voyage + Anthropic, ~1–2 céntimos). Deja
  `APP_PASSWORD` puesta y fija límites de gasto en ambas consolas.
- La app gratuita puede "dormirse" tras un rato sin uso; despierta sola al
  abrir la URL (tarda unos segundos).
- Para actualizar el corpus: se regenera el índice, se re-exportan
  `embeddings.npy` + `corpus.jsonl` y se vuelven a subir al repo.
