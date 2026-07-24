# Gemelo Digital · Javier Díaz-Giménez — web de pruebas (Streamlit)

Chat para probar el gemelo, desplegable **gratis** en **Streamlit Community
Cloud** desde un repositorio de GitHub. Streamlit instala las dependencias en
su nube: no hay que instalar nada en ningún servidor.

El corpus va **cifrado** en el repo (`corpus.jsonl.enc`), así que el repositorio
puede ser **público** sin exponer el texto con copyright de Javier: solo se
puede leer con la clave `APP_DATA_KEY`, que vive en los *Secrets* de Streamlit y
nunca en el repo.

## Qué contiene

```
webapp-streamlit/
├── streamlit_app.py         ← la app (chat + RAG numpy + descifrado + registro)
├── requirements.txt         ← streamlit, numpy, voyageai, anthropic, cryptography
├── sistema.md               ← prompt de sistema del gemelo
├── embeddings.npy           ← vectores del corpus (2.720 × 1024; solo números)
├── corpus.jsonl.enc         ← texto + metadatos del corpus, CIFRADO
├── info.json                ← dimensión y modelo de los vectores
├── .gitignore               ← evita subir claves, el registro y el corpus en claro
└── .streamlit/
    └── secrets.toml.example ← plantilla de claves (las reales van en la nube)
```

> Comportamiento idéntico a `src/rag/answer.py`: voyage-4 · umbral 0.40 ·
> top_k 6 · Claude Sonnet 5.

## Despliegue en 5 pasos

### 1. Sube estos ficheros a un repositorio de GitHub
Crea un repo (**puede ser público**, el corpus va cifrado) y sube **el contenido
de esta carpeta**. Lo más simple: en el repo → *Add file* → *Upload files* →
arrastra todos los ficheros, incluida la subcarpeta `.streamlit/`. Confirma con
*Commit*.

⚠️ Sube `corpus.jsonl.enc` (cifrado). **Nunca** subas el corpus en texto plano ni
la clave: el `.gitignore` ya excluye `corpus.jsonl`, `secrets.toml`, `.env` y
`CLAVE_no_subir.txt`.

### 2. Entra en Streamlit Community Cloud
https://share.streamlit.io → inicia sesión **con tu cuenta de GitHub**.

### 3. Crea la app
**Create app** → *Deploy a public app from GitHub*:
- **Repository:** tu repo.
- **Branch:** `main`.
- **Main file path:** `streamlit_app.py`.

### 4. Añade los secretos
En **Advanced settings → Secrets**, pega esto con tus valores reales:

```toml
ANTHROPIC_API_KEY = "tu-clave-anthropic"
VOYAGE_API_KEY = "tu-clave-voyage"
VOYAGE_MODEL = "voyage-4"
APP_PASSWORD = "la-contraseña-para-Javier-y-Miguel"
APP_DATA_KEY = "la-clave-de-cifrado-que-te-dio-Claude"
```

(Tus claves de Anthropic y Voyage están en el `.env` del proyecto. La
`APP_DATA_KEY` te la ha facilitado Claude en el chat.)

### 5. Deploy
Pulsa **Deploy**. En un par de minutos tendrás la URL pública
(`https://…streamlit.app`). Ábrela, mete la contraseña y prueba una pregunta del
banco (`tests/preguntas.md`). Comparte URL + contraseña con Javier y Miguel.

## Probar en local (opcional)

```bash
cd webapp-streamlit
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # rellena las claves + APP_DATA_KEY
streamlit run streamlit_app.py
```

## Sobre el cifrado del corpus

- `corpus.jsonl.enc` está cifrado con **Fernet (AES-128)**. Sin `APP_DATA_KEY`
  es ruido ilegible, así que es seguro tenerlo en un repo público.
- La app lo descifra **en memoria** al arrancar; nunca escribe el texto en claro
  en disco.
- Si pierdes la clave, se puede regenerar volviendo a cifrar el corpus.
- Guarda la `APP_DATA_KEY` solo donde tú controles (gestor de contraseñas y los
  Secrets de Streamlit). No la pongas en el repo ni la compartas con los testers.

## Registro y notas

- Cada interacción se guarda en `registro.jsonl`, descargable en **CSV** desde la
  barra lateral. El disco de Streamlit gratis es **efímero**: descarga el CSV al
  terminar cada sesión. (Si quieres registro central permanente, se puede
  conectar a Google Sheets.)
- Cada consulta gasta API de pago (~1–2 céntimos). Deja `APP_PASSWORD` puesta y
  fija límites de gasto en Anthropic y Voyage.
- Para actualizar el corpus: se regenera el índice, se re-exportan y se vuelve a
  cifrar `corpus.jsonl` → `corpus.jsonl.enc`, y se sube al repo.
