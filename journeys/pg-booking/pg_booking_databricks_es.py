# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 4 de 6 · Evitar horarios que se traslapan</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Evitar horarios que se traslapan
# MAGIC #### Duración: 20 minutos
# MAGIC
# MAGIC *Recorrido 4 de 6 de la ruta de Desarrolladores de aplicaciones. La búsqueda leyó datos; en este recorrido la base de datos rechaza datos que rompen una regla.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Cada tramo de liquidación reserva una ventana de tiempo en una cuenta, y dos ventanas de la misma cuenta
# MAGIC nunca deben traslaparse. Con muchas solicitudes compitiendo por reservar, revisar en el código de la
# MAGIC aplicación ("¿está libre el horario?" y luego "resérvalo") deja un hueco en el que dos solicitudes ven
# MAGIC el horario libre al mismo tiempo.
# MAGIC
# MAGIC Postgres puede hacer cumplir la regla por sí mismo con una **restricción de exclusión**: la base de
# MAGIC datos rechaza, de forma atómica, cualquier fila cuyo rango de tiempo se traslape con el de otra fila de
# MAGIC la misma cuenta. En este laboratorio agregas la restricción e intentas romperla.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Describir una regla de no traslape** como una restricción de exclusión sobre una cuenta y un rango de tiempo.
# MAGIC 2. **Agregar la restricción** con un índice GiST y la extensión `btree_gist`.
# MAGIC 3. **Ver cómo la base de datos rechaza** una liquidación que se traslapa.
# MAGIC 4. **Explicar por qué la base de datos es el lugar correcto** para esta regla cuando las solicitudes compiten.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Rango de tiempo (`tstzrange`):** un valor de Postgres con una hora de inicio y una de fin. `&&` es verdadero cuando dos rangos se traslapan.
# MAGIC - **Restricción de exclusión:** una regla que impide que dos filas coincidan en todas las condiciones indicadas, aquí la misma cuenta (`=`) y rangos de tiempo que se traslapan (`&&`). Postgres la revisa al escribir una fila.
# MAGIC - **GiST y `btree_gist`:** GiST es el tipo de índice detrás de los operadores de rangos; `btree_gist` le permite comparar también valores simples como `account_id`, para que los dos quepan en una restricción.
# MAGIC - **Condición de carrera:** dos solicitudes que revisan y luego escriben pueden pasar la revisión las dos. Una restricción cierra ese hueco, porque la base de datos revisa y escribe en un solo paso.
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
# MAGIC     Necesitas: la extensión <code>btree_gist</code>, que este notebook crea. Ejecútalo en una rama recién cargada: agrega una restricción de exclusión a <code>bank.settlement</code>.
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
# MAGIC ## B. El calendario actual

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Revisa las liquidaciones
# MAGIC
# MAGIC Tres tramos de liquidación, cada uno reservado en una cuenta por una ventana de tiempo. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT settlement_id, account_id, starts_at, ends_at FROM bank.settlement LIMIT 3;
# MAGIC ```

# COMMAND ----------

sql = "SELECT settlement_id, account_id, starts_at, ends_at FROM bank.settlement LIMIT 3"
rows = run_sql(sql)
print("Liquidaciones de ejemplo:")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** tres filas, `STL-1` en `CTA-100240`, `STL-2` en `CTA-100241` y `STL-3` en `CTA-200310`, cada una
# MAGIC con su hora de inicio y de fin. Las horas son relativas al momento en que cargaste el banco, así que
# MAGIC verás la fecha de hoy.
# MAGIC
# MAGIC **Qué demuestra:** hoy lo único que mantiene separadas las ventanas es que nadie ha reservado un choque todavía.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Deja que la base de datos haga cumplir la regla

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Agrega la restricción de exclusión
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS btree_gist;
# MAGIC ALTER TABLE bank.settlement ADD CONSTRAINT no_account_overlap
# MAGIC   EXCLUDE USING gist (account_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
            print("extensión btree_gist creada")
        except:
            pass

        # Postgres no tiene ADD CONSTRAINT IF NOT EXISTS; se borra y se vuelve a agregar para poder repetirlo.
        cur.execute("ALTER TABLE bank.settlement DROP CONSTRAINT IF EXISTS no_account_overlap")
        sql = """
        ALTER TABLE bank.settlement
          ADD CONSTRAINT no_account_overlap
          EXCLUDE USING gist (account_id WITH =,
                              tstzrange(starts_at, ends_at) WITH &&)
        """
        try:
            cur.execute(sql)
            print("Restricción de exclusión creada: no_account_overlap")
        except Exception as e:
            print(f"No se pudo crear la restricción: {e}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** ```
# MAGIC extensión btree_gist creada
# MAGIC Restricción de exclusión creada: no_account_overlap
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la regla ahora vive en la base de datos. Las filas existentes ya la cumplen; si no, agregarla habría fallado.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>No se pudo crear la restricción: ... already exists</code>: ya ejecutaste esta celda antes en esta rama. No pasa nada; sigue con C2.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Intenta reservar una liquidación que se traslapa
# MAGIC
# MAGIC La celda toma una liquidación existente e inserta otra en la misma cuenta, traslapando su ventana.

# COMMAND ----------

import datetime

# Toma una liquidación existente (y su operación, por la llave foránea) para traslaparla.
stls = run_sql("""
SELECT settlement_id, trade_id, account_id, starts_at, ends_at
  FROM bank.settlement
 WHERE account_id IS NOT NULL AND starts_at IS NOT NULL AND ends_at IS NOT NULL
 LIMIT 1
""")

if not stls:
    print("No se encontraron liquidaciones")
else:
    settlement_id, trade_id, account_id, starts_at, ends_at = stls[0]

    # Intenta insertar una liquidación que se traslapa
    with connect() as conn:
        with conn.cursor() as cur:
            # Borra cualquier fila de prueba anterior para poder repetirlo
            cur.execute("DELETE FROM bank.settlement WHERE settlement_id = 'STL-OVERLAP'")
            try:
                # Crea una liquidación que se traslapa con la existente
                overlap_start = starts_at
                overlap_end = ends_at + datetime.timedelta(hours=1)

                cur.execute("""
                INSERT INTO bank.settlement
                  (settlement_id, trade_id, account_id, seq, status, starts_at, ends_at)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s)
                """, ('STL-OVERLAP', trade_id, account_id, 99, 'pending', overlap_start, overlap_end))
                print("ERROR: ¡el traslape debió rechazarse!")
            except Exception as e:
                error_msg = str(e)
                if "no_account_overlap" in error_msg or "conflicting key" in error_msg or "exclusion" in error_msg.lower():
                    print("Bien: la base de datos rechazó la liquidación que se traslapa.")
                    print(f"  {error_msg.splitlines()[0][:120]}")
                else:
                    print(f"Error inesperado: {error_msg[:120]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Bien: la base de datos rechazó la liquidación que se traslapa.
# MAGIC   conflicting key value violates exclusion constraint "no_account_overlap"
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el traslape no se puede escribir, sin importar qué aplicación, usuario o carrera lo intente. Ningún código de la aplicación revisó nada.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C3. Revisa el plan de un insert
# MAGIC
# MAGIC `EXPLAIN` muestra cómo Postgres produciría la fila nueva. La restricción no aparece en el plan: Postgres
# MAGIC revisa una restricción de exclusión al escribir la fila, con el índice GiST de la restricción, y por eso
# MAGIC C2 falló al momento de insertar.

# COMMAND ----------

sql = ("EXPLAIN INSERT INTO bank.settlement "
       "(settlement_id, trade_id, account_id, seq, status, starts_at, ends_at) "
       "SELECT 'stl-explain', trade_id, 'CTA-100240', 98, 'pending', now(), now() + interval '1 hour' "
       "FROM bank.settlement LIMIT 1")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        print("Plan de la consulta (la restricción se revisa al escribir la fila, por eso no aparece aquí):")
        for row in rows:
            print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC Plan de la consulta (la restricción se revisa al escribir la fila, por eso no aparece aquí):
# MAGIC   Insert on settlement  (cost=0.00..0.36 rows=0 width=0)
# MAGIC     ->  Subquery Scan on "*SELECT*"  (cost=0.00..0.36 rows=1 width=148)
# MAGIC           ->  Limit  (cost=0.00..0.35 rows=1 width=148)
# MAGIC                 ->  Seq Scan on settlement settlement_1  (cost=0.00..1.05 rows=3 width=148)
# MAGIC ```

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>¿Por qué no revisarlo en la aplicación?</strong></summary>
# MAGIC
# MAGIC Una revisión en la aplicación son dos pasos: leer ("¿está libre la ventana?") y escribir ("resérvala").
# MAGIC Dos solicitudes pueden leer antes de que alguna escriba, y las dos reservan. Los bloqueos en la
# MAGIC aplicación pueden resolverlo, pero cada servicio que escribe liquidaciones tiene que hacerlo bien. Una
# MAGIC restricción es una sola regla, en un solo lugar, que se revisa de forma atómica para todos.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Qué dos condiciones combina `no_account_overlap`?</strong></summary>
# MAGIC
# MAGIC La misma `account_id` (`=`) y rangos de tiempo que se traslapan (`&&`).
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué la restricción no aparece en la salida de `EXPLAIN`?</strong></summary>
# MAGIC
# MAGIC Postgres revisa las restricciones de exclusión al escribir la fila, no como parte del plan de la consulta.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué una restricción es más segura que una revisión en la aplicación?</strong></summary>
# MAGIC
# MAGIC La base de datos revisa y escribe en un solo paso atómico, así que dos solicitudes que compiten no pueden pasar las dos.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusión
# MAGIC
# MAGIC En este laboratorio agregaste una restricción de exclusión y viste cómo la base de datos rechazó una
# MAGIC liquidación que se traslapaba. Puntos clave:
# MAGIC
# MAGIC 1. **Las restricciones de exclusión expresan "no puede haber dos filas que choquen"** con cualquier
# MAGIC    combinación de condiciones.
# MAGIC 2. **GiST y `btree_gist`** permiten que una restricción combine la misma cuenta con un traslape de tiempo.
# MAGIC 3. **La base de datos hace cumplir la regla de forma atómica,** para cualquiera que escriba, sin hueco
# MAGIC    para una carrera.
# MAGIC 4. **La revisión ocurre al escribir,** no en el plan de la consulta.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de aplicaciones:** <a href="$../data-api/data_api_databricks_es">API de datos de Lakebase →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
