# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 1 · Recorrido 1 de 5 · Ramas de base de datos</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Ramas de base de datos
# MAGIC #### Duración: unos 15 minutos
# MAGIC
# MAGIC *Recorrido 1 de 5. Todo en la Parte 1 se ejecuta en tu propia rama de la base de datos del banco, la que creaste en la configuración.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC En producción, la cuenta `CTA-100240`, una cuenta de crédito de banca minorista, está en `watch` y
# MAGIC todavía puede hacer cargos. Una transacción de la madrugada obtuvo un puntaje de fraude alto, y una
# MAGIC analista de fraude quiere congelar la cuenta para ver cómo reaccionan los procesos que dependen de
# MAGIC ella. Congelar la cuenta de un cliente real para hacer un experimento es justo el tipo de cambio que
# MAGIC despierta a alguien a las 2 de la mañana.
# MAGIC
# MAGIC En lugar de eso, bifurcas toda la base de datos en una rama, congelas ahí la cuenta y descartas la rama
# MAGIC cuando terminas. El cliente nunca lo nota. Cada paso usa la interfaz real: SQL cuando el paso es una
# MAGIC consulta y el SDK de Databricks cuando es una acción del control plane, como crear una rama.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Bifurcar una base de datos de Lakebase en uso** en una rama nueva y medir cuánto tarda en estar lista.
# MAGIC 2. **Cambiar datos en el fork** y demostrar que la rama de origen no cambió.
# MAGIC 3. **Borrar el fork** y confirmar que no queda nada.
# MAGIC 4. **Explicar por qué crear una rama es rápido y casi gratis:** el almacenamiento usa copy-on-write, así que no se copian datos.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Rama:** una copia completa e independiente de una base de datos dentro de un proyecto de Lakebase, como una rama de git pero para datos. `production` es la original de tu proyecto; `u-tunombre` es tu rama de trabajo.
# MAGIC - **Copy-on-write (copia en escritura):** una rama nueva comparte los datos almacenados de su rama de origen y solo escribe las páginas que cambias. Por eso una rama se crea sin copiar datos.
# MAGIC - **Endpoint (cómputo):** el servidor de Postgres en ejecución al que te conectas. La rama guarda los datos; su endpoint ejecuta tus consultas. Cada rama tiene su propio endpoint.
# MAGIC - **Control plane (plano de control) vs. SQL:** crear, listar y borrar ramas son acciones de administración que se hacen con la API de Lakebase (aquí, con el SDK de Databricks). Leer y cambiar datos se hace con SQL.
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
# MAGIC Ejecuta las siguientes tres celdas antes que nada. Instalan el driver de Postgres, actualizan el
# MAGIC SDK de Databricks si la versión de tu entorno es anterior a la API de Lakebase, y toman `LB_PROJECT`,
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
# MAGIC conexión de Postgres a cualquier rama por su nombre. La vas a usar para leer tanto tu rama como el
# MAGIC fork.
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
from lakebase import client, branch_name, branch_endpoint, wait_active
from databricks.sdk.service.postgres import Branch, BranchSpec
from databricks.sdk.common.types.fieldmask import FieldMask
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
EXP     = MINE + "-exp"
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
ACCOUNT = "CTA-100240"
w = client()

def connect_branch(branch):
    host, eid, state = branch_endpoint(w, PROJECT, branch)
    if not host:
        raise RuntimeError(f"la rama {branch} no está lista ({state})")
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(PROJECT, branch)}/endpoints/{eid}")
    conn = psycopg.connect(host=host, port=5432, dbname="databricks_postgres",
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    return conn

print("conectado como", w.current_user.me().user_name)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `conectado como` y tu correo.
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
# MAGIC ## B. Bifurca tu rama
# MAGIC
# MAGIC Tu rama, `u-tunombre`, se bifurcó de la rama `production` de tu proyecto durante la configuración. En esta
# MAGIC sección bifurcas **tu** rama en una rama de experimento de corta duración, `u-tunombre-exp`.
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 230" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="210" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <text x="30" y="38" font-size="15" font-weight="700" fill="#0b2026">Proyecto: bank-tunombre</text>
# MAGIC   <rect x="40" y="60" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="135" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">production</text>
# MAGIC   <text x="135" y="104" text-anchor="middle" font-size="12" fill="#5A6F77">el banco limpio, nunca se toca</text>
# MAGIC   <rect x="280" y="60" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="375" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-tunombre</text>
# MAGIC   <text x="375" y="104" text-anchor="middle" font-size="12" fill="#5A6F77">tu rama, de la configuración</text>
# MAGIC   <rect x="280" y="146" width="190" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="375" y="170" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-tunombre-exp</text>
# MAGIC   <text x="375" y="190" text-anchor="middle" font-size="12" fill="#5A6F77">el fork: crear, cambiar, borrar</text>
# MAGIC   <line x1="230" y1="88" x2="272" y2="88" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="272,82 282,88 272,94" fill="#1B5162"/>
# MAGIC   <line x1="375" y1="116" x2="375" y2="138" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <polygon points="369,138 375,148 381,138" fill="#FF3621"/>
# MAGIC   <text x="500" y="84" font-size="12" fill="#5A6F77">fork = copy-on-write:</text>
# MAGIC   <text x="500" y="102" font-size="12" fill="#5A6F77">no se copian datos, solo se</text>
# MAGIC   <text x="500" y="120" font-size="12" fill="#5A6F77">escriben las páginas que cambias</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Consulta CTA-100240 en tu rama
# MAGIC
# MAGIC `CTA-100240` es una cuenta de crédito de banca minorista de la sucursal CDMX Reforma, una de las
# MAGIC cuentas que cargaste en la configuración. Es una consulta normal, el mismo SQL que podrías ejecutar en
# MAGIC cualquier herramienta de Postgres:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status, health_pct FROM bank.account WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as c, c.cursor() as cur:
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("tu rama, antes:", cur.fetchone())

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `tu rama, antes: ('CTA-100240', 'watch', Decimal('91.00'))`
# MAGIC
# MAGIC **Qué demuestra:** tu rama tiene el banco que cargaste en la configuración. Contra esto vas a comparar el fork.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>NotFound: branch id not found</code>: tu rama todavía no existe. Ejecuta <code>00-setup/setup_databricks_es</code> o revisa el widget <code>LB_BRANCH</code>.</li>
# MAGIC       <li><code>None</code> en lugar de una fila, o <code>relation "account" does not exist</code>: el banco no está cargado en tu rama. Vuelve a ejecutar <code>00-setup/setup_databricks_es</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Crea el fork
# MAGIC
# MAGIC Crear una rama es una operación del control plane, no de SQL, así que este paso usa el SDK. La celda
# MAGIC primero borra cualquier fork que haya quedado de una ejecución anterior, luego crea una nueva y
# MAGIC mide cuánto tarda en estar lista. La misma llamada desde una terminal:
# MAGIC
# MAGIC ```bash
# MAGIC databricks postgres create-branch --profile "$LB_PROFILE" \
# MAGIC   --parent projects/$LB_PROJECT \
# MAGIC   --json '{"branch_id": "'$LB_BRANCH'-exp", "spec": {"source_branch": "projects/'$LB_PROJECT'/branches/'$LB_BRANCH'"}}'
# MAGIC ```

# COMMAND ----------

try:
    w.postgres.update_branch(name=branch_name(PROJECT, EXP),
        branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
    w.postgres.delete_branch(name=branch_name(PROJECT, EXP)); time.sleep(2)
except Exception:
    pass

t0 = time.time()
w.postgres.create_branch(parent=f"projects/{PROJECT}",
    branch=Branch(spec=BranchSpec(source_branch=branch_name(PROJECT, MINE), no_expiry=True)),
    branch_id=EXP, replace_existing=False)
api_ms = (time.time() - t0) * 1000
waited = wait_active(w, PROJECT, EXP)
print(f"API del fork {api_ms:.0f} ms; endpoint ACTIVE en ~{waited:.1f}s")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `API del fork 554 ms; endpoint ACTIVE en ~1.9s` en una ejecución de prueba. Tus números van a variar un poco.
# MAGIC
# MAGIC **Qué demuestra:** una copia completa de tu base de datos está lista para consultarse en unos dos segundos, sin copiar datos.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, selecciona tu proyecto y luego la pestaña <strong>Branches</strong>.
# MAGIC     El fork, <code>u-tunombre-exp</code>, aparece con tu rama como su rama de origen.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Error de permisos:</strong> crear una rama requiere <code>CAN_MANAGE</code> en el proyecto. Como el proyecto es tuyo, ya lo tienes: revisa que el widget <code>LB_PROJECT</code> tenga tu proyecto, <code>bank-tunombre</code>.</li>
# MAGIC       <li><code>TimeoutError: la rama ... no llegó a ACTIVE en 30s</code>: la primera rama de una sesión puede tardar más. Vuelve a ejecutar la celda.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Por qué el fork está listo en segundos y qué significan los dos números</strong></summary>
# MAGIC
# MAGIC Una rama de Lakebase usa copy-on-write. Crearla no copia tus datos: la rama nueva comparte el
# MAGIC almacenamiento de la rama de la que salió, tal como estaba en ese momento, y solo las páginas que
# MAGIC cambias en el fork se escriben por separado. Por eso el tiempo para crear un fork no
# MAGIC depende del tamaño de la base de datos.
# MAGIC
# MAGIC La celda imprime dos números. El **tiempo de la API**, muy por debajo de un segundo, es lo que tarda
# MAGIC Lakebase en aceptar la rama nueva. El **tiempo hasta ACTIVE**, unos dos segundos, incluye arrancar el
# MAGIC endpoint de cómputo al que te conectas. Si escuchas "ramas en menos de 500 ms", se refiere solo al
# MAGIC primer número, no a una base de datos que ya puedas consultar.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Congela la cuenta en el fork y compara
# MAGIC
# MAGIC Congela `CTA-100240` solo en el fork y luego léela desde las dos ramas. El SQL que se ejecuta en
# MAGIC el fork:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'frozen', health_pct = 70.0 WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect_branch(EXP) as c, c.cursor() as cur:
    cur.execute("UPDATE account SET status='frozen', health_pct=70.0 WHERE account_id=%s", [ACCOUNT])
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("fork, después del cambio:", cur.fetchone())

with connect_branch(MINE) as c, c.cursor() as cur:
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("tu rama, sin cambios:    ", cur.fetchone())

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC fork, después del cambio: ('CTA-100240', 'frozen', Decimal('70.00'))
# MAGIC tu rama, sin cambios:     ('CTA-100240', 'watch', Decimal('91.00'))
# MAGIC ```
# MAGIC
# MAGIC Dos bases de datos en uso, una bifurcada de la otra hace un minuto, ahora tienen datos distintos
# MAGIC sobre la misma cuenta.
# MAGIC
# MAGIC **Qué demuestra:** un cambio en una rama se queda en esa rama. Tu rama, y `production` detrás de ella, nunca vieron el congelamiento.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Una nota sobre datos regulados</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Una rama de producción es una copia completa de los datos de producción, incluidos los datos de
# MAGIC     clientes. Aplícale los mismos controles de acceso que a producción y borra los forks cuando
# MAGIC     termine el experimento.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Borra el fork
# MAGIC
# MAGIC Borrar el fork lo elimina junto con su endpoint. Tu rama no se ve afectada, porque el
# MAGIC fork solo escribió sus propias páginas modificadas.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, EXP),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
w.postgres.delete_branch(name=branch_name(PROJECT, EXP))
print("descartado", EXP)
print("ramas ahora:", [b.branch_id for b in w.postgres.list_branches(parent=f"projects/{PROJECT}")])

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `descartado u-tunombre-exp` y luego una lista de ramas que incluye
# MAGIC `production` y tu rama, pero no el fork.
# MAGIC
# MAGIC **Qué demuestra:** el experimento ya no existe y tu rama sigue ahí, sin cambios.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Congelaste `CTA-100240` en el fork. ¿Por qué tu rama seguía mostrando `watch`?</strong></summary>
# MAGIC
# MAGIC Una rama es una copia independiente. El fork escribió el cambio en sus propias páginas, así que tu rama nunca lo vio.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué el fork estuvo listo en unos dos segundos, si es una copia completa?</strong></summary>
# MAGIC
# MAGIC Por copy-on-write: crear la rama no copia datos. Casi todo el tiempo se va en arrancar el endpoint del fork.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Para crear el fork usaste el SDK, pero para leer la cuenta usaste SQL. ¿Por qué?</strong></summary>
# MAGIC
# MAGIC Las ramas se administran con la API de Lakebase (el control plane). Los datos se leen y se cambian con SQL.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio bifurcaste una base de datos en uso, congelaste una cuenta en el fork,
# MAGIC demostraste que tu rama no cambió y borraste el fork. Puntos clave:
# MAGIC
# MAGIC 1. **Una rama es una copia completa y aislada de la base de datos** que casi no cuesta crear, porque
# MAGIC    el almacenamiento usa copy-on-write.
# MAGIC 2. **Está lista en segundos:** la API responde en menos de un segundo y el endpoint queda ACTIVE en
# MAGIC    unos dos.
# MAGIC 3. **Los cambios en una rama nunca llegan a su rama de origen,** y borrar una rama no afecta a su rama de origen.
# MAGIC 4. **Usa las ramas como usas las ramas de git:** una por experimento, por pull request o por cada
# MAGIC    "¿qué pasaría si...?", en lugar de esa copia de la base de datos que siempre evitas hacer.
# MAGIC
# MAGIC El siguiente recorrido usa el mismo mecanismo hacia el pasado: restaurar a un punto en el tiempo es
# MAGIC crear una rama desde un momento anterior.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la Parte 1:** <a href="$../break-and-rewind/break_and_rewind_databricks_es">Restauración a un punto en el tiempo →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
