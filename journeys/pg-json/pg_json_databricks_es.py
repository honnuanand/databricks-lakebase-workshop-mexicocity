# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 1 de 6 · Datos JSON con JSONB</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Datos JSON con JSONB
# MAGIC #### Duración: 20 minutos
# MAGIC
# MAGIC *Recorrido 1 de 6 de la ruta de Desarrolladores de aplicaciones. La Parte 1 usó columnas fijas; este recorrido guarda datos cuya forma cambia de una fila a otra.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC El equipo de productos del banco tiene una ficha técnica de cada instrumento: una acción tiene ticker,
# MAGIC sector y beta; un bono tiene plazo, cupón y calificación; el efectivo solo tiene moneda. Un tipo de
# MAGIC producto nuevo normalmente implicaría cambiar el esquema, y un `ALTER TABLE` en una tabla muy usada
# MAGIC nunca es agradable.
# MAGIC
# MAGIC Postgres guarda esas fichas como **JSONB**, JSON estructurado dentro de una columna normal, y permite
# MAGIC consultarlas e indexarlas con SQL. En este laboratorio revisas las fichas, buscas dentro de ellas,
# MAGIC extraes campos como si fueran columnas y agregas un índice que mantiene rápidas esas búsquedas cuando
# MAGIC la tabla crece.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Guardar documentos con campos variables** en una columna JSONB, junto a columnas normales.
# MAGIC 2. **Encontrar filas por lo que contiene su documento** con el operador de contención `@>`.
# MAGIC 3. **Extraer un campo como valor** con `#>>` y comprobar si existe una llave con `?`.
# MAGIC 4. **Indexar una columna JSONB** con GIN para que las búsquedas de contención sigan siendo rápidas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **JSONB:** el tipo JSON binario de Postgres. Guarda un documento JSON en una columna y permite consultarlo por dentro con SQL; las llaves pueden cambiar de una fila a otra.
# MAGIC - **Contención (`@>`):** "¿el documento de la izquierda contiene esta parte?" `spec @> '{"sector": "tech"}'` encuentra cada ficha con esa llave y ese valor, tenga lo que tenga además.
# MAGIC - **Extracción por ruta (`#>>`) y existencia de llave (`?`):** `spec #>> '{sector}'` devuelve el sector como texto; `spec ? 'sector'` es verdadero cuando la llave existe.
# MAGIC - **Índice GIN:** un Generalized Inverted Index: indexa las llaves y los valores de cada documento, para que las búsquedas de contención no lean todas las filas.
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
# MAGIC     Necesitas: nada además de la configuración (JSONB y GIN vienen con Postgres).
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
# MAGIC ## B. Mira dentro de los documentos

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Revisa las fichas
# MAGIC
# MAGIC Cada instrumento tiene una columna `spec` de tipo JSONB, y sus campos cambian según el tipo. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3;
# MAGIC ```

# COMMAND ----------

sql = "SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3"
rows = run_sql(sql)
print("Fichas técnicas de ejemplo (JSONB, campos variables):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** tres instrumentos y sus fichas, por ejemplo:
# MAGIC
# MAGIC ```
# MAGIC Fichas técnicas de ejemplo (JSONB, campos variables):
# MAGIC   INS-CASH-MXN: Mexican Peso Cash
# MAGIC     spec: {'ccy': 'MXN'}
# MAGIC   INS-SLEEVE-EQ: Equity Sleeve
# MAGIC     spec: {'theme': 'large-cap'}
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     spec: {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC ```
# MAGIC
# MAGIC Sin un `ORDER BY`, las tres filas que veas pueden ser otras.
# MAGIC
# MAGIC **Qué demuestra:** una sola columna guarda documentos de formas distintas. Nadie tuvo que agregar una columna `beta` o `ccy`.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Busca por lo que contiene un documento
# MAGIC
# MAGIC `@>` pregunta si el documento de la izquierda contiene la parte de la derecha. Busca los instrumentos
# MAGIC del sector tecnológico. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}' LIMIT 5;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
 LIMIT 5
"""
rows = run_sql(sql)
print("Instrumentos con sector='tech' (con el operador de contención @>):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** las dos acciones del sector tech:
# MAGIC
# MAGIC ```
# MAGIC Instrumentos con sector='tech' (con el operador de contención @>):
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     spec: {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC   INS-ZAFR: Zafiro Software
# MAGIC     spec: {'beta': 0.9, 'sector': 'tech', 'ticker': 'ZAFR'}
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** puedes filtrar por un campo dentro del documento, y las filas que no tienen ese campo simplemente no coinciden.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Extrae un campo como si fuera una columna
# MAGIC
# MAGIC `#>>` extrae como texto el valor de una ruta; `?` deja solo las filas que tienen la llave. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec #>> '{sector}' AS sector FROM bank.instrument
# MAGIC  WHERE spec ? 'sector' LIMIT 5;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec #>> '{sector}' as sector
  FROM bank.instrument
 WHERE spec ? 'sector'
 LIMIT 5
"""
rows = run_sql(sql)
print("Campo sector extraído de la ficha JSONB:")
for row in rows:
    print(f"  {row[0]}: sector={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Campo sector extraído de la ficha JSONB:
# MAGIC   INS-QTZL: sector=tech
# MAGIC   INS-ZAFR: sector=tech
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** un campo JSON se puede usar como una columna normal en un resultado. Solo las dos acciones tienen la llave `sector`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Hazlo rápido

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Agrega un índice GIN
# MAGIC
# MAGIC Con cinco filas, las búsquedas son rápidas de todos modos. Con millones, un índice GIN en la columna
# MAGIC JSONB permite que `@>` use el índice en lugar de leer cada fila. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops);
# MAGIC ```

# COMMAND ----------

sql = "CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops)"
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
print("Índice GIN creado en bank.instrument(spec)")
print("(Las consultas usarán el índice cuando convenga)")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** ```
# MAGIC Índice GIN creado en bank.instrument(spec)
# MAGIC (Las consultas usarán el índice cuando convenga)
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** las columnas JSONB se indexan como cualquier otra columna. En una tabla tan chica, el planificador puede seguir leyendo toda la tabla; el índice se nota cuando la tabla crece.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     En la app <strong>Lakebase Postgres</strong>, abre la pestaña <strong>Tables</strong> de tu rama y selecciona <code>instrument</code> para ver sus columnas, incluida <code>spec</code>, y sus índices.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Una consulta de selección
# MAGIC
# MAGIC Combina una condición sobre JSONB con una columna normal: acciones del sector tech. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}' AND kind = 'equity' LIMIT 10;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
    AND kind = 'equity'
 LIMIT 10
"""
rows = run_sql(sql)
print("Acciones del sector tech:")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    if row[2]:
        print(f"    {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Acciones del sector tech:
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC   INS-ZAFR: Zafiro Software
# MAGIC     {'beta': 0.9, 'sector': 'tech', 'ticker': 'ZAFR'}
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** JSONB y las columnas normales se combinan en un mismo `WHERE`, así que las fichas flexibles no te quitan el SQL de siempre.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cuándo usar JSONB y cuándo no</strong></summary>
# MAGIC
# MAGIC Usa JSONB para atributos que cambian según el tipo o con frecuencia: fichas de productos, mandatos,
# MAGIC configuraciones. Deja como columnas normales los campos que usas para unir, sumar o restringir (ids,
# MAGIC montos, fechas): ocupan menos, tienen tipo y son más fáciles de validar.
# MAGIC
# MAGIC `jsonb_path_ops`, el que se usa aquí, hace un índice más chico y rápido para `@>`, pero no sirve para el
# MAGIC operador `?`; el `jsonb_ops` por defecto sirve para los dos.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Qué filas encuentra `spec @> '{"sector": "tech"}'`?</strong></summary>
# MAGIC
# MAGIC Todas las filas cuya ficha tiene la llave `sector` con el valor `tech`, tengan las demás llaves que tengan.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué el Bono M no apareció en B3?</strong></summary>
# MAGIC
# MAGIC Su ficha no tiene la llave `sector`, así que `spec ? 'sector'` es falso para él.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Cuándo ayuda el índice GIN?</strong></summary>
# MAGIC
# MAGIC En tablas grandes, para búsquedas de contención: el planificador puede usarlo en lugar de leer cada fila.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusión
# MAGIC
# MAGIC En este laboratorio guardaste documentos de formas distintas en una sola columna, buscaste dentro de
# MAGIC ellos, extrajiste campos y los indexaste. Puntos clave:
# MAGIC
# MAGIC 1. **JSONB guarda campos variables** en una sola columna, sin cambiar el esquema por cada tipo de producto.
# MAGIC 2. **`@>` encuentra filas por lo que contiene su documento;** `#>>` y `?` leen y revisan campos sueltos.
# MAGIC 3. **Los índices GIN** mantienen rápidas las búsquedas de contención cuando las tablas crecen.
# MAGIC 4. **JSONB y las columnas normales trabajan juntos** en el mismo SQL.
# MAGIC
# MAGIC El siguiente recorrido guarda otro tipo de valor en la fila: un vector, para buscar por similitud.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de aplicaciones:** <a href="$../pg-vector/pg_vector_databricks_es">Búsqueda por similitud de vectores →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
