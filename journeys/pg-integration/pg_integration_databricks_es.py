# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 1 · Recorrido 5 de 5 · Conectar herramientas de Postgres</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Conectar herramientas de Postgres
# MAGIC #### Duración: unos 10 minutos
# MAGIC
# MAGIC *Recorrido 5 de 5. Hasta ahora usaste Lakebase desde este notebook. Este recorrido muestra lo que ve cualquier herramienta de Postgres cuando se conecta.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC La plataforma central del banco, el motor de fraude y las aplicaciones de riesgo y reportes ya usan
# MAGIC SQLAlchemy, JDBC, dbt, Metabase y Tableau. Si una base de datos nueva necesita sus propios drivers o
# MAGIC adaptadores, hay que rehacer cada una de esas integraciones. La pregunta del equipo es sencilla:
# MAGIC ¿las herramientas que ya usamos van a funcionar tal cual?
# MAGIC
# MAGIC Lakebase es Postgres, así que sí. Cuando una herramienta de BI o un ORM se conecta, lo primero que hace
# MAGIC es leer el catálogo estándar de Postgres, `information_schema`, para conocer las tablas y las columnas.
# MAGIC En este laboratorio ejecutas tú mismo esas consultas.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Descubrir las tablas y columnas** de una base de datos de Lakebase con `information_schema`.
# MAGIC 2. **Armar el mapa del esquema** que arma una herramienta de BI o un ORM al conectarse.
# MAGIC 3. **Leer filas de ejemplo** para confirmar que los datos coinciden con el esquema.
# MAGIC 4. **Saber qué necesita una herramienta de Postgres para conectarse:** host, puerto, base de datos, usuario y un token de inicio de sesión.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Esquema de Postgres:** una carpeta con nombre que agrupa tablas dentro de una base de datos. Las tablas del taller están en el esquema `bank`, así que sus nombres completos son `bank.account`, `bank.txn`, etcétera. (No hay que confundirlo con "el esquema" en el sentido de la estructura de las tablas.)
# MAGIC - **`information_schema`:** un conjunto de vistas de solo lectura, definidas por el estándar SQL, que tiene toda base de datos Postgres. Describen la propia base de datos: sus esquemas, tablas, columnas y tipos. Consultarlas es la forma en que una herramienta sabe qué hay en una base de datos sin que nadie se lo diga.
# MAGIC - **Wire protocol (protocolo de comunicación):** el "idioma" de red que usa un cliente para hablar con una base de datos. Lakebase habla el protocolo estándar de Postgres, así que cualquier driver de Postgres puede conectarse.
# MAGIC - **ORM y herramienta de BI:** un ORM (object-relational mapper, como SQLAlchemy) permite que el código de una aplicación trabaje con las tablas como objetos; una herramienta de BI (como Tableau o Power BI) arma reportes y tableros. Las dos descubren las tablas y columnas a partir del catálogo de la base de datos, como lo vas a hacer aquí.
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
# MAGIC     Si acabas de hacer Restauración a un punto en el tiempo, asegúrate de haber ejecutado su celda de reinicio.
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>.
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
# MAGIC Esta celda carga `run_sql()` de `common/scripts/`. Abre una conexión a tu rama, ejecuta una sentencia
# MAGIC SQL y devuelve las filas, si hay.
# MAGIC
# MAGIC Por dentro, `run_sql()` le pide a la API de Lakebase el nombre de host de tu rama, obtiene un token de
# MAGIC inicio de sesión con tu identidad de Databricks (válido por cerca de una hora) y abre una conexión
# MAGIC estándar de Postgres con `psycopg`, un driver de Postgres para Python.
# MAGIC
# MAGIC En los pasos siguientes, el bloque de SQL de cada paso es la sentencia que se ejecuta en tu rama. La
# MAGIC celda de Python de abajo solo envía esa sentencia e imprime el resultado.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql, _env
from collections import defaultdict

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print(f"Esquema: {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Esquema: bank`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Descubre el esquema como lo hace una herramienta
# MAGIC
# MAGIC ### B1. Lista las tablas
# MAGIC
# MAGIC Una consulta estándar al catálogo de Postgres. Cualquier herramienta que se conecta ejecuta algo parecido:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name FROM information_schema.tables
# MAGIC WHERE table_schema = 'bank' ORDER BY table_name;
# MAGIC ```

# COMMAND ----------

query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{SCHEMA}' ORDER BY table_name"
rows = run_sql(query)
tables = [row[0] for row in rows]
print(f"{len(tables)} tablas encontradas:")
for table in tables:
    print(f"  - {table}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `14 tablas encontradas:` y luego una línea por tabla: `account`, `agent_memory`,
# MAGIC `branch`, `case_note`, `counterparty`, `custodian`, `fund`, `holding`, `instrument`, `position`,
# MAGIC `settlement`, `trade`, `trade_counterparty`, `txn`.
# MAGIC
# MAGIC **Qué demuestra:** con una sola consulta estándar, tú, o cualquier herramienta, pueden listar todas las tablas del esquema `bank`. No interviene ninguna API específica de Lakebase.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>0 tablas encontradas</code>: el banco no está cargado en esta rama, o <code>LB_SCHEMA</code> no es <code>bank</code>. Revisa el widget o ejecuta <code>00-setup/setup_databricks_es</code>.</li>
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego A2 y esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Lista las columnas y sus tipos
# MAGIC
# MAGIC La celda imprime el total y luego las primeras columnas de las tres primeras tablas:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema = 'bank'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

# Agrupa por tabla
by_table = defaultdict(list)
for table, column, dtype in rows:
    by_table[table].append((column, dtype))

print(f"{len(rows)} columnas en {len(by_table)} tablas")
for table in sorted(by_table.keys())[:3]:
    print(f"\n{table}:")
    for col, dtype in by_table[table][:5]:
        print(f"  {col}: {dtype}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `77 columnas en 14 tablas` si hiciste *Datos de Lakebase en el Lakehouse*, que
# MAGIC agrega la columna `fraud_risk` (76 en una rama recién cargada). Luego las primeras columnas de
# MAGIC `account`, `agent_memory` y `branch`:
# MAGIC
# MAGIC ```
# MAGIC account:
# MAGIC   account_id: text
# MAGIC   branch_id: text
# MAGIC   line: text
# MAGIC   type: text
# MAGIC   status: text
# MAGIC
# MAGIC agent_memory:
# MAGIC   id: bigint
# MAGIC   ...
# MAGIC
# MAGIC branch:
# MAGIC   branch_id: text
# MAGIC   ...
# MAGIC   lat: double precision
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** los nombres y tipos de las columnas salen de las mismas vistas estándar. Así sabe una herramienta que `health_pct` es un número y `status` es texto antes de leer una sola fila.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Arma un mapa del esquema
# MAGIC
# MAGIC Agrega si cada columna acepta nulos y tienes el mapa que arma una herramienta de BI o un ORM antes de
# MAGIC mostrarte cualquier dato:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type, is_nullable
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema = 'bank'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type, is_nullable "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

schema_map = defaultdict(list)
for table, column, dtype, nullable in rows:
    schema_map[table].append({
        "column": column,
        "type": dtype,
        "nullable": nullable == "YES"
    })

print(f"\n=== Mapa del esquema del banco ===")
total_cols = 0
for table in sorted(schema_map.keys())[:3]:
    print(f"\nTABLA: {table}")
    for col_info in schema_map[table][:4]:
        col = col_info["column"]
        dtype = col_info["type"]
        null_marker = "" if col_info["nullable"] else " NOT NULL"
        print(f"  {col}: {dtype}{null_marker}")
        total_cols += 1

print(f"\n=== Estadísticas ===")
print(f"Total de tablas: {len(schema_map)}")
print(f"Total de columnas: {len(rows)}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `=== Mapa del esquema del banco ===`, las primeras cuatro columnas de cada una
# MAGIC de las tres primeras tablas, con `NOT NULL` donde aplica (por ejemplo, `account_id: text NOT NULL`), y
# MAGIC luego:
# MAGIC
# MAGIC ```
# MAGIC === Estadísticas ===
# MAGIC Total de tablas: 14
# MAGIC Total de columnas: 77
# MAGIC ```
# MAGIC
# MAGIC Igual que en B2, el total es 76 en una rama recién cargada.
# MAGIC
# MAGIC **Qué demuestra:** al agregar `is_nullable`, una herramienta tiene lo que necesita para armar formularios, reportes o modelos de ORM, todo a partir de `information_schema`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Revisa los datos
# MAGIC
# MAGIC Lee algunas filas de dos tablas para confirmar que los datos coinciden con el esquema. La celda imprime
# MAGIC las primeras tres columnas de cada fila:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account LIMIT 3;
# MAGIC SELECT * FROM bank.trade LIMIT 3;
# MAGIC ```

# COMMAND ----------

# Muestra de la tabla account
rows = run_sql(f"SELECT * FROM {SCHEMA}.account LIMIT 3")
print(f"Filas de ejemplo de la tabla account:")
for row in rows:
    print(f"  {row[:3]}...")  # Muestra las primeras 3 columnas

# Muestra de la tabla trade
rows = run_sql(f"SELECT * FROM {SCHEMA}.trade LIMIT 3")
print(f"\nFilas de ejemplo de la tabla trade:")
for row in rows:
    print(f"  {row[:3]}...")  # Muestra las primeras 3 columnas

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Filas de ejemplo de la tabla account:
# MAGIC   ('CTA-100234', 'BR-CDMX', 'Checking')...
# MAGIC   ('CTA-100235', 'BR-CDMX', 'Savings')...
# MAGIC   ('CTA-100240', 'BR-CDMX', 'Credit')...
# MAGIC
# MAGIC Filas de ejemplo de la tabla trade:
# MAGIC   ('TRD-8821', 'BR-CDMX', 'FUND-GROWTH-A')...
# MAGIC   ('TRD-8822', 'BR-MTY', 'FUND-INCOME-B')...
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** los datos coinciden con la estructura que descubrió la herramienta.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>No hay filas de trade:</strong> <em>Restauración a un punto en el tiempo</em> las borró de tu rama. Ejecuta <code>import branch; branch.reset()</code> en una celda nueva para reconstruir tu rama y vuelve a ejecutar esta celda.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## D. Conecta tus propias herramientas
# MAGIC
# MAGIC Cualquier cliente de Postgres se conecta con los mismos cinco datos que usa este notebook: el **host**
# MAGIC de la rama, el puerto **5432**, la base de datos **databricks_postgres**, tu **usuario de Databricks** y
# MAGIC un **token de inicio de sesión** como contraseña. Las conexiones deben usar SSL (`sslmode=require`).
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     En la app <strong>Lakebase Postgres</strong>, abre tu proyecto y tu rama, y elige <strong>Connect</strong>
# MAGIC     en <strong>Computes</strong>. Ahí aparecen el host y cadenas de conexión listas para <code>psql</code> y otros
# MAGIC     clientes. La pestaña <strong>Tables</strong> muestra las mismas tablas que acabas de listar.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Tokens de inicio de sesión y herramientas que se quedan conectadas</strong></summary>
# MAGIC
# MAGIC La contraseña es un token de corta duración que sale de tu identidad de Databricks, no una contraseña
# MAGIC guardada. Vence después de cerca de una hora. Eso no es problema para un notebook o un script que pide
# MAGIC un token nuevo cada vez que se conecta, como lo hace el módulo de ayuda del taller.
# MAGIC
# MAGIC Una herramienta que mantiene una conexión abierta por días, como un servidor de BI o una aplicación,
# MAGIC tiene que obtener un token nuevo antes de que venza el anterior. Las aplicaciones normalmente lo hacen
# MAGIC en su pool de conexiones. El recorrido *Crear una app de Databricks sobre Lakebase* muestra cómo
# MAGIC se conecta una aplicación con su propio service principal.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Qué es `information_schema`?</strong></summary>
# MAGIC
# MAGIC Un conjunto de vistas estándar de solo lectura que describen los propios esquemas, tablas, columnas y tipos de la base de datos.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué las herramientas de BI no necesitan un driver especial para Lakebase?</strong></summary>
# MAGIC
# MAGIC Lakebase habla el wire protocol estándar de Postgres, así que cualquier driver de Postgres se conecta.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Qué usa una herramienta como contraseña?</strong></summary>
# MAGIC
# MAGIC Un token de inicio de sesión de corta duración, de tu identidad de Databricks, válido por cerca de una hora.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio descubriste el esquema del banco como lo hace una herramienta de BI o un ORM, y
# MAGIC revisaste los datos. Puntos clave:
# MAGIC
# MAGIC 1. **Lakebase es Postgres:** las consultas estándar al catálogo, los drivers y las herramientas funcionan
# MAGIC    sin adaptadores.
# MAGIC 2. **Las herramientas descubren el esquema solas** con `information_schema`.
# MAGIC 3. **Para conectarse bastan cinco datos:** host, puerto 5432, base de datos, tu usuario y un token de
# MAGIC    inicio de sesión, sobre SSL.
# MAGIC 4. **Los tokens de inicio de sesión duran poco,** así que las herramientas que se quedan conectadas los
# MAGIC    renuevan en su pool de conexiones.
# MAGIC
# MAGIC Aquí termina la Parte 1. La Parte 2 sigue con el mismo banco: elige la ruta que va con tu trabajo.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Terminaste la Parte 1.** Para la Parte 2, elige una ruta:
# MAGIC
# MAGIC - Desarrolladores de aplicaciones: <a href="$../pg-json/pg_json_databricks_es">Datos JSON con JSONB →</a>
# MAGIC - Desarrolladores de agentes: <a href="$../agent-memory/agent_memory_databricks_es">Memoria compartida entre agentes →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
