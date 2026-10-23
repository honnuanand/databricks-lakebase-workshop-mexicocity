# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 1 · Recorrido 4 de 5 · Escalar a cero</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Escalar a cero
# MAGIC #### Duración: unos 10 minutos
# MAGIC
# MAGIC *Recorrido 4 de 5. Ya viste lo que Lakebase hace con tus datos. Este trata del costo: cuánto cuesta tu rama cuando nadie la usa.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Son las 23:00 de un viernes. Las mesas de operación cerraron, los procesos de liquidación ya
# MAGIC corrieron, y las bases de datos de desarrollo y pruebas de cada equipo no van a recibir una consulta
# MAGIC hasta el lunes. Una base de datos siempre encendida cobra esas horas de inactividad de todos modos.
# MAGIC
# MAGIC El cómputo de Lakebase que no recibe consultas se suspende solo después de un tiempo definido, su
# MAGIC **suspend timeout** (tiempo de suspensión), y no cuesta nada de cómputo mientras está suspendido. La
# MAGIC siguiente consulta lo despierta en menos de un segundo. Tus datos no se ven afectados, porque el
# MAGIC almacenamiento está separado del cómputo.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Leer el estado del cómputo:** `ACTIVE` (encendido y con costo) o `IDLE` (suspendido, sin costo de cómputo).
# MAGIC 2. **Explicar cuándo se suspende el cómputo** y dónde se configura su suspend timeout.
# MAGIC 3. **Despertar un cómputo suspendido** con una consulta y medir cuánto tarda.
# MAGIC 4. **Explicar por qué tus datos no se ven afectados:** solo se detiene el cómputo; el almacenamiento se queda.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Cómputo vs. almacenamiento:** Lakebase separa el servidor de Postgres que ejecuta las consultas (cómputo) del lugar donde se guardan los datos (almacenamiento). El cómputo puede detenerse y arrancar sin tocar el almacenamiento.
# MAGIC - **Unidad de capacidad (CU):** la forma de medir el tamaño del cómputo. Tu proyecto del taller usa 1 CU fija por rama.
# MAGIC - **ACTIVE e IDLE:** el estado de un endpoint. `ACTIVE` está encendido y genera costo de cómputo; `IDLE` está suspendido, sin costo de cómputo.
# MAGIC - **Suspend timeout (tiempo de suspensión):** cuánto espera un endpoint sin consultas antes de suspenderse: 5 minutos en tu proyecto del taller. El almacenamiento se sigue cobrando mientras el endpoint está inactivo.
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
# MAGIC ### A2. Conéctate
# MAGIC
# MAGIC Esta celda define `endpoint_state()`, que le pregunta a Lakebase el estado del cómputo de una rama. Es
# MAGIC una llamada del control plane a través del SDK, así que no despierta el cómputo.
# MAGIC
# MAGIC La consulta cronometrada de D se conecta igual que los módulos de ayuda de los otros recorridos:
# MAGIC obtiene un token de inicio de sesión con tu identidad de Databricks (válido por cerca de una hora) y
# MAGIC abre una conexión estándar de Postgres con `psycopg`. El `SELECT 1` que envía es el SQL que se muestra
# MAGIC en D.

# COMMAND ----------

import os, sys, time, psycopg
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, PG_PORT, DEFAULT_DB

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
w = client()

def endpoint_state(branch):
    e = list(w.postgres.list_endpoints(parent=branch_name(PROJECT, branch)))[0]
    st = e.status.current_state.value if e.status and e.status.current_state else "?"
    host = e.status.hosts.host if e.status and e.status.hosts else None
    return st, host, (e.endpoint_id or "primary")

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

# MAGIC %md
# MAGIC ## B. Revisa el estado del cómputo
# MAGIC
# MAGIC `ACTIVE` significa que el cómputo está encendido y genera costo. `IDLE` significa que se suspendió solo
# MAGIC y no genera costo de cómputo.

# COMMAND ----------

st, host, eid = endpoint_state(MINE)
print(f"rama {MINE}: el endpoint {eid} está {st}")
print("IDLE = suspendido en cero (sin costo de cómputo); ACTIVE = atendiendo consultas (con costo).")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado**, según cuánto tiempo haya pasado desde que usaste tu rama:
# MAGIC
# MAGIC ```
# MAGIC rama u-tunombre: el endpoint primary está ACTIVE
# MAGIC IDLE = suspendido en cero (sin costo de cómputo); ACTIVE = atendiendo consultas (con costo).
# MAGIC ```
# MAGIC
# MAGIC `ACTIVE` si ejecutaste el recorrido anterior hace unos minutos; `IDLE` si tu rama lleva 5 minutos o más
# MAGIC sin consultas. La sección C explica por qué.
# MAGIC
# MAGIC **Qué demuestra:** puedes ver si el cómputo está encendido sin enviarle una consulta, así que revisarlo no lo despierta.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>IndexError: list index out of range</code>: la rama de <code>LB_BRANCH</code> no tiene cómputo. Revisa el nombre en el widget.</li>
# MAGIC       <li><code>NotFound: branch id not found</code>: tu rama todavía no existe. Ejecuta <code>00-setup/setup_databricks_es</code> o revisa el widget <code>LB_BRANCH</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## C. Cuándo se suspende el cómputo
# MAGIC
# MAGIC Nunca detienes el cómputo tú mismo. Se suspende después de un periodo sin consultas: su **suspend
# MAGIC timeout**. El suspend timeout se configura por cómputo, así que una base de datos de producción puede
# MAGIC estar encendida todo el día mientras las ramas de desarrollo y pruebas se suspenden rápido.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     En la app <strong>Lakebase Postgres</strong>, abre tu proyecto, selecciona tu rama y elige
# MAGIC     <strong>Edit</strong> en <strong>Computes</strong>. La opción <strong>Scale to zero</strong> tiene el suspend timeout.
# MAGIC     La pestaña <strong>Monitoring</strong> muestra los eventos de suspensión y arranque en <strong>System Operations</strong>.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC **En tu proyecto del taller, el suspend timeout es de 5 minutos.** Si B mostró `ACTIVE`, todavía puedes
# MAGIC ver un arranque en frío: no uses tu rama durante 5 minutos (lee las notas de abajo o tómate un descanso)
# MAGIC y vuelve a ejecutar la celda de B. Cuando muestre `IDLE`, ejecuta D. Revisar el estado no cuenta como
# MAGIC consulta, así que no mantiene despierto el cómputo.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cómo elegir un suspend timeout</strong></summary>
# MAGIC
# MAGIC Un suspend timeout corto es el que más ahorra, y conviene para las ramas de desarrollo, de pruebas y de
# MAGIC cada desarrollador, que pasan inactivas la mayor parte del día. El costo es que la primera consulta
# MAGIC después de un rato sin uso espera un poco más, unos dos tercios de segundo en nuestra prueba, mientras
# MAGIC arranca el cómputo.
# MAGIC
# MAGIC Para una base de datos de producción que atiende a una aplicación todo el día, un suspend timeout
# MAGIC largo, o dejar el cómputo siempre encendido, evita ese retraso en la primera consulta. Como el suspend
# MAGIC timeout se configura por cómputo, cada rama puede usar el valor que le conviene.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Despiértalo con una consulta
# MAGIC
# MAGIC Un solo `SELECT 1` despierta el cómputo. Despertar tiene que ver con el cómputo, no con las tablas, así
# MAGIC que funciona en cualquier rama. La celda cronometra todo: obtener el token de inicio de sesión,
# MAGIC conectarse y ejecutar la consulta.
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 1;
# MAGIC ```

# COMMAND ----------

st, host, eid = endpoint_state(MINE)
cold = (st == "IDLE")
print("el endpoint está IDLE; midiendo el arranque..." if cold else f"el endpoint está {st} (en caliente, no es un arranque en frío)")
t0 = time.time()
cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, MINE)}/endpoints/{eid}")
conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                       user=w.current_user.me().user_name, password=cred.token,
                       sslmode="require", autocommit=True, connect_timeout=30)
with conn.cursor() as cur:
    cur.execute("SELECT 1"); cur.fetchone()
dt = (time.time() - t0) * 1000
conn.close()
st2, _, _ = endpoint_state(MINE)
print(f"{'despertó IDLE -> ' + st2 if cold else st2}; la primera consulta respondió en {dt:.0f} ms")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado**, según el estado de B (números de nuestras ejecuciones de prueba):
# MAGIC
# MAGIC - **Arranque en frío** (estaba `IDLE`):
# MAGIC   ```
# MAGIC   el endpoint está IDLE; midiendo el arranque...
# MAGIC   despertó IDLE -> ACTIVE; la primera consulta respondió en 865 ms
# MAGIC   ```
# MAGIC - **En caliente** (ya estaba `ACTIVE`):
# MAGIC   ```
# MAGIC   el endpoint está ACTIVE (en caliente, no es un arranque en frío)
# MAGIC   ACTIVE; la primera consulta respondió en 189 ms
# MAGIC   ```
# MAGIC
# MAGIC Los dos tiempos incluyen obtener el token de inicio de sesión y abrir la conexión. La diferencia, de
# MAGIC menos de un segundo, es el arranque del cómputo. Tus números van a variar.
# MAGIC
# MAGIC **Qué demuestra:** una base de datos suspendida regresa sola con la primera consulta. No hay botón para encenderla, y la consulta funciona de todos modos.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Confirma que vuelve a atender consultas
# MAGIC
# MAGIC Suspenderse nunca toca tus datos; solo se detuvo y arrancó el cómputo.

# COMMAND ----------

st, _, _ = endpoint_state(MINE)
print(f"el endpoint de la rama {MINE} ahora está {st}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `el endpoint de la rama u-tunombre ahora está ACTIVE`
# MAGIC
# MAGIC **Qué demuestra:** la primera consulta despertó el cómputo. Se queda `ACTIVE` hasta que vuelva a pasar 5 minutos sin consultas.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Tu rama mostró `ACTIVE` justo después del recorrido anterior. ¿Por qué?</strong></summary>
# MAGIC
# MAGIC Recibió una consulta en los últimos 5 minutos, el suspend timeout.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué pagas mientras un endpoint está `IDLE`?</strong></summary>
# MAGIC
# MAGIC El almacenamiento. El costo de cómputo se detiene mientras el endpoint está suspendido.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué una base de datos de producción podría usar un suspend timeout más largo que una rama de desarrollo?</strong></summary>
# MAGIC
# MAGIC Para evitar el retraso del arranque en la primera consulta en una aplicación que atiende usuarios todo el día.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusión
# MAGIC
# MAGIC En este laboratorio leíste el estado del cómputo, viste cuándo se suspende y lo despertaste con una
# MAGIC consulta. Puntos clave:
# MAGIC
# MAGIC 1. **Un cómputo inactivo se suspende solo** después de su suspend timeout, y no cuesta nada de cómputo
# MAGIC    mientras está suspendido.
# MAGIC 2. **La siguiente consulta lo despierta,** en menos de un segundo en nuestra prueba.
# MAGIC 3. **El suspend timeout se configura por cómputo,** así que cada rama puede equilibrar el costo contra
# MAGIC    el retraso de la primera consulta.
# MAGIC 4. **Los datos nunca se ven afectados:** el almacenamiento está separado, y solo el cómputo se detiene
# MAGIC    y arranca.
# MAGIC
# MAGIC El último recorrido de la Parte 1 muestra que, para tus herramientas actuales, Lakebase es Postgres
# MAGIC estándar.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la Parte 1:** <a href="$../pg-integration/pg_integration_databricks_es">Conectar herramientas de Postgres →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
