# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 3 de 6 · Búsqueda de texto completo y aproximada</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Búsqueda de texto completo y aproximada
# MAGIC #### Duración: 30 minutos
# MAGIC
# MAGIC *Recorrido 3 de 6 de la ruta de Desarrolladores de aplicaciones. Los vectores ordenaron filas por similitud; este recorrido busca texto por palabras y por cómo se escribe.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Una analista de fraude y PLD necesita buscar en años de notas de caso. "Me acuerdo de una nota sobre
# MAGIC una transferencia SPEI y una toma de cuenta" debería encontrarla, ordenada por relevancia, y un error
# MAGIC al escribir un id de cuenta no debería frenar la búsqueda.
# MAGIC
# MAGIC Postgres trae las dos cosas: **búsqueda de texto completo**, que encuentra palabras sin importar su
# MAGIC forma y ordena los resultados, y **coincidencia por trigramas** (`pg_trgm`), que encuentra textos que se
# MAGIC escriben parecido. En este laboratorio usas las dos en las notas de caso del banco y agregas el índice
# MAGIC que mantiene rápida la búsqueda de texto completo.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Buscar texto por palabras** con búsqueda de texto completo y ordenar los resultados.
# MAGIC 2. **Encontrar coincidencias aproximadas** de un id mal escrito con similitud por trigramas.
# MAGIC 3. **Indexar texto para buscarlo** con un índice GIN sobre `to_tsvector`.
# MAGIC 4. **Explicar la búsqueda híbrida:** combinar coincidencias de palabras con similitud de vectores.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Búsqueda de texto completo:** Postgres convierte el texto en una lista de palabras normalizadas (un `tsvector`) y la compara con una consulta (un `tsquery`). "transfers" y "transfer" coinciden, y `ts_rank` mide la relevancia.
# MAGIC - **Similitud por trigramas:** la extensión `pg_trgm` parte los textos en pedazos de tres caracteres y mide cuántos comparten dos textos (de 0 a 1). Sirve para errores de escritura en nombres e ids.
# MAGIC - **Índice GIN sobre texto:** indexa cada palabra del `tsvector`, para que la búsqueda de texto completo no lea todas las filas.
# MAGIC - **Búsqueda híbrida:** combinar la relevancia de texto completo con un puntaje de similitud de vectores. Este recorrido la explica; no la ejecuta.
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
# MAGIC     Necesitas: la extensión <code>pg_trgm</code>, que este notebook crea.
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
# MAGIC ### A2. Carga el módulo de ayuda
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

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print("conectado; esquema:", SCHEMA)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `conectado; esquema: bank`
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
# MAGIC ## B. Busca por palabras

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Revisa las notas de caso
# MAGIC
# MAGIC Notas de texto libre que escribieron los analistas sobre alertas. Las notas están en inglés. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3;
# MAGIC ```

# COMMAND ----------

sql = "SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3"
rows = run_sql(sql)
print("Notas de caso de ejemplo:")
for row in rows:
    writeup = (row[2][:60] + "...") if row[2] and len(row[2]) > 60 else row[2]
    print(f"  note_id={row[0]}, account_id={row[1]}")
    print(f"    '{writeup}'")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Notas de caso de ejemplo:
# MAGIC   note_id=1, account_id=CTA-100240
# MAGIC     'Cardholder reports three card-not-present charges to a forei...'
# MAGIC   note_id=2, account_id=CTA-300421
# MAGIC     'Large outbound SPEI transfer to a new beneficiary, just unde...'
# MAGIC   note_id=3, account_id=CTA-200311
# MAGIC     'Customer disputed a recurring subscription charge. Confirmed...'
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Búsqueda de texto completo, ordenada
# MAGIC
# MAGIC Encuentra las notas que mencionan "SPEI" o "takeover" (toma de cuenta), las más relevantes primero. Como
# MAGIC las notas están en inglés, la búsqueda usa la configuración `'english'`. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id,
# MAGIC        ts_rank(to_tsvector('english', writeup), to_tsquery('english', 'spei | takeover')) AS rank
# MAGIC   FROM bank.case_note
# MAGIC  WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'spei | takeover')
# MAGIC  ORDER BY rank DESC;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT note_id, account_id,
       ts_rank(to_tsvector('english', writeup),
               to_tsquery('english', 'spei | takeover')) as rank
  FROM bank.case_note
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'spei | takeover')
 ORDER BY rank DESC
 LIMIT 5
"""
rows = run_sql(sql)
print("Notas de caso que coinciden con 'SPEI OR takeover', ordenadas por relevancia:")
for row in rows:
    print(f"  note_id={row[0]}, account_id={row[1]}, rank={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Notas de caso que coinciden con 'SPEI OR takeover', ordenadas por relevancia:
# MAGIC   note_id=1, account_id=CTA-100240, rank=0.06079271
# MAGIC   note_id=2, account_id=CTA-300421, rank=0.030396355
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la búsqueda encuentra palabras, no textos exactos, y ordena por relevancia: la nota 1 menciona las dos palabras, así que queda arriba de la nota 2, que solo menciona "SPEI".

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Busca por cómo se escribe

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Coincidencia aproximada de un id de cuenta
# MAGIC
# MAGIC `pg_trgm` mide qué tan parecidos son dos textos por sus pedazos de tres caracteres. La celda lo activa y
# MAGIC busca las cuentas más parecidas a la primera que lee, `CTA-100234`. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS pg_trgm;
# MAGIC SELECT account_id, similarity(account_id, 'CTA-100234') AS sim
# MAGIC   FROM bank.account
# MAGIC  WHERE account_id % 'CTA-100234'      -- suficientemente parecido (umbral de pg_trgm, 0.3 por defecto)
# MAGIC  ORDER BY sim DESC LIMIT 5;
# MAGIC ```

# COMMAND ----------

# Activa pg_trgm
with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        except:
            pass

# Busca cuentas parecidas a un id de cuenta de ejemplo
sample_accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
if not sample_accounts:
    print("No se encontraron cuentas")
else:
    sample_id = sample_accounts[0][0]

    sql = """
    SELECT account_id,
           similarity(account_id, %s) as sim
      FROM bank.account
     WHERE account_id %% %s
     ORDER BY sim DESC
     LIMIT 5
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sample_id, sample_id))
            rows = cur.fetchall()

    print(f"Cuentas parecidas a '{sample_id}' (coincidencia aproximada, tolera errores de escritura):")
    for row in rows:
        print(f"  {row[0]} (similarity={row[1]:.3f})")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Cuentas parecidas a 'CTA-100234' (coincidencia aproximada, tolera errores de escritura):
# MAGIC   CTA-100234 (similarity=1.000)
# MAGIC   CTA-100235 (similarity=0.692)
# MAGIC   CTA-100240 (similarity=0.571)
# MAGIC   CTA-100241 (similarity=0.571)
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** se encuentran y ordenan las coincidencias cercanas, así que un id mal escrito como `CTA-100243` seguiría mostrando los candidatos correctos.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Indexa el texto
# MAGIC
# MAGIC Un índice GIN sobre el `tsvector` hace que la búsqueda de texto completo use el índice en lugar de leer
# MAGIC cada nota. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_case_note_fts ON bank.case_note USING gin (to_tsvector('english', writeup));
# MAGIC ```

# COMMAND ----------

sql = """
CREATE INDEX IF NOT EXISTS idx_case_note_fts
  ON bank.case_note
  USING gin(to_tsvector('english', writeup))
"""
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

print("Índice GIN creado en bank.case_note(writeup)")
print("(Las siguientes búsquedas de texto completo usarán el índice)")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Índice GIN creado en bank.case_note(writeup)
# MAGIC (Las siguientes búsquedas de texto completo usarán el índice)
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la búsqueda de texto se indexa dentro de la base de datos; no hace falta un motor de búsqueda aparte.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Búsqueda híbrida (explicada)

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Qué agrega la búsqueda híbrida
# MAGIC
# MAGIC La búsqueda de texto completo encuentra las palabras que escribiste; la búsqueda vectorial encuentra
# MAGIC notas que significan algo parecido. La búsqueda híbrida combina los dos puntajes. Esta celda solo la
# MAGIC explica: necesitaría un embedding en cada nota de caso (ver *Búsqueda por similitud de vectores*).

# COMMAND ----------

print("La búsqueda híbrida (palabras clave + semántica) necesita pgvector para los embeddings.")
print("Ya dominas la búsqueda de texto completo (FTS) y la coincidencia aproximada (pg_trgm).")
print("Esos dos enfoques cubren la mayoría de los casos de búsqueda en producción.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC La búsqueda híbrida (palabras clave + semántica) necesita pgvector para los embeddings.
# MAGIC Ya dominas la búsqueda de texto completo (FTS) y la coincidencia aproximada (pg_trgm).
# MAGIC Esos dos enfoques cubren la mayoría de los casos de búsqueda en producción.
# MAGIC ```

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cómo se vería una consulta híbrida</strong></summary>
# MAGIC
# MAGIC Dale a cada nota de caso una columna `embedding`, como en *Búsqueda por similitud de vectores*, y
# MAGIC ordena por una combinación con pesos de la relevancia de texto y la similitud del vector, por ejemplo
# MAGIC `0.6 * ts_rank(...) + 0.4 * (1 - (embedding <=> :query_embedding))`. Ajusta los pesos con preguntas
# MAGIC reales de tus analistas.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Por qué la nota 1 quedó arriba de la nota 2?</strong></summary>
# MAGIC
# MAGIC Coincide con las dos palabras de la búsqueda, "SPEI" y "takeover"; la nota 2 solo con "SPEI".
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Cuándo usarías similitud por trigramas en lugar de búsqueda de texto completo?</strong></summary>
# MAGIC
# MAGIC Para textos cortos donde importan los errores de escritura, como nombres e ids. La búsqueda de texto completo es para palabras en textos más largos.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Qué necesita la búsqueda híbrida que este recorrido no creó?</strong></summary>
# MAGIC
# MAGIC Un embedding en cada nota de caso, para combinar un puntaje de similitud de vectores con la relevancia del texto.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio buscaste notas de caso por palabras, encontraste coincidencias aproximadas por
# MAGIC cómo se escriben e indexaste el texto. Puntos clave:
# MAGIC
# MAGIC 1. **La búsqueda de texto completo** encuentra palabras sin importar su forma y ordena por relevancia.
# MAGIC 2. **La similitud por trigramas** atrapa errores de escritura en textos cortos como ids y nombres.
# MAGIC 3. **Los índices GIN** mantienen rápidas las dos, dentro de la misma base de datos.
# MAGIC 4. **La búsqueda híbrida** combina la relevancia de texto con la similitud de vectores cuando agregas
# MAGIC    embeddings.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de aplicaciones:** <a href="$../pg-booking/pg_booking_databricks_es">Evitar horarios que se traslapan →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
