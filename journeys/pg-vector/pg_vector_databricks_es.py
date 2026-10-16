# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones: Recorrido 2 de 6 · Desarrolladores de agentes: Recorrido 4 de 5 · Búsqueda por similitud de vectores</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Búsqueda por similitud de vectores
# MAGIC #### Duración: 20 minutos
# MAGIC
# MAGIC *Recorrido 2 de 6 para Desarrolladores de aplicaciones y 4 de 5 para Desarrolladores de agentes. JSONB buscó coincidencias exactas; este recorrido ordena filas por qué tan parecidas son.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Una gestora de portafolio tiene Quetzal Tecnologia (`INS-QTZL`) y quiere los instrumentos más
# MAGIC parecidos, para encontrar un sustituto o una cobertura. "Más parecido" no es una columna que puedas
# MAGIC filtrar; es un juicio sobre todo el perfil. Es una pregunta de similitud.
# MAGIC
# MAGIC La respuesta habitual es un servicio aparte de búsqueda vectorial. Con la extensión **pgvector**,
# MAGIC Postgres guarda un embedding (una lista de números) en cada fila y ordena las filas por distancia con
# MAGIC SQL, junto a tus datos operativos. **Una nota honesta:** este recorrido arma sus embeddings con un hash
# MAGIC determinista del texto de cada instrumento, no con un modelo de embeddings real, así que el orden
# MAGIC muestra el mecanismo, no una similitud financiera real.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Agregar una columna de vectores** a una tabla con la extensión pgvector.
# MAGIC 2. **Guardar un embedding en cada fila** junto a sus datos operativos.
# MAGIC 3. **Ordenar filas por similitud** con una fila de referencia, en una sola consulta SQL.
# MAGIC 4. **Indexar los vectores** con HNSW para que la búsqueda siga siendo rápida a gran escala.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Embedding:** una lista de números que representa un elemento. Elementos con significado parecido quedan cerca, cuando los genera un modelo real.
# MAGIC - **pgvector:** una extensión de Postgres que agrega el tipo `vector` y operadores de distancia: `<->` (distancia en línea recta, la que usa este notebook) y `<=>` (distancia coseno).
# MAGIC - **Distancia:** qué tan separados están dos embeddings. Menor significa más parecido.
# MAGIC - **Índice HNSW:** Hierarchical Navigable Small World: un índice aproximado de vecinos más cercanos que mantiene rápida la búsqueda vectorial en millones de filas.
# MAGIC
# MAGIC Encontrarás más términos en `docs/glosario-es.md`, en la carpeta del taller.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Configuración
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Antes de empezar</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Ejecuta una vez <code>00-setup/setup_databricks_es</code> para crear tu rama y cargar el banco.
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>.
# MAGIC     Necesitas: la extensión <code>vector</code> (pgvector), que este notebook crea. No hace falta un endpoint de modelo: los embeddings son un hash determinista.
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
# MAGIC   LB_PROJECT = bank
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
# MAGIC ### A2. Carga el módulo de ayuda y la función de embeddings
# MAGIC
# MAGIC Esta celda carga `run_sql()` y `connect()` de `common/scripts/`. `run_sql()` abre una conexión a tu
# MAGIC rama, ejecuta una sentencia SQL y devuelve las filas, si hay; `connect()` te da la conexión en sí.
# MAGIC
# MAGIC Por dentro, las dos le piden a la API de Lakebase el nombre de host de tu rama, obtienen un token de
# MAGIC inicio de sesión con tu identidad de Databricks (válido por cerca de una hora) y abren una conexión
# MAGIC estándar de Postgres con `psycopg`, un driver de Postgres para Python.
# MAGIC
# MAGIC En los pasos siguientes, el bloque de SQL de cada paso es la sentencia que se ejecuta en tu rama. La
# MAGIC celda de Python de abajo solo envía esa sentencia e imprime el resultado.
# MAGIC
# MAGIC Esta celda también define `hash_to_embedding()`, que convierte un texto en un vector de 768 números con un hash, en lugar de un modelo de embeddings real.

# COMMAND ----------

import os, sys, hashlib, struct
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def hash_to_embedding(text: str, dim: int = 768) -> str:
    """Deterministic hash-based embedding for reproducibility."""
    h = hashlib.sha256(text.encode()).digest()
    values = []
    for i in range(dim):
        byte_idx = (i * 2) % len(h)
        val = (struct.unpack("B", h[byte_idx:byte_idx+1])[0] / 255.0) * 2 - 1
        values.append(f"{val:.4f}")
    return "[" + ",".join(values) + "]"

print("pgvector listo")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `pgvector listo`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> o <code>KeyError: 'LB_PROJECT'</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Prepara la tabla

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Revisa los instrumentos
# MAGIC
# MAGIC Cinco instrumentos: dos acciones de tecnología, un bono del gobierno mexicano, una canasta de acciones
# MAGIC y efectivo en pesos. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT count(*) FROM bank.instrument;
# MAGIC SELECT instrument_id, name FROM bank.instrument LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM bank.instrument")
        count = cur.fetchone()[0]
        cur.execute("SELECT instrument_id, name FROM bank.instrument LIMIT 5")
        instruments = cur.fetchall()

print(f"Revisando la tabla instrument:")
print(f"  Total de instrumentos: {count}")
print(f"  Instrumentos de ejemplo:")
for p in instruments:
    print(f"    - {p[0]}: {p[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Revisando la tabla instrument:
# MAGIC   Total de instrumentos: 5
# MAGIC   Instrumentos de ejemplo:
# MAGIC     - INS-CASH-MXN: Mexican Peso Cash
# MAGIC     - INS-SLEEVE-EQ: Equity Sleeve
# MAGIC     - INS-QTZL: Quetzal Tecnologia
# MAGIC     - INS-MBONO-10Y: Bono M 10Y (Mexico)
# MAGIC     - INS-ZAFR: Zafiro Software
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Activa pgvector
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS vector;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print(f"extensión pgvector creada")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `extensión pgvector creada`
# MAGIC
# MAGIC **Qué demuestra:** la búsqueda vectorial es una extensión de Postgres que activas, no un servicio aparte.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Agrega la columna de embeddings
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768)")
        print(f"Columna embedding agregada a bank.instrument")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Columna embedding agregada a bank.instrument`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B4. Guarda un embedding en cada fila
# MAGIC
# MAGIC La celda arma un texto para cada instrumento con su nombre, tipo y ficha, lo convierte en un vector con
# MAGIC el hash y lo escribe en la columna `embedding`. El SQL que ejecuta para cada fila:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.instrument SET embedding = '<768 números>'::vector WHERE instrument_id = '<id>';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT instrument_id, name, spec FROM bank.instrument ORDER BY instrument_id")
        instruments = cur.fetchall()

print(f"Guardando {len(instruments)} embeddings:")

with connect() as conn:
    with conn.cursor() as cur:
        for instrument_id, name, spec in instruments:
            text_for_embedding = f"{name} {spec}"
            embedding_str = hash_to_embedding(text_for_embedding, 768)
            cur.execute(
                f"UPDATE bank.instrument SET embedding = CAST(%s AS vector) WHERE instrument_id = %s",
                [embedding_str, instrument_id]
            )

print(f"  Se actualizaron {len(instruments)} instrumentos con embeddings")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Guardando 5 embeddings:
# MAGIC   Se actualizaron 5 instrumentos con embeddings
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el embedding vive en la misma fila que los datos operativos del instrumento.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Busca por similitud

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Encuentra los instrumentos más parecidos a Quetzal Tecnologia
# MAGIC
# MAGIC Toma el embedding guardado de `INS-QTZL` y ordena los demás instrumentos por su distancia (`<->`; menor
# MAGIC es más parecido). El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, embedding <-> (SELECT embedding FROM bank.instrument WHERE instrument_id = 'INS-QTZL') AS distance
# MAGIC   FROM bank.instrument
# MAGIC  WHERE instrument_id != 'INS-QTZL'
# MAGIC  ORDER BY distance
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # el instrumento de referencia y su embedding guardado (igual que pg_vector.py)
        cur.execute("SELECT instrument_id, name, embedding::text FROM bank.instrument WHERE instrument_id = %s",
                    ["INS-QTZL"])
        query_part = cur.fetchone()
        query_part_id = query_part[0]
        query_part_name = query_part[1]

query_embedding = query_part[2]

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT instrument_id, name, embedding <-> CAST(%s AS vector) AS distance "
            f"FROM bank.instrument "
            f"WHERE instrument_id != %s "
            f"ORDER BY embedding <-> CAST(%s AS vector) "
            f"LIMIT 5",
            [query_embedding, query_part_id, query_embedding]
        )
        similar_parts = cur.fetchall()

print(f"Instrumento de referencia: {query_part_id} ({query_part_name})")
print(f"\nInstrumentos más parecidos:")
for instrument_id, name, distance in similar_parts:
    print(f"  {instrument_id}: {name} (distancia: {distance:.4f})")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** de una ejecución de prueba:
# MAGIC
# MAGIC ```
# MAGIC Instrumento de referencia: INS-QTZL (Quetzal Tecnologia)
# MAGIC
# MAGIC Instrumentos más parecidos:
# MAGIC   INS-CASH-MXN: Mexican Peso Cash (distancia: 23.3074)
# MAGIC   INS-MBONO-10Y: Bono M 10Y (Mexico) (distancia: 23.6040)
# MAGIC   INS-SLEEVE-EQ: Equity Sleeve (distancia: 23.9502)
# MAGIC   INS-ZAFR: Zafiro Software (distancia: 23.9834)
# MAGIC ```
# MAGIC
# MAGIC El mismo hash da los mismos números en cada ejecución.
# MAGIC
# MAGIC **Qué demuestra:** una sola consulta SQL ordena filas por similitud, en la misma tabla que los datos. **No demuestra que el orden tenga sentido:** con embeddings de hash, Zafiro Software (la otra acción de tecnología) queda al final. Un modelo de embeddings real la pondría primero.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cómo hacer real la similitud</strong></summary>
# MAGIC
# MAGIC Cambia `hash_to_embedding()` por una llamada a un modelo de embeddings, por ejemplo un endpoint de
# MAGIC Foundation Model de Databricks, y guarda su resultado. La tabla, la columna, la consulta y el índice
# MAGIC siguen igual; solo cambian los números, y el orden empieza a tener sentido.
# MAGIC
# MAGIC pgvector conviene para búsquedas operativas sobre filas vivas, como esta. Para colecciones grandes de
# MAGIC documentos que se sincronizan por lotes (buscar en miles de PDF, por ejemplo), Databricks Vector Search
# MAGIC suele ser la mejor herramienta.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Indexa los vectores
# MAGIC
# MAGIC Con cinco filas, la búsqueda lee todas de todos modos. Con millones, un índice HNSW encuentra los
# MAGIC vecinos más cercanos sin recorrer todo. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_instrument_embedding_hnsw
# MAGIC   ON bank.instrument USING hnsw (embedding vector_l2_ops);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_instrument_embedding_hnsw "
            f"ON bank.instrument USING hnsw (embedding vector_l2_ops)"
        )
        print(f"Índice HNSW creado en bank.instrument.embedding")
        print(f"\nOptimización del índice: HNSW (Hierarchical Navigable Small World)")
        print(f"  Búsqueda rápida y aproximada de los vecinos más cercanos")
        print(f"  Tiempo de consulta O(log n) para millones de vectores")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** ```
# MAGIC Índice HNSW creado en bank.instrument.embedding
# MAGIC
# MAGIC Optimización del índice: HNSW (Hierarchical Navigable Small World)
# MAGIC   Búsqueda rápida y aproximada de los vecinos más cercanos
# MAGIC   Tiempo de consulta O(log n) para millones de vectores
# MAGIC ```
# MAGIC
# MAGIC `vector_l2_ops` corresponde a la distancia `<->` de C1; un índice solo ayuda a las consultas que usan su operador.
# MAGIC
# MAGIC **Qué demuestra:** las columnas de vectores se indexan como cualquier otra columna, dentro de la misma base de datos.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Dónde se guarda el embedding de cada instrumento?</strong></summary>
# MAGIC
# MAGIC En la columna `embedding` de `bank.instrument`, en la misma fila que el instrumento.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué Zafiro Software quedó al final, si es la otra acción de tecnología?</strong></summary>
# MAGIC
# MAGIC Los embeddings son un hash del texto, no lo que entiende un modelo, así que las distancias son arbitrarias. Un modelo de embeddings real lo corregiría sin cambiar la consulta.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Qué devuelve `<->`?</strong></summary>
# MAGIC
# MAGIC La distancia entre dos vectores. Menor significa más parecido.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusión
# MAGIC
# MAGIC En este laboratorio agregaste vectores a una tabla, guardaste uno por fila, ordenaste filas por
# MAGIC similitud e indexaste los vectores. Puntos clave:
# MAGIC
# MAGIC 1. **pgvector convierte a Postgres en un almacén de vectores:** un tipo de columna, operadores de
# MAGIC    distancia e índices.
# MAGIC 2. **Los embeddings viven junto a los datos operativos,** así que una búsqueda por similitud también
# MAGIC    puede filtrar por estado, dueño o cualquier otra cosa en la misma consulta.
# MAGIC 3. **HNSW la mantiene rápida** cuando las tablas crecen.
# MAGIC 4. **El orden es tan bueno como los embeddings:** aquí un hash, en producción un modelo real.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente**, según tu ruta:
# MAGIC
# MAGIC - Desarrolladores de aplicaciones: <a href="$../pg-search/pg_search_databricks_es">Búsqueda de texto completo y aproximada →</a>
# MAGIC - Desarrolladores de agentes: <a href="$../pg-features/pg_features_databricks_es">Servir features en línea →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
