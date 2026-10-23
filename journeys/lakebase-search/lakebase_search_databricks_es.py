# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 2 de 4 · Lakebase Search</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Lakebase Search
# MAGIC #### Duración: 35 minutos
# MAGIC
# MAGIC *Recorrido 2 de 4 de la ruta de Desarrolladores de aplicaciones. JSONB buscó valores exactos; este recorrido encuentra filas por sus palabras y por su significado.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Una analista de fraude y PLD busca entre cientos de notas de alertas. A veces conoce el término exacto: una
# MAGIC **CLABE**, una **CURP**, la palabra "chargeback". A veces solo sabe qué pasó: "el cliente perdió el control
# MAGIC de su cuenta", que las notas describen como un dispositivo nuevo, un cambio de SIM o un número de teléfono
# MAGIC cambiado, sin decir nunca "takeover". Un solo tipo de búsqueda se pierde la mitad.
# MAGIC
# MAGIC **Lakebase Search** pone los dos dentro de tu base de datos de Lakebase, junto a los datos operativos:
# MAGIC `lakebase_text` ordena las coincidencias de palabras con **BM25**, `lakebase_vector` encuentra filas por
# MAGIC significado con un índice de **vecinos más cercanos aproximados (ANN)**, y una sola consulta SQL combina
# MAGIC las dos en una **búsqueda híbrida** que puede filtrar y hacer joins como cualquier otra consulta. En este
# MAGIC laboratorio lo activas, generas los embeddings de 40 notas con un modelo real y ejecutas las tres.
# MAGIC
# MAGIC Las notas están en inglés, como el modelo de embeddings, así que las búsquedas también.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Activar Lakebase Search** en tu proyecto e instalar sus extensiones.
# MAGIC 2. **Ordenar coincidencias de palabras con BM25**, y ver en qué supera al `ts_rank` clásico de Postgres.
# MAGIC 3. **Buscar por significado** con embeddings reales y un índice `lakebase_ann`.
# MAGIC 4. **Combinar las dos en una búsqueda híbrida** con Reciprocal Rank Fusion, con filtros y joins sobre tablas vivas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Lakebase Search:** una configuración del proyecto que agrega tres extensiones de Postgres: `lakebase_text` (búsqueda por palabras), `lakebase_vector` (búsqueda vectorial) y `lakebase_tokenizer` (tokenización, incluidos chino, japonés y coreano).
# MAGIC - **BM25:** el puntaje de relevancia estándar de la búsqueda por palabras. Premia las palabras raras, las repetidas y los textos cortos y enfocados, con estadísticas de toda la tabla. `lakebase_text` lo calcula con un índice `lakebase_bm25`.
# MAGIC - **Embedding:** una lista de números que un modelo genera para un texto, de modo que textos con significado parecido tengan números parecidos. Este recorrido usa `databricks-gte-large-en`, que devuelve 1,024 números por texto.
# MAGIC - **Índice ANN:** encuentra los embeddings más cercanos sin comparar contra todas las filas. `lakebase_ann` reparte los vectores en grupos (IVF) y los comprime (RaBitQ); en una tabla pequeña simplemente los compara todos.
# MAGIC - **Búsqueda híbrida:** combinar los resultados por palabras y por vectores. **Reciprocal Rank Fusion (RRF)** (fusión por posición recíproca) suma `1 / (60 + posición)` de cada lista, así que las filas que quedan bien en las dos salen primero.
# MAGIC
# MAGIC Encontrarás más términos en `docs/glosario-es.md`, en la carpeta del taller.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Configuración
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Antes de empezar</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Ejecuta una vez <code>00-setup/setup_databricks_es</code> para crear tu proyecto y tu rama y cargar el banco.
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>.
# MAGIC     Necesitas: <strong>Lakebase Search activado en tu proyecto</strong> (el paso A3 explica cómo) y el
# MAGIC     endpoint de embeddings <code>databricks-gte-large-en</code>.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Instala el driver y elige tu rama
# MAGIC
# MAGIC Ejecuta las siguientes tres celdas antes que nada. Instalan el driver de Postgres, actualizan el SDK de
# MAGIC Databricks si la versión de tu entorno es anterior a la API de Lakebase, y toman `LB_PROJECT`,
# MAGIC `LB_BRANCH` y `LB_SCHEMA` de los widgets de la parte superior del notebook. `LB_BRANCH` toma por defecto
# MAGIC la rama que creó `00-setup/setup_databricks_es`. Cambia un widget solo si usaste otro nombre de
# MAGIC proyecto o de rama.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils, lang="es");

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `sesión iniciada como` y tu correo, seguido de tu proyecto, tu rama y tu esquema:
# MAGIC
# MAGIC ```
# MAGIC sesión iniciada como alex.kim@example.com
# MAGIC   LB_PROJECT = bank-alex-kim
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... es anterior a la API de Lakebase</code>: vuelve a ejecutar la celda de instalación y la de reinicio, y luego esta.</li>
# MAGIC       <li><code>Llena LB_BRANCH en los widgets de la parte superior del notebook</code>: escribe el nombre de tu rama en el campo <code>LB_BRANCH</code> y vuelve a ejecutar esta celda.</li>
# MAGIC       <li>Los widgets muestran un nombre de rama viejo: ejecuta <code>dbutils.widgets.removeAll()</code> en una celda nueva y vuelve a ejecutar esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Carga los helpers
# MAGIC
# MAGIC Esta celda carga `connect()` de `common/scripts/`, que abre una conexión a tu rama con un token de inicio
# MAGIC de sesión de tu identidad de Databricks, y define dos helpers pequeños para el modelo de embeddings:
# MAGIC
# MAGIC - `embed(texts)` envía una lista de textos al endpoint `databricks-gte-large-en` y devuelve un embedding
# MAGIC   (1,024 números) por texto.
# MAGIC - `to_vector(numbers)` escribe un embedding en el formato de texto que Postgres lee como `vector`.
# MAGIC
# MAGIC En los pasos siguientes, el bloque de SQL de cada paso es la sentencia que se ejecuta en tu rama. La
# MAGIC celda de Python de abajo solo envía esa sentencia e imprime el resultado.

# COMMAND ----------

import os, sys, requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, client

EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "databricks-gte-large-en")

def embed(texts: list[str]) -> list[list[float]]:
    """One embedding per text, from the embedding model's serving endpoint."""
    w = client()
    r = requests.post(f"{w.config.host}/serving-endpoints/{EMBED_ENDPOINT}/invocations",
                      headers=w.config.authenticate(), json={"input": texts}, timeout=120)
    r.raise_for_status()
    return [row["embedding"] for row in r.json()["data"]]

def to_vector(numbers: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in numbers) + "]"

print(f"helpers listos; endpoint de embeddings: {EMBED_ENDPOINT} ({len(embed(['test'])[0])} dimensiones)")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `helpers listos; endpoint de embeddings: databricks-gte-large-en (1024 dimensiones)`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>404 Client Error</code>: el nombre del endpoint está mal o no existe en este workspace. Revisa <strong>Serving</strong> en la barra lateral izquierda y corrige <code>EMBED_ENDPOINT</code> en esta celda.</li>
# MAGIC       <li><code>403 Client Error</code>: no tienes permiso para consultar el endpoint. Pídele a tu instructor <code>CAN_QUERY</code> sobre él.</li>
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ### A3. Activa Lakebase Search
# MAGIC
# MAGIC Activa Lakebase Search en la configuración de tu proyecto:
# MAGIC
# MAGIC 1. En tu proyecto de Lakebase, haz clic en **Settings** en la navegación de la izquierda.
# MAGIC 2. En **Lakebase Search**, haz clic en **Enable Lakebase Search**.
# MAGIC
# MAGIC Tu proyecto es el del widget `LB_PROJECT`, `bank-<tu nombre de correo>`. Ábrelo desde la app
# MAGIC **Lakebase Postgres**.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">Advertencia: al activar Lakebase Search</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li>Se reinician todos los cómputos de tu proyecto y se cortan las conexiones activas</li>
# MAGIC       <li>Las extensiones <code>lakebase_vector</code>, <code>lakebase_text</code> y <code>lakebase_tokenizer</code> quedan disponibles para instalar</li>
# MAGIC       <li>No se puede desactivar una vez activado</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC Después ejecuta la siguiente celda. Instala las tres extensiones en tu rama; mientras Lakebase Search no
# MAGIC esté activado, se detiene y te regresa aquí. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_text;
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE;   -- CASCADE también instala pgvector
# MAGIC CREATE SCHEMA IF NOT EXISTS tokenizer_ext;
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_tokenizer WITH SCHEMA tokenizer_ext;
# MAGIC ```

# COMMAND ----------

try:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE")
            cur.execute("CREATE SCHEMA IF NOT EXISTS tokenizer_ext")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_tokenizer WITH SCHEMA tokenizer_ext")
            cur.execute("SELECT extname, extversion FROM pg_extension "
                        "WHERE extname LIKE 'lakebase%' ORDER BY extname")
            installed = cur.fetchall()
except Exception as e:
    if "shared_preload_libraries" in str(e):
        raise SystemExit("Lakebase Search todavía no está activado en tu proyecto. Sigue los dos pasos de A3, "
                         "espera a que se reinicien los cómputos y vuelve a ejecutar esta celda.") from None
    raise

print("Lakebase Search está activado. Extensiones instaladas:")
for name, version in installed:
    print(f"  {name} {version}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Lakebase Search está activado. Extensiones instaladas:
# MAGIC   lakebase_text 0.1.3
# MAGIC   lakebase_tokenizer 0.2.0
# MAGIC   lakebase_vector 1.1.1
# MAGIC ```
# MAGIC
# MAGIC Los números de versión pueden ser más nuevos en tu workspace.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Lakebase Search todavía no está activado en tu proyecto</code>: haz los dos pasos de arriba en tu propio proyecto y vuelve a ejecutar esta celda.</li>
# MAGIC       <li>Un error de conexión justo después de activarlo: los cómputos se están reiniciando. Espera unos segundos y vuelve a ejecutar esta celda.</li>
# MAGIC       <li>No aparece la sección <strong>Lakebase Search</strong> en Settings: tu proyecto necesita Postgres 16 o superior. El proyecto del taller usa 17.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Carga las notas de los analistas

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Carga 40 notas
# MAGIC
# MAGIC `search_note`, en la carpeta de este recorrido, tiene 40 notas cortas que los analistas escribieron sobre
# MAGIC alertas: robo de cuenta (account takeover), estructuración, mulas de dinero, fraude con tarjeta, phishing,
# MAGIC aclaraciones, problemas con SPEI y CoDi, y falsos positivos. Algunas están escritas para que la búsqueda
# MAGIC por palabras tropiece: varias tomas de cuenta nunca usan la palabra "takeover". Volver a ejecutar es
# MAGIC seguro; las filas tienen ids fijos. El SQL, en resumen:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE IF NOT EXISTS bank.search_note (
# MAGIC     note_id INT PRIMARY KEY, account_id TEXT REFERENCES bank.account,
# MAGIC     category TEXT, ts TIMESTAMPTZ, writeup TEXT);
# MAGIC INSERT INTO bank.search_note VALUES (...) ON CONFLICT (note_id) DO NOTHING;
# MAGIC SELECT category, count(*) FROM bank.search_note GROUP BY category ORDER BY count(*) DESC;
# MAGIC ```

# COMMAND ----------

with open(os.path.join(os.getcwd(), "search_notes.sql")) as f:
    notes_sql = f.read()

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(notes_sql)
        cur.execute("SELECT category, count(*) FROM bank.search_note GROUP BY category ORDER BY count(*) DESC, category")
        by_category = cur.fetchall()

print(f"{sum(n for _, n in by_category)} notas en bank.search_note:")
for category, n in by_category:
    print(f"  {category:10} {n}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC 40 notas en bank.search_note:
# MAGIC   fraud      13
# MAGIC   cleared    9
# MAGIC   aml        6
# MAGIC   dispute    5
# MAGIC   phishing   4
# MAGIC   mule       3
# MAGIC ```
# MAGIC
# MAGIC Las categorías son valores de la tabla y se quedan en inglés: `aml` es PLD, `dispute` es aclaración,
# MAGIC `mule` es mula de dinero y `cleared` es un caso cerrado sin hallazgos.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Agrega las columnas de búsqueda
# MAGIC
# MAGIC Dos columnas nuevas en las mismas filas: `writeup_tsv`, las palabras de la nota en la forma normalizada que
# MAGIC usa la búsqueda por palabras (Postgres la mantiene al día solo), y `embedding`, el significado de la nota
# MAGIC como 1,024 números. La celda envía al modelo, en una sola llamada, las notas que todavía no tienen
# MAGIC embedding, y guarda los resultados. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS writeup_tsv tsvector
# MAGIC   GENERATED ALWAYS AS (to_tsvector('english', writeup)) STORED;
# MAGIC ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS embedding vector(1024);
# MAGIC UPDATE bank.search_note SET embedding = '<1,024 números>'::vector WHERE note_id = <id>;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS writeup_tsv tsvector "
                    "GENERATED ALWAYS AS (to_tsvector('english', writeup)) STORED")
        cur.execute("ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS embedding vector(1024)")
        cur.execute("SELECT note_id, writeup FROM bank.search_note WHERE embedding IS NULL ORDER BY note_id")
        missing = cur.fetchall()
        if missing:
            for (note_id, _), numbers in zip(missing, embed([w for _, w in missing])):
                cur.execute("UPDATE bank.search_note SET embedding = %s::vector WHERE note_id = %s",
                            [to_vector(numbers), note_id])
        cur.execute("SELECT count(embedding), count(*) FROM bank.search_note")
        with_embedding, total = cur.fetchone()
        cur.execute("SELECT writeup_tsv FROM bank.search_note WHERE note_id = 5")
        sample_tsv = cur.fetchone()[0]

print(f"embeddings generados ahora: {len(missing)}; {with_embedding} de {total} notas tienen embedding")
print(f"la nota 5 como palabras: {sample_tsv}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** en la primera ejecución (si vuelves a ejecutar, se generan 0):
# MAGIC
# MAGIC ```
# MAGIC embeddings generados ahora: 40; 40 de 40 notas tienen embedding
# MAGIC la nota 5 como palabras: 'ad':20 'beneficiari':18 'carrier':6 'code':10 'new':14 'one':8 'one-tim':7 'report':3 'sim':1,15 'swap':2 'time':9 'went':11
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** los dos tipos de búsqueda trabajan con columnas en la misma fila que la nota. `writeup_tsv` guarda las palabras sin terminaciones ni palabras comunes ("carrier" queda `carrier`, "codes" queda `code`), con su posición.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Crea los índices de búsqueda
# MAGIC
# MAGIC Crea los dos índices **después** de cargar los datos: BM25 calcula sus estadísticas sobre toda la tabla al
# MAGIC crear el índice, y `VACUUM` las actualiza después de una carga grande. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS search_note_bm25 ON bank.search_note USING lakebase_bm25 (writeup_tsv);
# MAGIC CREATE INDEX IF NOT EXISTS search_note_ann  ON bank.search_note USING lakebase_ann (embedding vector_cosine_ops);
# MAGIC VACUUM bank.search_note;
# MAGIC SELECT lakebase_ann_index_info('bank.search_note_ann');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE INDEX IF NOT EXISTS search_note_bm25 ON bank.search_note USING lakebase_bm25 (writeup_tsv)")
        cur.execute("CREATE INDEX IF NOT EXISTS search_note_ann ON bank.search_note "
                    "USING lakebase_ann (embedding vector_cosine_ops)")
        cur.execute("VACUUM bank.search_note")
        cur.execute("SELECT lakebase_ann_index_info('bank.search_note_ann')")
        ann_info = cur.fetchone()[0]

print("índices listos: search_note_bm25 (lakebase_bm25), search_note_ann (lakebase_ann)")
print(f"lakebase_ann_index_info: {ann_info}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC índices listos: search_note_bm25 (lakebase_bm25), search_note_ann (lakebase_ann)
# MAGIC lakebase_ann_index_info: {"default_epsilon":1.899999976158142,"default_probes":[],"lists":[],"version":"_2"}
# MAGIC ```
# MAGIC
# MAGIC `"lists":[]` quiere decir que el índice no tiene grupos IVF: con 40 filas, `lakebase_ann` compara la
# MAGIC consulta contra todos los vectores, lo que es exacto y rápido a este tamaño. Con millones de filas los
# MAGIC reparte en grupos y solo revisa los más cercanos.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Búsqueda por palabras con BM25

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Encuentra un término exacto
# MAGIC
# MAGIC Una analista busca todas las notas que mencionan una **CLABE**. El operador `<@>` devuelve el puntaje BM25
# MAGIC como número **negativo**, así que la nota más relevante tiene el puntaje más bajo y la consulta ordena de
# MAGIC menor a mayor. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', 'CLABE'), 'bank.search_note_bm25') AS score, writeup
# MAGIC   FROM bank.search_note
# MAGIC  ORDER BY score
# MAGIC  LIMIT 3;
# MAGIC ```

# COMMAND ----------

BM25 = "writeup_tsv <@> to_bm25query(to_tsvector('english', %(q)s), 'bank.search_note_bm25')"

def keyword_search(q: str, limit: int = 5):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT note_id, {BM25} AS score, writeup FROM bank.search_note "
                        f"ORDER BY score LIMIT %(limit)s", {"q": q, "limit": limit})
            return cur.fetchall()

print("BM25 para 'CLABE':")
for note_id, score, writeup in keyword_search("CLABE", 3):
    print(f"  {note_id:>2}  {score:7.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC BM25 para 'CLABE':
# MAGIC   29   -2.864  SPEI transfer returned by the receiving bank because the CLABE had a t
# MAGIC   22   -2.654  Fake invoice email from a supplier changed the CLABE for payment. Comm
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** BM25 encuentra términos exactos, como códigos, ids y nombres. Solo las notas que
# MAGIC contienen "CLABE" tienen puntaje; una nota que no contiene ninguna palabra de la búsqueda no aparece.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. BM25 contra el `ts_rank` clásico
# MAGIC
# MAGIC Postgres siempre ha tenido búsqueda por palabras: `@@` encuentra coincidencias y `ts_rank` les da puntaje.
# MAGIC Para "account takeover", la consulta clásica necesita **las dos** palabras en la nota; BM25 ordena todas
# MAGIC las notas que tengan **cualquiera** de las dos, y le da más peso a la palabra rara ("takeover") que a la
# MAGIC común ("account"). Las dos consultas:
# MAGIC
# MAGIC ```sql
# MAGIC -- clásica
# MAGIC SELECT note_id, ts_rank(writeup_tsv, plainto_tsquery('english', 'account takeover')) AS rank
# MAGIC   FROM bank.search_note WHERE writeup_tsv @@ plainto_tsquery('english', 'account takeover')
# MAGIC  ORDER BY rank DESC;
# MAGIC -- Lakebase Search
# MAGIC SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', 'account takeover'), 'bank.search_note_bm25') AS score
# MAGIC   FROM bank.search_note ORDER BY score LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT note_id, ts_rank(writeup_tsv, plainto_tsquery('english', %s)) AS rank, writeup "
                    "FROM bank.search_note WHERE writeup_tsv @@ plainto_tsquery('english', %s) "
                    "ORDER BY rank DESC, note_id", ["account takeover", "account takeover"])
        classic = cur.fetchall()

print(f"ts_rank clásico: {len(classic)} notas")
for note_id, rank, writeup in classic:
    print(f"  {note_id:>2}  {rank:.3f}  {writeup[:70]}")
print("\nBM25: las 5 primeras")
for note_id, score, writeup in keyword_search("account takeover"):
    print(f"  {note_id:>2}  {score:7.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC ts_rank clásico: 2 notas
# MAGIC    1  0.099  Account takeover suspected: password reset, then a SPEI transfer to a
# MAGIC    2  0.099  Confirmed account takeover. Customer never requested the credential ch
# MAGIC
# MAGIC BM25: las 5 primeras
# MAGIC    2   -4.265  Confirmed account takeover. Customer never requested the credential ch
# MAGIC    1   -4.265  Account takeover suspected: password reset, then a SPEI transfer to a
# MAGIC    9   -1.810  AML review opened for structuring across three accounts owned by the s
# MAGIC   13   -1.673  Possible money mule: a student account receives transfers from strange
# MAGIC   22   -1.612  Fake invoice email from a supplier changed the CLABE for payment. Comm
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** BM25 ordena las coincidencias parciales en vez de descartarlas, y pesa cada palabra
# MAGIC según qué tan rara es en toda la tabla. Pero sigue viendo solo palabras: las notas 3 a 7 describen tomas
# MAGIC de cuenta sin esas palabras, y ninguna de las dos consultas las encuentra.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Busca por significado

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Pregunta en lenguaje natural
# MAGIC
# MAGIC La celda convierte la pregunta en un embedding con el mismo modelo y ordena las notas por distancia coseno
# MAGIC con `<=>` (menor es más parecido), usando el índice `lakebase_ann`. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, embedding <=> '<embedding de la pregunta>'::vector AS distance, writeup
# MAGIC   FROM bank.search_note
# MAGIC  ORDER BY distance
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

QUESTION = "customer lost control of their account"
question_vector = to_vector(embed([QUESTION])[0])

def semantic_search(vector: str, limit: int = 5):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT note_id, embedding <=> %(v)s::vector AS distance, writeup FROM bank.search_note "
                        "ORDER BY distance LIMIT %(limit)s", {"v": vector, "limit": limit})
            return cur.fetchall()

print(f"Lo más parecido en significado a '{QUESTION}':")
for note_id, distance, writeup in semantic_search(question_vector):
    print(f"  {note_id:>2}  {distance:.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** el orden es el mismo en cada ejecución; el último decimal de una distancia puede variar un poco:
# MAGIC
# MAGIC ```
# MAGIC Lo más parecido en significado a 'customer lost control of their account':
# MAGIC    2  0.250  Confirmed account takeover. Customer never requested the credential ch
# MAGIC    4  0.273  Customer says someone else got into the mobile app; the email on file
# MAGIC    6  0.340  Security questions answered correctly by a caller whose voice did not
# MAGIC    7  0.336  Session cookies reused from a foreign IP address. Customer was asleep
# MAGIC   35  0.352  New phone set up by the customer in the branch, identity checked in pe
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el modelo relaciona "lost control of their account" con "someone else got into the
# MAGIC mobile app" y "a caller whose voice did not match", que no comparten palabras con la pregunta. La nota 35
# MAGIC es un caso cerrado que solo suena parecido; E1 la filtra. Las notas 6 y 7 salen un poco fuera de orden
# MAGIC (0.340 antes que 0.336): el índice es *aproximado*, primero compara vectores comprimidos, así que dos casi
# MAGIC empates se pueden invertir. Es lo que cambia un índice ANN a cambio de velocidad en tablas grandes.

# COMMAND ----------

# MAGIC %md
# MAGIC ### D2. Dónde fallan los vectores, y el plan que usa Postgres
# MAGIC
# MAGIC La misma búsqueda por significado para el término exacto "CLABE" devuelve notas que tratan *sobre*
# MAGIC transferencias, no las que contienen el código: el significado es la herramienta equivocada para términos
# MAGIC exactos. La celda también muestra el plan de la consulta, para confirmar que los dos tipos de búsqueda usan
# MAGIC su índice. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN SELECT note_id FROM bank.search_note ORDER BY embedding <=> '<embedding>'::vector LIMIT 5;
# MAGIC ```

# COMMAND ----------

print("Búsqueda por significado para 'CLABE':")
for note_id, distance, writeup in semantic_search(to_vector(embed(["CLABE"])[0]), 3):
    print(f"  {note_id:>2}  {distance:.3f}  {writeup[:70]}")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("EXPLAIN SELECT note_id FROM bank.search_note ORDER BY embedding <=> %s::vector LIMIT 5",
                    [question_vector])
        vector_plan = [r[0] for r in cur.fetchall()]
        cur.execute(f"EXPLAIN SELECT note_id FROM bank.search_note ORDER BY {BM25} LIMIT 5",
                    {"q": "account takeover"})
        keyword_plan = [r[0] for r in cur.fetchall()]

print("\nPlanes:")
print("  vector:  ", next(line.strip() for line in vector_plan if "Index Scan" in line))
print("  palabras:", next(line.strip() for line in keyword_plan if "Index Scan" in line))

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Búsqueda por significado para 'CLABE':
# MAGIC    8  0.443  Structuring pattern: SPEI transfers just under the internal reporting
# MAGIC   34  0.466  Payroll run triggered a velocity alert: two hundred transfers to emplo
# MAGIC    9  0.466  AML review opened for structuring across three accounts owned by the s
# MAGIC
# MAGIC Planes:
# MAGIC   vector:   ->  Index Scan using search_note_ann on search_note  (cost=0.00..8.50 rows=40 width=12)
# MAGIC   palabras: ->  Index Scan using search_note_bm25 on search_note  (cost=0.00..8.50 rows=40 width=12)
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la búsqueda por palabras y la vectorial fallan cada una donde la otra acierta, y por eso
# MAGIC el siguiente paso las combina. Las dos son recorridos de índice normales dentro de Postgres.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Búsqueda híbrida

# COMMAND ----------

# MAGIC %md
# MAGIC ### E1. Combina las dos listas, filtra y haz un join
# MAGIC
# MAGIC Una sola consulta toma los 20 primeros de cada búsqueda, le da a cada nota `1 / (60 + posición)` por cada
# MAGIC lista en la que aparece (**Reciprocal Rank Fusion**), quita los casos cerrados con un `WHERE` normal y hace
# MAGIC un join con la cuenta para mostrar su estado actual. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC WITH v AS (SELECT note_id, RANK() OVER (ORDER BY d) AS rank FROM (
# MAGIC              SELECT note_id, embedding <=> '<embedding de la pregunta>'::vector AS d
# MAGIC                FROM bank.search_note ORDER BY d LIMIT 20) x),
# MAGIC      k AS (SELECT note_id, RANK() OVER (ORDER BY s) AS rank FROM (
# MAGIC              SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', '<pregunta>'), 'bank.search_note_bm25') AS s
# MAGIC                FROM bank.search_note ORDER BY s LIMIT 20) y)
# MAGIC SELECT n.note_id, n.category, a.status AS account_status, v.rank AS vector_rank, k.rank AS keyword_rank,
# MAGIC        COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf
# MAGIC   FROM bank.search_note n
# MAGIC   JOIN bank.account a USING (account_id)
# MAGIC   LEFT JOIN v USING (note_id)
# MAGIC   LEFT JOIN k USING (note_id)
# MAGIC  WHERE (v.note_id IS NOT NULL OR k.note_id IS NOT NULL)
# MAGIC    AND n.category <> 'cleared'
# MAGIC  ORDER BY rrf DESC, n.note_id
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

HYBRID = f"""
WITH v AS (SELECT note_id, RANK() OVER (ORDER BY d) AS rank FROM (
             SELECT note_id, embedding <=> %(v)s::vector AS d
               FROM bank.search_note ORDER BY d LIMIT 20) x),
     k AS (SELECT note_id, RANK() OVER (ORDER BY s) AS rank FROM (
             SELECT note_id, {BM25} AS s
               FROM bank.search_note ORDER BY s LIMIT 20) y)
SELECT n.note_id, n.category, a.status, v.rank, k.rank,
       COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf, n.writeup
  FROM bank.search_note n
  JOIN bank.account a USING (account_id)
  LEFT JOIN v USING (note_id)
  LEFT JOIN k USING (note_id)
 WHERE (v.note_id IS NOT NULL OR k.note_id IS NOT NULL)
   AND n.category <> 'cleared'
 ORDER BY rrf DESC, n.note_id
 LIMIT 5
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(HYBRID, {"q": QUESTION, "v": question_vector})
        hybrid = cur.fetchall()

print(f"Búsqueda híbrida para '{QUESTION}' (sin casos cerrados):")
print(f"  {'nota':>4}  {'categoría':9} {'cuenta':14} {'vector':>6} {'palabras':>8}  {'rrf':>6}")
for note_id, category, status, vrank, krank, rrf, writeup in hybrid:
    print(f"  {note_id:>4}  {category:9} {status:14} {vrank or '-':>6} {krank or '-':>8}  {rrf:.4f}  {writeup[:45]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Búsqueda híbrida para 'customer lost control of their account' (sin casos cerrados):
# MAGIC   nota  categoría cuenta         vector palabras     rrf
# MAGIC      2  fraud     good_standing       1        2  0.0325  Confirmed account takeover. Customer never re
# MAGIC      1  fraud     watch               6        5  0.0305  Account takeover suspected: password reset, t
# MAGIC      7  fraud     watch               3       11  0.0300  Session cookies reused from a foreign IP addr
# MAGIC     39  aml       watch               7       10  0.0292  Customer cannot explain the source of a large
# MAGIC     21  phishing  watch              19        1  0.0291  Caller posing as bank security asked the cust
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** las notas que las dos búsquedas ponen arriba salen primero. La nota 7 es apenas la
# MAGIC 11 por palabras pero la 3 por significado, y la nota 21 es la 1 por palabras pero la 19 por significado;
# MAGIC combinadas, las dos quedan entre las 5 primeras. El falso positivo de D1 (la nota 35) desaparece, y cada
# MAGIC fila muestra el estado actual de su cuenta. Filtrar y hacer joins funciona como en cualquier consulta,
# MAGIC porque la búsqueda corre en la misma base de datos que las cuentas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Errores de escritura en ids

# COMMAND ----------

# MAGIC %md
# MAGIC ### F1. Encuentra una cuenta con un id mal escrito
# MAGIC
# MAGIC BM25 y los vectores trabajan con palabras y significado; para códigos cortos con un error, `pg_trgm` de
# MAGIC Postgres compara pedazos de tres caracteres. Una analista escribe `CTA-10234`, con un dígito de menos. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS pg_trgm;
# MAGIC SELECT account_id, similarity(account_id, 'CTA-10234') AS sim
# MAGIC   FROM bank.account
# MAGIC  ORDER BY sim DESC
# MAGIC  LIMIT 3;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cur.execute("SELECT account_id, similarity(account_id, %s) AS sim FROM bank.account "
                    "ORDER BY sim DESC, account_id LIMIT 3", ["CTA-10234"])
        matches = cur.fetchall()

print("Cuentas más parecidas a 'CTA-10234':")
for account_id, sim in matches:
    print(f"  {account_id}  similitud={sim:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Cuentas más parecidas a 'CTA-10234':
# MAGIC   CTA-100234  similitud=0.750
# MAGIC   CTA-100235  similitud=0.500
# MAGIC   CTA-100240  similitud=0.400
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la cuenta correcta sale primero a pesar del error. Cada tipo de búsqueda tiene su
# MAGIC función: BM25 para palabras, vectores para significado y trigramas para la escritura.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>¿Lakebase Search o Databricks Vector Search?</strong></summary>
# MAGIC
# MAGIC Usa Lakebase Search para buscar en **filas operativas vivas** dentro de la base de datos de tu app, donde
# MAGIC los resultados deben reflejar las últimas escrituras y hacer joins con otras tablas, como aquí. Usa
# MAGIC Databricks Vector Search para colecciones grandes de documentos que se sincronizan por lotes desde el
# MAGIC lakehouse, como miles de PDF.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Ajustes</strong></summary>
# MAGIC
# MAGIC - **BM25:** `k1` (1.2 por defecto) controla cuánto cuentan las palabras repetidas; `b` (0.75 por defecto)
# MAGIC   controla cuánto se penalizan las notas largas. Se fijan con `CREATE INDEX ... WITH (k1 = 1.5)` o `ALTER INDEX ... SET`.
# MAGIC - **Vectores:** `SET lakebase_ann.probes` revisa más grupos para encontrar más resultados correctos en
# MAGIC   tablas grandes, y `SET lakebase_ann.prefilter = on` aplica filtros baratos antes de la búsqueda.
# MAGIC - **RRF:** la constante 60 y las listas de 20 son un punto de partida; ajústalos con preguntas reales de
# MAGIC   tus analistas.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Índices y escalar a cero</strong></summary>
# MAGIC
# MAGIC Los dos índices se guardan con los datos, así que sobreviven cuando tu cómputo se suspende y vuelven con
# MAGIC la siguiente consulta; no se reconstruye nada. Después de una carga grande, ejecuta `VACUUM` para que las
# MAGIC estadísticas de BM25 incluyan las filas nuevas.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Por qué `<@>` devuelve un número negativo?</strong></summary>
# MAGIC
# MAGIC Es el puntaje BM25 con el signo invertido, así que ordenar de menor a mayor, como una distancia, pone primero la nota más relevante.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué búsqueda encuentra las notas sobre una CLABE, y cuál encuentra "lost control of their account"?</strong></summary>
# MAGIC
# MAGIC BM25 encuentra el término exacto CLABE; la búsqueda vectorial encuentra las tomas de cuenta descritas con otras palabras. La búsqueda híbrida encuentra las dos.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué se crea el índice BM25 después de cargar los datos?</strong></summary>
# MAGIC
# MAGIC BM25 calcula sus estadísticas sobre toda la tabla al crear el índice; `VACUUM` las actualiza después de cargar más filas.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusión
# MAGIC
# MAGIC En este laboratorio activaste Lakebase Search, generaste los embeddings de 40 notas con un modelo real y
# MAGIC las buscaste de tres formas. Puntos clave:
# MAGIC
# MAGIC 1. **Lakebase Search es una configuración del proyecto más tres extensiones,** dentro del mismo Postgres que tus datos.
# MAGIC 2. **BM25 (`lakebase_text`) es para palabras exactas,** y ordena mejor que el `ts_rank` clásico.
# MAGIC 3. **Los vectores (`lakebase_vector`) son para el significado,** con embeddings reales y un índice ANN.
# MAGIC 4. **La búsqueda híbrida es una sola consulta SQL:** RRF combina las dos listas, y los filtros y joins funcionan como siempre.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de aplicaciones:** <a href="$../data-api/data_api_databricks_es">API de datos de Lakebase →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
