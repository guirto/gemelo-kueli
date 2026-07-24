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

## Parámetros (solo desde Secrets, no desde la web)

La web ya **no** muestra sliders: `k` y umbral se fijan desde los Secrets, para
que los testers no los toquen. Son opcionales (por defecto 6 y 0.40):

```toml
TOP_K = "6"       # nº de fragmentos a recuperar
UMBRAL = "0.40"   # umbral de similitud mínima
```

## Registro permanente en Google Sheets (recomendado)

Por defecto el registro se guarda en `registro.jsonl` (descargable en CSV desde
la barra lateral), pero el disco de Streamlit gratis es **efímero** y se pierde
al reiniciar. Para un registro central que no se pierde nunca —y para que la app
**reutilice respuestas ya dadas** (si una pregunta ya se contestó, la lee de la
hoja y no vuelve a gastar API)— conéctala a Google Sheets:

1. **Crea una hoja de cálculo** en Google Sheets (vacía). Copia su **ID**: en la
   URL, lo que va entre `/d/` y `/edit`.
2. **Crea una cuenta de servicio** en Google Cloud:
   - Ve a https://console.cloud.google.com → crea un proyecto (o usa uno).
   - *APIs y servicios → Biblioteca* → busca **Google Sheets API** → *Habilitar*.
   - *APIs y servicios → Credenciales* → *Crear credenciales* → *Cuenta de
     servicio*. Ponle nombre y créala.
   - En la cuenta creada → pestaña *Claves* → *Agregar clave* → *Crear clave
     nueva* → **JSON**. Se descarga un fichero JSON.
3. **Comparte la hoja** con la cuenta de servicio: abre el JSON, copia el
   `client_email` (algo como `...@...iam.gserviceaccount.com`), y en tu Google
   Sheet pulsa *Compartir* y dale acceso de **Editor** a ese correo.
4. **Pega las credenciales en los Secrets de Streamlit** (Settings → Secrets),
   añadiendo el ID de la hoja y el JSON como tabla `[gcp_service_account]`:

   ```toml
   GSHEET_ID = "el-id-de-tu-hoja"

   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "...@...iam.gserviceaccount.com"
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```
   (Copia cada campo del JSON descargado. El `private_key` va con las `\n` tal
   cual aparecen en el JSON.)
5. **Reinicia la app** (*Manage app → Reboot*). A partir de ahí, cada pregunta se
   guarda en la hoja, y si alguien repite una pregunta ya contestada, la app
   muestra la respuesta guardada sin llamar a las APIs.

Si no configuras esto, la app funciona igual pero solo con el registro local
efímero (descarga el CSV al terminar cada sesión).

## Notas

- Cada consulta nueva gasta API de pago (~1–2 céntimos); las repetidas, si tienes
  Google Sheets, son gratis. Deja `APP_PASSWORD` puesta y fija límites de gasto
  en Anthropic y Voyage.
- Para actualizar el corpus: se regenera el índice, se re-exportan y se vuelve a
  cifrar `corpus.jsonl` → `corpus.jsonl.enc`, y se sube al repo.
