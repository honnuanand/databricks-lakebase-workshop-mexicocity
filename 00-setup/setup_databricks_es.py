# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Configuración · Crea tu rama</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Configuración: crea tu rama
# MAGIC
# MAGIC Ejecuta este notebook una vez, de arriba abajo, antes de cualquier recorrido. Hace la parte del
# MAGIC participante de `00-setup/` dentro del workspace, sin laptop ni CLI:
# MAGIC
# MAGIC 1. Instala el driver de Postgres.
# MAGIC 2. Toma el nombre de tu proyecto y de tu rama de los widgets de la parte superior del notebook.
# MAGIC 3. Crea tu rama, `u-<tu nombre de correo>`, como una rama copy-on-write de `production`.
# MAGIC 4. Carga en ella los datos del banco. Si ya están cargados, se omite este paso, así que puedes volver a ejecutar el notebook sin problema.
# MAGIC 5. Ejecuta `SELECT 1` y una consulta real para comprobar que todo funciona.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Antes de empezar</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. Tu instructor hace el resto una vez, antes
# MAGIC     de la sesión: crea el proyecto de Lakebase (por defecto, <code>bank</code>) y le da a tu grupo el permiso
# MAGIC     <code>CAN_MANAGE</code> para que puedas crear una rama (ver <code>provision.md</code> y
# MAGIC     <code>grants.md</code>). Si lo haces por tu cuenta, crea primero el proyecto en la interfaz:
# MAGIC     <strong>Compute → Lakebase Postgres → Create</strong>, con el nombre <code>bank</code> y Postgres 17.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Instala el driver de Postgres
# MAGIC `psycopg` es el driver de Postgres que usa el taller para ejecutar SQL. El SDK de Databricks solo
# MAGIC se actualiza si la versión de tu entorno es anterior a la API de Lakebase (0.120.0); si es más nueva,
# MAGIC se deja como está. La segunda celda reinicia Python para que la instalación surta efecto.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Tu proyecto y tu rama
# MAGIC Esta celda agrega tres widgets en la parte superior del notebook. `LB_BRANCH` toma por defecto `u-` más
# MAGIC la parte de tu correo antes de la `@`; por ejemplo, `alex.kim@example.com` queda como `u-alex-kim`.
# MAGIC Cambia un widget solo si tu instructor te dio otro nombre de proyecto o de rama, y vuelve a ejecutar
# MAGIC desde aquí.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "common", "scripts"))
from lakebase import client, connect, run_sql, notebook_env

env = notebook_env(dbutils, lang="es")   # por defecto: project=bank, schema=bank
w = client()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Comprueba que el proyecto existe

# COMMAND ----------

try:
    w.postgres.get_project(name=f"projects/{env['LB_PROJECT']}")
except Exception as e:
    raise SystemExit(
        f"No se encuentra el proyecto de Lakebase '{env['LB_PROJECT']}' ({str(e)[:120]}). Pídele a tu instructor "
        f"el nombre del proyecto y escríbelo en el widget LB_PROJECT, o crea primero el proyecto.") from e
print(f"proyecto {env['LB_PROJECT']} encontrado")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Crea tu rama
# MAGIC Una rama copy-on-write de `production`: no se copian datos, la API responde en menos de un segundo y el
# MAGIC endpoint al que te conectas queda `ACTIVE` en unos dos segundos. Si la rama ya existe, esta celda solo
# MAGIC confirma que está funcionando.

# COMMAND ----------

import branch
branch.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Carga el banco en tu rama
# MAGIC Esquema y datos de ejemplo. Si tu rama ya tiene el banco, se omite la carga y solo se muestran las
# MAGIC filas por tabla, así que volver a ejecutar el notebook no duplica transacciones.

# COMMAND ----------

import load_bank
with connect() as conn:
    loaded = load_bank.is_loaded(conn)
if loaded:
    print("El banco ya está cargado en tu rama, así que se omitió la carga.")
    load_bank.main(["--check"])
else:
    load_bank.main([])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Comprueba que funciona

# COMMAND ----------

print("SELECT 1 ->", run_sql("SELECT 1")[0][0])
print("cuentas por sucursal:")
for row in run_sql("SELECT branch_id, count(*) FROM bank.account GROUP BY branch_id ORDER BY branch_id"):
    print("  ", row)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC Todo listo. **Siguiente en la Parte 1:** <a href="$../journeys/branch-the-brain/branch_the_brain_databricks_es">Ramas de base de datos →</a>
# MAGIC
# MAGIC O abre el <a href="$../START_HERE_es">índice</a> para ver la Parte 1 y las dos rutas de la Parte 2.
# MAGIC Todos los notebooks de los recorridos empiezan con las mismas celdas de instalación y widgets, y los
# MAGIC widgets toman por defecto la rama que acabas de crear.
