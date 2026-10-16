# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Configuración · Crea tu proyecto y tu rama</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Configuración: crea tu proyecto y tu rama
# MAGIC
# MAGIC Ejecuta este notebook una vez, de arriba abajo, antes de cualquier recorrido. Hace la parte del
# MAGIC participante de `00-setup/` dentro del workspace, sin laptop ni CLI:
# MAGIC
# MAGIC 1. Instala el driver de Postgres.
# MAGIC 2. Toma el nombre de tu proyecto y de tu rama de los widgets de la parte superior del notebook.
# MAGIC 3. Crea tu propio proyecto de Lakebase, `bank-<tu nombre de correo>`, que viene con una rama `production`.
# MAGIC 4. Carga los datos del banco en `production`.
# MAGIC 5. Configura la Data API en `production`, para el recorrido API de datos de Lakebase.
# MAGIC 6. Crea tu rama, `u-<tu nombre de correo>`, como una rama copy-on-write de `production`. Todos los recorridos se ejecutan en ella.
# MAGIC 7. Ejecuta `SELECT 1` y una consulta real para comprobar que todo funciona.
# MAGIC
# MAGIC Cada paso revisa primero y se salta lo que ya está hecho, así que puedes volver a ejecutar el notebook sin problema.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Antes de empezar</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. Necesitas permiso para crear proyectos de
# MAGIC     Lakebase en este workspace. Para el recorrido de la Data API, tu instructor también crea antes de la
# MAGIC     sesión un service principal del taller y guarda su client id y su secreto en el secret scope
# MAGIC     <code>lakebase-workshop</code>. Sin ese scope, el paso 5 se omite y todos los demás recorridos
# MAGIC     funcionan igual.
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
# MAGIC Esta celda agrega tres widgets en la parte superior del notebook. Los nombres salen de la parte de tu
# MAGIC correo antes de la `@`: con `alex.kim@example.com`, el proyecto es `bank-alex-kim` y la rama `u-alex-kim`.
# MAGIC Cambia un widget solo si tu instructor te dio otros nombres, y vuelve a ejecutar desde aquí.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "common", "scripts"))
from lakebase import client, connect, run_sql, notebook_env

env = notebook_env(dbutils, lang="es")   # por defecto: project=bank-<nombre de correo>, schema=bank
w = client()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Crea tu proyecto
# MAGIC Un proyecto de Lakebase es una base de datos Postgres con sus propias ramas y su propio cómputo. El tuyo
# MAGIC usa Postgres 17, y su cómputo se suspende solo después de 5 minutos sin consultas, como verás en Escalar
# MAGIC a cero. Queda listo en unos segundos. Si ya existe, esta celda solo confirma que está funcionando.

# COMMAND ----------

import project
project.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Carga el banco en `production`
# MAGIC Esquema y datos de ejemplo. `production` guarda esta copia limpia, y tu rama parte de ella. Si el banco
# MAGIC ya está ahí, se omite la carga y solo se muestran las filas por tabla, así que volver a ejecutar el
# MAGIC notebook no duplica transacciones.

# COMMAND ----------

import load_bank
with connect(branch="production") as conn:
    loaded = load_bank.is_loaded(conn)
os.environ["LB_BRANCH"] = "production"   # load_bank trabaja sobre LB_BRANCH
try:
    if loaded:
        print("El banco ya está cargado en production, así que se omitió la carga.")
        load_bank.main(["--check"])
    else:
        load_bank.main([])
finally:
    os.environ["LB_BRANCH"] = env["LB_BRANCH"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Configura la Data API
# MAGIC La Data API sirve tus tablas por HTTPS. Rechaza las solicitudes del dueño del proyecto (tú), así que el
# MAGIC recorrido API de datos de Lakebase la llama como el service principal del taller. Esta celda habilita la
# MAGIC Data API en `production` y le da al service principal acceso de solo lectura al esquema `bank`. Tu rama
# MAGIC hereda las dos cosas cuando se crea en el siguiente paso.

# COMMAND ----------

try:
    sp_app_id = dbutils.secrets.get("lakebase-workshop", "sp-client-id")
except Exception:
    sp_app_id = None
    print("No existe el secret scope lakebase-workshop, así que se omitió la configuración de la Data API. "
          "Todos los recorridos, excepto API de datos de Lakebase, funcionan sin ella.")
if sp_app_id:
    project.enable_data_api(branch="production")
    project.grant_data_api(sp_app_id)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Crea tu rama
# MAGIC Una rama copy-on-write de `production`: no se copian datos, la API responde en menos de un segundo y el
# MAGIC endpoint al que te conectas queda `ACTIVE` en unos dos segundos. Empieza con el banco que acabas de
# MAGIC cargar. Si la rama ya existe, esta celda solo confirma que está funcionando.

# COMMAND ----------

import branch
branch.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Comprueba que funciona

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
# MAGIC widgets toman por defecto el proyecto y la rama que acabas de crear.
