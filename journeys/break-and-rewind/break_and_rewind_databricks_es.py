# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 1 · Recorrido 2 de 5 · Restauración a un punto en el tiempo</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Restauración a un punto en el tiempo
# MAGIC #### Duración: unos 15 minutos
# MAGIC
# MAGIC *Recorrido 2 de 5. En Ramas de base de datos bifurcaste tu rama tal como está ahora. Aquí la bifurcas tal como estaba hace un momento.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Eres el DBA de la plataforma de operaciones del banco. Al final del día, alguien ejecuta una consulta
# MAGIC de limpieza con el `WHERE` equivocado, y desaparece todo el libro de operaciones: no quedan operaciones
# MAGIC abiertas ni liquidaciones pendientes. En la mayoría de las bases de datos, eso significa restaurar el
# MAGIC respaldo de anoche y perder horas.
# MAGIC
# MAGIC En Lakebase, el historial de la base de datos se guarda en el almacenamiento, así que puedes crear en
# MAGIC segundos una rama de la base de datos como estaba un momento antes del error. En este laboratorio
# MAGIC cometes ese error en tu propia rama, a propósito, y recuperas los datos.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Capturar una posición del registro (LSN)** que marca el estado de la base de datos antes de un cambio.
# MAGIC 2. **Recuperar datos borrados** creando una rama en ese LSN anterior.
# MAGIC 3. **Leer las filas recuperadas** desde la rama de recuperación y confirmar que están completas.
# MAGIC 4. **Explicar qué tan atrás puedes restaurar:** la ventana de historial del proyecto, 7 días por defecto.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Write-ahead log (WAL, registro de escritura anticipada):** Postgres registra cada cambio en un log antes de aplicarlo. Lakebase guarda ese historial en su almacenamiento.
# MAGIC - **LSN (número de secuencia del registro):** una posición en el write-ahead log, como una marca de tiempo del estado de la base de datos. `pg_current_wal_lsn()` devuelve la actual.
# MAGIC - **Restauración a un punto en el tiempo:** crear una rama de la base de datos como estaba en un LSN o en un momento anterior.
# MAGIC - **Ventana de historial:** qué tan atrás puedes restaurar. Se define por proyecto; 7 días por defecto.
# MAGIC - **Rama de recuperación:** la rama que creas en ese punto anterior. Está separada de tu rama, así que puedes revisar los datos anteriores antes de decidir qué hacer con ellos.
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
# MAGIC ### A2. Conéctate a tu rama
# MAGIC
# MAGIC Esta celda carga el módulo compartido de `common/scripts/` y define `connect_branch()`, que abre una
# MAGIC conexión de Postgres a cualquier rama por su nombre. La vas a usar en tu rama y en la rama de
# MAGIC recuperación.
# MAGIC
# MAGIC Por dentro, `connect_branch()` le pide a la API de Lakebase el nombre de host de la rama, obtiene un
# MAGIC token de inicio de sesión con tu identidad de Databricks (válido por cerca de una hora) y abre una
# MAGIC conexión estándar de Postgres con `psycopg`, un driver de Postgres para Python.
# MAGIC
# MAGIC En los pasos siguientes, el bloque de SQL de cada paso es la sentencia que se ejecuta en la rama. La
# MAGIC celda de Python de abajo solo envía esa sentencia e imprime el resultado.

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint, wait_active, _env, PG_PORT, DEFAULT_DB
from databricks.sdk.service.postgres import Branch, BranchSpec
from databricks.sdk.common.types.fieldmask import FieldMask
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
RESTORE = MINE + "-restore"
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
w = client()

def connect_branch(branch):
    host, eid, state = branch_endpoint(w, PROJECT, branch)
    if not host:
        raise RuntimeError(f"la rama {branch} no está lista ({state})")
    cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, branch)}/endpoints/{eid}")
    conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True, connect_timeout=20)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    return conn

print("conectado como", w.current_user.me().user_name)
print(f"proyecto={PROJECT}, tu rama={MINE}, la rama de recuperación será {RESTORE}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC conectado como alex.kim@example.com
# MAGIC proyecto=bank, tu rama=u-alex-kim, la rama de recuperación será u-alex-kim-restore
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>KeyError: 'LB_PROJECT'</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## B. Antes del error
# MAGIC
# MAGIC Cada cambio en la base de datos se escribe en el write-ahead log, y cada posición de ese log tiene un
# MAGIC número, el **LSN** (número de secuencia del registro). En esta sección revisas los datos y anotas el
# MAGIC LSN actual. Después vas a crear una rama en ese LSN para recuperar los datos.
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 230" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="210" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <text x="30" y="95" font-size="14" font-weight="700" fill="#0b2026">u-tunombre</text>
# MAGIC   <line x1="140" y1="90" x2="680" y2="90" stroke="#1B5162" stroke-width="3"/>
# MAGIC   <polygon points="680,84 692,90 680,96" fill="#1B5162"/>
# MAGIC   <text x="686" y="114" text-anchor="end" font-size="12" fill="#5A6F77">tiempo</text>
# MAGIC   <text x="260" y="48" text-anchor="middle" font-size="12" font-weight="700" fill="#0b2026">B2. LSN capturado</text>
# MAGIC   <text x="260" y="66" text-anchor="middle" font-size="12" fill="#5A6F77">2 operaciones</text>
# MAGIC   <circle cx="260" cy="90" r="8" fill="#1B5162"/>
# MAGIC   <text x="470" y="48" text-anchor="middle" font-size="12" font-weight="700" fill="#0b2026">C. DELETE</text>
# MAGIC   <text x="470" y="66" text-anchor="middle" font-size="12" fill="#5A6F77">0 operaciones</text>
# MAGIC   <circle cx="470" cy="90" r="8" fill="#FF3621"/>
# MAGIC   <path d="M 260 98 L 260 180 L 300 180" fill="none" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <polygon points="300,174 310,180 300,186" fill="#FF3621"/>
# MAGIC   <rect x="312" y="155" width="290" height="50" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="457" y="177" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-tunombre-restore</text>
# MAGIC   <text x="457" y="195" text-anchor="middle" font-size="12" fill="#5A6F77">D. creada en el LSN capturado: 2 operaciones</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Revisa las operaciones
# MAGIC
# MAGIC Confirma que las operaciones existen en tu rama. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT trade_id, fund_id, qty, status FROM bank.trade ORDER BY trade_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT trade_id, fund_id, qty, status FROM trade ORDER BY trade_id")
        rows = cur.fetchall()
print(f"Operaciones en tu rama ({len(rows)} en total):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Operaciones en tu rama (2 en total):
# MAGIC   ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
# MAGIC   ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** tu rama tiene dos operaciones. Recuérdalas: las vas a borrar y después a recuperar.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Operaciones en tu rama (0 en total)</code>: ya ejecutaste este recorrido y las operaciones siguen borradas. Ejecuta la celda de reinicio de la sección E y empieza otra vez desde B1.</li>
# MAGIC       <li><code>NotFound: branch id not found</code>: tu rama todavía no existe. Ejecuta <code>00-setup/setup_databricks_es</code> o revisa el widget <code>LB_BRANCH</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Captura el LSN
# MAGIC
# MAGIC Anota la posición del log ahora, antes del error. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT pg_current_wal_lsn();
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_current_wal_lsn()")
        lsn = cur.fetchone()[0]
print(f"LSN capturado: {lsn}")
print(f"Este LSN marca el momento antes del borrado. Lo vamos a usar para recuperar los datos.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `LSN capturado: 0/1BE6B80` en una ejecución de prueba, y luego la línea que lo
# MAGIC explica. Tu LSN tendrá otro valor con el mismo formato.
# MAGIC
# MAGIC **Qué demuestra:** ya tienes una marca de "la base de datos antes del error". D1 la necesita, así que no vuelvas a ejecutar esta celda después de la sección C.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## C. Comete el error
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">Advertencia: esto borra datos de tu rama</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     La siguiente celda borra a propósito todas las operaciones y liquidaciones de <strong>tu</strong> rama.
# MAGIC     Nunca toca <code>production</code>, que guarda la copia limpia del banco. Las filas siguen borradas en tu rama
# MAGIC     hasta que ejecutes la celda de reinicio de la sección E.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC La limpieza demasiado amplia. Las filas de `settlement` hacen referencia a `trade` con una llave
# MAGIC foránea, así que primero se borran las liquidaciones:
# MAGIC
# MAGIC ```sql
# MAGIC DELETE FROM bank.settlement;
# MAGIC DELETE FROM bank.trade;
# MAGIC ```

# COMMAND ----------

# La limpieza equivocada: las filas de settlement hacen referencia a trade (llave foránea),
# así que primero se borran las liquidaciones y después las operaciones.
with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM settlement")    # primero las hijas (llave foránea a trade)
        cur.execute("DELETE FROM trade")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM trade")
        tr = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM settlement")
        stl = cur.fetchone()[0]
print(f"Borrado completo. Operaciones restantes: {tr}, liquidaciones restantes: {stl}")
if tr == 0 and stl == 0:
    print("Se borraron de tu rama todas las operaciones y sus liquidaciones.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Borrado completo. Operaciones restantes: 0, liquidaciones restantes: 0
# MAGIC Se borraron de tu rama todas las operaciones y sus liquidaciones.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el error es real. A tu rama no le quedan operaciones ni liquidaciones.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Recupera con una restauración a un punto en el tiempo
# MAGIC
# MAGIC ### D1. Crea una rama en el LSN capturado
# MAGIC
# MAGIC Crea una rama de recuperación a partir de tu rama, pero como estaba en el LSN que capturaste en B2. Es
# MAGIC una operación del control plane, así que usa el SDK. La celda primero borra cualquier rama de
# MAGIC recuperación que haya quedado de una ejecución anterior. La llamada clave:
# MAGIC
# MAGIC ```python
# MAGIC w.postgres.create_branch(
# MAGIC     parent=f"projects/{PROJECT}",
# MAGIC     branch=Branch(spec=BranchSpec(
# MAGIC         source_branch=branch_name(PROJECT, MINE),
# MAGIC         source_branch_lsn=lsn,
# MAGIC         no_expiry=True)),
# MAGIC     branch_id=RESTORE)
# MAGIC ```

# COMMAND ----------

# Borra cualquier rama de recuperación que haya quedado de una ejecución anterior
try:
    w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
        branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
    w.postgres.delete_branch(name=branch_name(PROJECT, RESTORE))
    time.sleep(2)
except Exception:
    pass

# Crea la rama de recuperación en el LSN capturado
t0 = time.time()
w.postgres.create_branch(
    parent=f"projects/{PROJECT}",
    branch=Branch(spec=BranchSpec(
        source_branch=branch_name(PROJECT, MINE),
        source_branch_lsn=lsn,
        no_expiry=True)),
    branch_id=RESTORE, replace_existing=False)
api_ms = (time.time() - t0) * 1000
waited = wait_active(w, PROJECT, RESTORE)
print(f"rama PITR {RESTORE} creada")
print(f"  la API create_branch respondió en {api_ms:.0f} ms")
print(f"  el endpoint llegó a ACTIVE en ~{waited:.1f}s")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado** (de una ejecución de prueba; tus números van a variar un poco):
# MAGIC
# MAGIC ```
# MAGIC rama PITR u-tunombre-restore creada
# MAGIC   la API create_branch respondió en 436 ms
# MAGIC   el endpoint llegó a ACTIVE en ~1.9s
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** volver en el tiempo es solo crear una rama en un LSN anterior, así que tarda más o
# MAGIC menos lo mismo que crear cualquier otra rama.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     En la app <strong>Lakebase Postgres</strong>, abre tu proyecto. La pestaña <strong>Branches</strong> muestra
# MAGIC     <code>u-tunombre-restore</code>, y en la pestaña <strong>Backup &amp; Restore</strong> puedes hacer la misma
# MAGIC     restauración sin código, eligiendo un momento en lugar de un LSN.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Error de permisos:</strong> crear una rama requiere <code>CAN_MANAGE</code> en el proyecto. Como el proyecto es tuyo, ya lo tienes: revisa que el widget <code>LB_PROJECT</code> tenga tu proyecto, <code>bank-tunombre</code>.</li>
# MAGIC       <li><code>TimeoutError: la rama ... no llegó a ACTIVE en 30s</code>: la primera rama de una sesión puede tardar más. Vuelve a ejecutar la celda.</li>
# MAGIC       <li><code>NameError: name 'lsn' is not defined</code>: el notebook se reinició después de B2, así que se perdió el LSN de antes del borrado. No vuelvas a ejecutar B2: capturaría un punto <em>posterior</em> al borrado. Mejor restaura por fecha y hora desde la pestaña <strong>Backup &amp; Restore</strong>, o ejecuta la celda de reinicio de la sección E y empieza otra vez desde B1.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### D2. Lee las operaciones recuperadas
# MAGIC
# MAGIC La rama de recuperación tiene la base de datos como estaba antes del DELETE, así que ahí están las
# MAGIC operaciones. La misma consulta que en B1, en la rama de recuperación:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT trade_id, fund_id, qty, status FROM bank.trade ORDER BY trade_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(RESTORE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT trade_id, fund_id, qty, status FROM trade ORDER BY trade_id")
        rows = cur.fetchall()
print(f"Operaciones recuperadas de la rama PITR ({len(rows)} en total):")
for row in rows:
    print(f"  {row}")
print("\nLos datos borrados están intactos. Cada byte está como antes del error.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Operaciones recuperadas de la rama PITR (2 en total):
# MAGIC   ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
# MAGIC   ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
# MAGIC
# MAGIC Los datos borrados están intactos. Cada byte está como antes del error.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** son las mismas dos operaciones de B1, leídas desde una rama creada después de
# MAGIC borrarlas. La rama de recuperación tiene toda tu base de datos como estaba en el LSN de B2.

# COMMAND ----------

# MAGIC %md
# MAGIC ### D3. Cómo regresar los datos a tu rama
# MAGIC
# MAGIC Este recorrido llega hasta leer las filas recuperadas. En la práctica, elegirías una de dos formas de
# MAGIC recuperarlas:
# MAGIC
# MAGIC - **Copiar las filas de vuelta.** Léelas desde la rama de recuperación e insértalas en tu rama, por
# MAGIC   ejemplo con un script que abra una conexión a cada rama, como hace D2. Úsalo cuando solo se perdió
# MAGIC   una parte de los datos y el resto de tu rama ya avanzó desde el error.
# MAGIC - **Cambiarte a la rama de recuperación.** Apunta tu aplicación a la rama de recuperación y úsala como
# MAGIC   la nueva rama de trabajo. Úsalo cuando todo lo que se escribió después del error se puede descartar.
# MAGIC
# MAGIC En los dos casos, revisa primero los datos recuperados. Para eso está separada la rama de recuperación.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>En qué se diferencia de una restauración tradicional de Postgres y qué tan atrás puedes ir</strong></summary>
# MAGIC
# MAGIC En un Postgres tradicional, la recuperación a un punto en el tiempo significa restaurar un respaldo
# MAGIC base en un servidor nuevo y volver a aplicar el write-ahead log hasta el momento que quieres. Eso tarda
# MAGIC de minutos a horas, según el tamaño de la base de datos y la antigüedad del respaldo.
# MAGIC
# MAGIC Lakebase guarda el historial en su capa de almacenamiento, así que restaurar es crear una rama
# MAGIC copy-on-write en un LSN anterior: no hay respaldo que copiar ni log que volver a aplicar. Tarda los
# MAGIC mismos dos segundos que cualquier rama.
# MAGIC
# MAGIC Qué tan atrás puedes ir lo define la **ventana de historial** del proyecto (en **Settings** del
# MAGIC proyecto, en la app Lakebase Postgres). Tu proyecto del taller usa el valor por defecto, 7 días.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Limpieza
# MAGIC
# MAGIC ### E1. Borra la rama de recuperación
# MAGIC
# MAGIC Ya revisaste los datos recuperados, así que borra la rama de recuperación. Borrarla no afecta a tu
# MAGIC rama.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
w.postgres.delete_branch(name=branch_name(PROJECT, RESTORE))
print(f"Descartada {RESTORE}")
print("\nRecuperación completa. La rama PITR ya no existe y no dejó almacenamiento. En tu rama, las operaciones siguen borradas.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Descartada u-tunombre-restore
# MAGIC
# MAGIC Recuperación completa. La rama PITR ya no existe y no dejó almacenamiento. En tu rama, las operaciones siguen borradas.
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### E2. Reconstruye tu rama
# MAGIC
# MAGIC **Tu rama sigue sin operaciones.** Leíste las filas recuperadas desde la rama de recuperación, pero no
# MAGIC las copiaste de vuelta. La siguiente celda reconstruye tu rama para que los siguientes recorridos
# MAGIC empiecen con el banco completo: borra tu rama y la vuelve a crear a partir de `production`, que ya
# MAGIC tiene el banco completo. Solo toca tu rama.

# COMMAND ----------

import branch
branch.reset()

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `rama u-tunombre eliminada`, la rama nueva llegando a `ACTIVE`, y luego
# MAGIC `Tablas del banco en la rama u-tunombre:` con las filas por tabla, entre ellas `trade 2 filas` y
# MAGIC `settlement 3 filas`: la rama nueva ya trae el banco completo de `production`. Tarda unos 10 segundos.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Por qué capturaste el LSN antes del DELETE y no después?</strong></summary>
# MAGIC
# MAGIC La rama de recuperación se crea en ese LSN. Un LSN posterior al DELETE te daría una copia sin las operaciones.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Al terminar este recorrido, ¿tu propia rama tiene las operaciones?</strong></summary>
# MAGIC
# MAGIC No hasta E2. Solo leíste las operaciones desde la rama de recuperación; el reinicio de E2 reconstruye tu rama con un banco nuevo.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Podrías restaurar a un momento de hace dos semanas?</strong></summary>
# MAGIC
# MAGIC No con la configuración por defecto: la ventana de historial es de 7 días. Es una configuración del proyecto.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusión
# MAGIC
# MAGIC En este laboratorio borraste datos en uso, creaste una rama en un LSN anterior al borrado y leíste de
# MAGIC nuevo cada fila. Puntos clave:
# MAGIC
# MAGIC 1. **Restaurar a un punto en el tiempo es crear una rama en un LSN anterior,** con el mismo mecanismo
# MAGIC    copy-on-write del recorrido anterior.
# MAGIC 2. **Tarda segundos,** sin respaldo que restaurar ni log que volver a aplicar.
# MAGIC 3. **La rama de recuperación está separada de tu rama,** así que puedes revisar los datos anteriores
# MAGIC    antes de decidir qué copiar de vuelta.
# MAGIC 4. **Qué tan atrás puedes ir** lo define la ventana de historial del proyecto, 7 días por defecto, en
# MAGIC    la configuración del proyecto.
# MAGIC
# MAGIC El siguiente recorrido ve los mismos datos desde el lado analítico: una sola copia de los datos, usada
# MAGIC tanto para la operación como para la analítica.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la Parte 1:** <a href="$../write-to-analytics/write_to_analytics_databricks_es">Datos de Lakebase en el Lakehouse →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
