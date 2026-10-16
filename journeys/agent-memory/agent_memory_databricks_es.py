# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de agentes · Recorrido 1 de 5 · Memoria compartida entre agentes</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Memoria compartida entre agentes
# MAGIC #### Duración: unos 20 minutos
# MAGIC
# MAGIC *Recorrido 1 de 5. La Parte 1 mostró lo que Lakebase hace con tus datos. Esta ruta pone agentes de IA encima, empezando por lo más básico que necesita un agente: un lugar donde recordar.*
# MAGIC
# MAGIC ## Descripción general
# MAGIC
# MAGIC Durante la noche, la cola de fraude marcó `CTA-100240`: una transferencia SPEI nocturna de MXN 38,500
# MAGIC a un beneficiario nuevo, con un puntaje de anomalía de 8.7. Un agente asesor de fraude escribió una
# MAGIC nota al respecto. En la mañana, a un agente asistente de operaciones le preguntan si ya se puede
# MAGIC liberar la retención de la cuenta. Debería dar la misma respuesta que daría el asesor de fraude, sin
# MAGIC que los dos agentes hablen entre sí.
# MAGIC
# MAGIC En este laboratorio los dos agentes comparten una tabla de Postgres en tu rama. Cada agente lee la
# MAGIC tabla, le pide su respuesta a un modelo real (un endpoint de Foundation Model en este workspace) y
# MAGIC agrega su turno. Sin cola de mensajes, sin caché, sin servicio de orquestación: solo una tabla
# MAGIC gobernada.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio, vas a poder:
# MAGIC
# MAGIC 1. **Cargar memoria compartida** para agentes como filas de una tabla de Lakebase.
# MAGIC 2. **Anclar la respuesta de un modelo** en esa memoria: leerla con SQL y pasarla en el prompt.
# MAGIC 3. **Pasar contexto de un agente a otro** agregando turnos a la misma tabla.
# MAGIC 4. **Explicar por qué una base de datos sirve como memoria de agentes:** es durable, consistente, consultable y gobernada como cualquier otra tabla.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Memoria del agente:** lo que un agente sabe de turnos anteriores. Aquí son filas de `bank.agent_memory`, una por mensaje.
# MAGIC - **Namespace y sesión:** las columnas `namespace` y `session_id` delimitan la memoria, para que distintos equipos o conversaciones no vean las filas de los demás. Este laboratorio usa `default` / `sess-01`.
# MAGIC - **Endpoint de Foundation Model:** un modelo servido por Model Serving de Databricks. El notebook lo llama por HTTPS con tu identidad de Databricks. El predeterminado es `databricks-claude-opus-4-8`.
# MAGIC - **Grounding (anclar la respuesta en los datos):** poner hechos (aquí, las filas de memoria) en el prompt, para que el modelo responda con ellos y no con su conocimiento general.
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
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. Los agentes llaman al endpoint de
# MAGIC     Foundation Model <code>databricks-claude-opus-4-8</code>; debe estar <strong>Ready</strong> en este
# MAGIC     workspace (barra lateral izquierda, <strong>Serving</strong>). Si no lo está, el notebook se ejecuta
# MAGIC     igual, con respuestas fijas.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="180" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="40" y="40" width="170" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="64" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">fraud_advisor</text>
# MAGIC   <text x="125" y="84" text-anchor="middle" font-size="12" fill="#5A6F77">agente 1</text>
# MAGIC   <rect x="40" y="114" width="170" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="138" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">ops_assistant</text>
# MAGIC   <text x="125" y="158" text-anchor="middle" font-size="12" fill="#5A6F77">agente 2</text>
# MAGIC   <rect x="290" y="70" width="190" height="70" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="385" y="98" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">bank.agent_memory</text>
# MAGIC   <text x="385" y="118" text-anchor="middle" font-size="12" fill="#5A6F77">una tabla en tu rama</text>
# MAGIC   <rect x="540" y="70" width="150" height="70" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="615" y="98" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">modelo</text>
# MAGIC   <text x="615" y="118" text-anchor="middle" font-size="12" fill="#5A6F77">claude-opus-4-8</text>
# MAGIC   <line x1="210" y1="68" x2="282" y2="95" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="282,89 290,98 279,100" fill="#1B5162"/>
# MAGIC   <line x1="210" y1="142" x2="282" y2="117" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="279,111 290,113 283,122" fill="#1B5162"/>
# MAGIC   <text x="250" y="60" text-anchor="middle" font-size="11" fill="#5A6F77">lee + agrega</text>
# MAGIC   <text x="250" y="168" text-anchor="middle" font-size="11" fill="#5A6F77">lee + agrega</text>
# MAGIC   <line x1="480" y1="105" x2="532" y2="105" stroke="#5A6F77" stroke-width="2" stroke-dasharray="4 3"/>
# MAGIC   <polygon points="532,99 542,105 532,111" fill="#5A6F77"/>
# MAGIC   <text x="510" y="94" text-anchor="middle" font-size="11" fill="#5A6F77">prompt</text>
# MAGIC </svg>
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
# MAGIC ### A2. Conéctate y define la llamada al modelo
# MAGIC
# MAGIC Esta celda carga el helper compartido de `common/scripts/` y define los nombres que usa el
# MAGIC laboratorio: la tabla de memoria, la sesión y la pregunta que los dos agentes van a responder.
# MAGIC
# MAGIC - `connect()` abre una conexión de Postgres a tu rama. Por dentro, le pide a la API de Lakebase el
# MAGIC   nombre de host de la rama, obtiene un token de inicio de sesión de tu identidad de Databricks
# MAGIC   (válido por cerca de una hora) y se conecta con `psycopg`, un driver de Postgres para Python.
# MAGIC - `fm_call()` envía una lista de mensajes de chat al endpoint de Foundation Model por HTTPS, con tu
# MAGIC   sesión, y regresa el texto del modelo. Si la llamada falla, imprime por qué y regresa `None`, y el
# MAGIC   agente usa una respuesta fija.
# MAGIC
# MAGIC Los prompts de los agentes están en inglés, con una instrucción para que el modelo responda en
# MAGIC español de México. Las notas y la pregunta son datos del banco y se quedan en inglés.
# MAGIC
# MAGIC En los pasos siguientes, el bloque SQL de cada paso es la sentencia que se ejecuta en tu rama. La
# MAGIC celda de Python debajo envía esa sentencia e imprime el resultado.

# COMMAND ----------

import os, sys
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "bank.agent_memory"
QUESTION = "Is CTA-100240 cleared, or do we freeze it for suspected fraud?"

def fm_call(messages, max_tokens=400):
    """Llama a la API de Foundation Model; regresa el texto, o None para usar la respuesta de respaldo."""
    try:
        w = client()
        tok = w.config.authenticate()["Authorization"][len("Bearer "):]
        r = requests.post(
            f"{w.config.host}/serving-endpoints/{FM_ENDPOINT}/invocations",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"messages": messages, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  (API de FM no disponible: {e}; se usa la simulación de respaldo)")
        return None

print(f"Sesión: {SESSION_ID}, endpoint de FM: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `Sesión: sess-01, endpoint de FM: databricks-claude-opus-4-8`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> en una celda posterior: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego esta.</li>
# MAGIC       <li>Tu taller usa otro endpoint de modelo: cambia el valor predeterminado en la línea <code>FM_ENDPOINT = ...</code> de esta celda y vuelve a ejecutarla.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Carga la memoria compartida
# MAGIC
# MAGIC Empieza la sesión con una nota del asesor de fraude, como si la hubiera escrito durante la noche.
# MAGIC Esta fila es el estado compartido que los dos agentes van a leer. Primero la celda borra las filas
# MAGIC anteriores de esta sesión, para que cada ejecución empiece limpia. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant',
# MAGIC         'CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.');
# MAGIC ```

# COMMAND ----------

SEED_NOTE = ("CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. "
             "Keep on watch, do not release the hold until the customer is reached.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE} WHERE namespace=%s AND session_id=%s", [NAMESPACE, SESSION_ID])
        cur.execute(
            f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", SEED_NOTE]
        )
print("Se cargó en agent_memory la nota de fraude previa")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `Se cargó en agent_memory la nota de fraude previa`
# MAGIC
# MAGIC **Qué demuestra:** la memoria de un agente es una fila común. Cualquier agente, app o analista con acceso a tu rama puede leerla.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>relation "bank.agent_memory" does not exist</code>: el banco no está cargado en tu rama. Vuelve a ejecutar <code>00-setup/setup_databricks_es</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Lee la memoria compartida
# MAGIC
# MAGIC Antes de responder, un agente lee todo lo de su sesión, de lo más antiguo a lo más reciente. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT agent_id, role, content FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01'
# MAGIC ORDER BY created_at;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        rows = cur.fetchall()

print(f"Memoria previa ({len(rows)} filas):")
for agent_id, role, content in rows:
    print(f"  {agent_id}: {content[:80]}..." if len(content) > 80 else f"  {agent_id}: {content}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Memoria previa (1 filas):
# MAGIC   fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly...
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la lectura es SQL normal, así que lo que un agente "recuerda" es exactamente lo que hay en la tabla, en orden.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, selecciona tu proyecto y tu rama, y luego la pestaña
# MAGIC     <strong>Tables</strong>. <code>agent_memory</code>, en el esquema <code>bank</code>, tiene la fila que acabas de escribir.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Responde el asesor de fraude
# MAGIC
# MAGIC El asesor de fraude recibe tres mensajes: su rol, las filas de memoria como contexto, y la pregunta
# MAGIC *"Is CTA-100240 cleared, or do we freeze it for suspected fraud?"* (¿se libera CTA-100240 o la
# MAGIC congelamos por sospecha de fraude?). Llama al modelo y luego agrega dos filas a la memoria: la
# MAGIC pregunta y su respuesta.

# COMMAND ----------

fraud_sys = ("You are a fraud advisor at a retail bank. You read overnight alerts and prior notes "
             "about account risk, including anomaly scores (0-10, higher is riskier). Decide whether "
             "an account should be cleared or kept on a hold / frozen for suspected fraud, grounded in "
             "the notes. Keep answers to 1-2 sentences. Answer in Spanish (Mexico).")

messages = [{"role": "system", "content": fraud_sys},
            {"role": "system", "content": "Prior context from shared memory:\n" +
             "\n".join(f"{a} ({r}): {c}" for a, r, c in rows)},
            {"role": "user", "content": QUESTION}]

response1 = fm_call(messages)
if response1 is None:
    response1 = ("CTA-100240 no se libera. Un puntaje de anomalía de 8.7 en una transferencia SPEI nocturna a "
                 "un beneficiario nuevo es una señal fuerte de fraude. Mantén la retención y verifica la "
                 "transferencia con el cliente antes de liberar fondos.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", response1])

print("fraud_advisor agregó:")
print(f"  {response1}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** la respuesta del modelo, que cambia en cada ejecución. De una ejecución de prueba:
# MAGIC
# MAGIC ```
# MAGIC fraud_advisor agregó:
# MAGIC   CTA-100240 permanece en retención por sospecha de fraude; no se libera hasta contactar al cliente, dado el SPEI nocturno de MXN 38,500 a un beneficiario nuevo con puntaje de anomalía de 8.7.
# MAGIC ```
# MAGIC
# MAGIC Revisa que la respuesta sea "mantener la retención" y que cite la nota: la transferencia SPEI, el puntaje de 8.7 o contactar al cliente.
# MAGIC
# MAGIC **Qué demuestra:** el modelo respondió con la memoria compartida. Lo único que su prompt tenía sobre esta cuenta era la fila que cargaste.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(API de FM no disponible: 404 Client Error: Not Found for url: ...; se usa la simulación de respaldo)</code>: el nombre del endpoint está mal o no existe en este workspace. Revisa <strong>Serving</strong> en la barra lateral izquierda y corrige <code>FM_ENDPOINT</code> en A2.</li>
# MAGIC       <li>Un error <code>403</code> en esa misma línea: no tienes permiso para consultar el endpoint. Pídele a tu instructor <code>CAN_QUERY</code> sobre él.</li>
# MAGIC       <li>Con una línea de respaldo, el laboratorio sigue funcionando: el agente usa una respuesta fija y el flujo de memoria es el mismo.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Responde el asistente de operaciones
# MAGIC
# MAGIC El asistente de operaciones lee la memoria **completa**, incluida la respuesta del asesor de fraude,
# MAGIC y recibe la misma pregunta. Su rol le pide atenerse a la determinación del asesor de fraude cuando
# MAGIC exista. Agrega su propia pregunta y su respuesta.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        full_memory = cur.fetchall()

print(f"Memoria completa para el asistente de operaciones ({len(full_memory)} filas):")
for agent_id, role, content in full_memory:
    print(f"  {agent_id}: {content[:70]}..." if len(content) > 70 else f"  {agent_id}: {content}")

ops_sys = ("You are an operations assistant at a retail bank branch. You release or keep account holds. "
           "You defer to the fraud advisor's determination when present in the shared notes. Answer whether "
           "the hold stays or can be released, grounded in the notes. Keep answers to 1-2 sentences. "
           "Answer in Spanish (Mexico).")

messages2 = [{"role": "system", "content": ops_sys},
             {"role": "system", "content": "Prior context from shared memory:\n" +
              "\n".join(f"{a} ({r}): {c}" for a, r, c in full_memory)},
             {"role": "user", "content": QUESTION}]

response2 = fm_call(messages2)
if response2 is None:
    response2 = ("Mantengo la retención de CTA-100240 y no libero fondos, de acuerdo con la determinación del "
                 "asesor de fraude. Primero voy a contactar al cliente para confirmar la transferencia nocturna.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "assistant", response2])

print(f"\nops_assistant agregó:")
print(f"  {response2}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** tres filas de memoria y luego la respuesta del asistente de operaciones. De una ejecución de prueba:
# MAGIC
# MAGIC ```
# MAGIC Memoria completa para el asistente de operaciones (3 filas):
# MAGIC   fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiar...
# MAGIC   fraud_advisor: Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   fraud_advisor: CTA-100240 permanece en retención por sospecha de fraude; no se libera...
# MAGIC
# MAGIC ops_assistant agregó:
# MAGIC   La cuenta CTA-100240 permanece en retención por sospecha de fraude; no se libera hasta contactar al cliente, debido al SPEI nocturno de MXN 38,500 a un beneficiario nuevo con puntaje de anomalía de 8.7.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el segundo agente tomó la decisión del primero desde la tabla. Nunca se llamaron entre sí.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Por qué una tabla, y no una caché o una cola de mensajes</strong></summary>
# MAGIC
# MAGIC Los agentes necesitan una memoria que sobreviva a los reinicios, que dos agentes puedan leer y
# MAGIC escribir al mismo tiempo sin perder un turno, y que alguien pueda auditar después. Una tabla de
# MAGIC Postgres te da las tres cosas: las escrituras son durables en cuanto se confirman, cada lector ve las
# MAGIC filas confirmadas y el historial está a un `SELECT` de distancia. Además se gobierna como el resto
# MAGIC de tus datos, así que aplican los mismos controles de acceso.
# MAGIC
# MAGIC Las columnas `namespace` y `session_id` sirven para separar la memoria: un namespace por equipo o
# MAGIC producto, una sesión por conversación. Agrega un índice sobre `(namespace, session_id, created_at)`
# MAGIC cuando la tabla crezca.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Lee la conversación completa
# MAGIC
# MAGIC La sesión completa, de lo más antiguo a lo más reciente. Es la misma consulta de C; solo que ahora
# MAGIC hay más filas.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        final_memory = cur.fetchall()

print(f"Memoria final ({len(final_memory)} filas en total):")
for agent_id, role, content in final_memory:
    print(f"  [{agent_id}] {content}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** cinco filas, en el orden en que se escribieron (aquí las dos respuestas van recortadas):
# MAGIC
# MAGIC ```
# MAGIC Memoria final (5 filas en total):
# MAGIC   [fraud_advisor] CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.
# MAGIC   [fraud_advisor] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   [fraud_advisor] CTA-100240 permanece en retención por sospecha de fraude; ...
# MAGIC   [ops_assistant] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   [ops_assistant] La cuenta CTA-100240 permanece en retención por sospecha de fraude; ...
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la tabla es el registro completo y ordenado de lo que los dos agentes vieron y dijeron.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Cómo supo el asistente de operaciones lo que había decidido el asesor de fraude?</strong></summary>
# MAGIC
# MAGIC Leyó la tabla `agent_memory`, que ya tenía la respuesta del asesor de fraude. Los dos agentes nunca se enviaron mensajes.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué la respuesta del modelo menciona la transferencia SPEI y el puntaje de 8.7?</strong></summary>
# MAGIC
# MAGIC Porque las filas de memoria se le pasaron al modelo en su prompt. Eso es grounding: la respuesta sale de tus datos, no de lo que el modelo ya sabía.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Para qué sirven las columnas namespace y session_id?</strong></summary>
# MAGIC
# MAGIC Delimitan la memoria, para que las filas de un equipo o de una conversación no se mezclen con las de otra. Cada lectura filtra por las dos.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusión
# MAGIC
# MAGIC En este laboratorio dos agentes compartieron una tabla de Lakebase: el asesor de fraude leyó una nota
# MAGIC cargada y respondió, y el asistente de operaciones leyó las dos y se atuvo a esa decisión. Puntos
# MAGIC clave:
# MAGIC
# MAGIC 1. **La memoria de un agente puede ser una tabla común:** se lee con `SELECT` y se agrega con `INSERT`, sin otro sistema.
# MAGIC 2. **El grounding es solo SQL más un prompt:** lees las filas, se las pasas al modelo y su respuesta sigue tus datos.
# MAGIC 3. **Los agentes se coordinan a través de los datos,** no llamándose entre sí: lo que uno escribe, el siguiente lo lee.
# MAGIC 4. **La memoria es gobernada y auditable** como cualquier otra tabla de tu rama.
# MAGIC
# MAGIC El siguiente recorrido le da herramientas a un agente: lee el riesgo de una cuenta, la retiene y usa
# MAGIC esta misma tabla de memoria para no hacerlo dos veces.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de agentes:** <a href="$../agentic-work/agentic_work_databricks_es">Agentes que usan herramientas →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
