# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de agentes · Recorrido 2 de 5 · Agentes que usan herramientas</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Agentes que usan herramientas
# MAGIC #### Duración: unos 20 minutos
# MAGIC
# MAGIC *Recorrido 2 de 5. En Memoria compartida entre agentes, los agentes solo hablaban. Aquí un agente actúa: cambia datos en tu rama y usa la misma tabla de memoria para recordar lo que hizo.*
# MAGIC
# MAGIC ## Descripción general
# MAGIC
# MAGIC `CTA-100240` sigue en `watch`, y su transacción más riesgosa, la transferencia SPEI nocturna, tiene un
# MAGIC puntaje de 8.7. Un agente de operaciones de fraude tiene dos herramientas: una lee el riesgo de una
# MAGIC cuenta y la otra la retiene. Debe retener la cuenta una vez, y solo una: si se lo piden otra vez,
# MAGIC tiene que darse cuenta de que el trabajo ya está hecho.
# MAGIC
# MAGIC Cada herramienta son unas cuantas líneas de SQL contra tu rama. En este laboratorio el orden de las
# MAGIC llamadas está fijo en el notebook (leer el riesgo y luego retener), y un modelo real explica cada
# MAGIC decisión con palabras sencillas. En un agente en producción, el modelo elegiría qué herramienta
# MAGIC llamar; el lado de la base de datos, que es el tema de este laboratorio, queda igual.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio, vas a poder:
# MAGIC
# MAGIC 1. **Escribir herramientas de agente en SQL** contra Lakebase: una que lee el estado y otra que lo cambia.
# MAGIC 2. **Registrar una acción en dos lugares** (el estado de la cuenta y una nota de caso), para que la vean las personas y los demás sistemas.
# MAGIC 3. **Hacer que un agente sea idempotente** revisando su memoria antes de actuar.
# MAGIC 4. **Explicar el papel del modelo:** explica la decisión; las herramientas y los datos hacen el trabajo.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Herramienta:** una función que un agente puede llamar para leer o cambiar el mundo exterior. Aquí, `get_account_risk` y `place_hold` son SQL en tu rama.
# MAGIC - **Function calling (llamadas a funciones):** una capacidad del modelo para elegir una herramienta y sus argumentos. Este laboratorio fija el orden en el código, para que veas el efecto de cada herramienta paso a paso.
# MAGIC - **Acción idempotente:** una acción que da el mismo resultado si se ejecuta una o dos veces. El agente revisa su memoria primero, así que una segunda solicitud no pone una segunda retención.
# MAGIC - **Registro de auditoría:** la fila de `case_note` con `action='hold_placed'` registra qué hizo el agente, cuándo y por qué.
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
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. Las explicaciones del agente vienen del
# MAGIC     endpoint de Foundation Model <code>databricks-claude-opus-4-8</code> (barra lateral izquierda,
# MAGIC     <strong>Serving</strong>); si no está disponible, el notebook imprime una línea fija. No necesitas
# MAGIC     haber hecho antes Memoria compartida entre agentes.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 150" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="130" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="100" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">get_account_risk</text>
# MAGIC   <text x="100" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">lee estado + puntaje</text>
# MAGIC   <rect x="200" y="45" width="140" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="270" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">place_hold</text>
# MAGIC   <text x="270" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">congela + nota de caso</text>
# MAGIC   <rect x="370" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="440" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">recordar</text>
# MAGIC   <text x="440" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">agrega a la memoria</text>
# MAGIC   <rect x="540" y="45" width="150" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="615" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">otra solicitud</text>
# MAGIC   <text x="615" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">la memoria dice: no</text>
# MAGIC   <line x1="170" y1="73" x2="192" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="192,67 200,73 192,79" fill="#1B5162"/>
# MAGIC   <line x1="340" y1="73" x2="362" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="362,67 370,73 362,79" fill="#1B5162"/>
# MAGIC   <line x1="510" y1="73" x2="532" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="532,67 540,73 532,79" fill="#1B5162"/>
# MAGIC   <text x="360" y="125" text-anchor="middle" font-size="11" fill="#5A6F77">todas las lecturas y escrituras son SQL en tu rama; el modelo explica los pasos 2 y 4</text>
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
# MAGIC ### A2. Conéctate y define la llamada al modelo
# MAGIC
# MAGIC Esta celda carga el helper compartido de `common/scripts/` y nombra la cuenta y las tablas con las
# MAGIC que trabaja el agente.
# MAGIC
# MAGIC - `connect()` abre una conexión de Postgres a tu rama. Por dentro, le pide a la API de Lakebase el
# MAGIC   nombre de host de la rama, obtiene un token de inicio de sesión de tu identidad de Databricks
# MAGIC   (válido por cerca de una hora) y se conecta con `psycopg`, un driver de Postgres para Python.
# MAGIC - `fm_call()` envía mensajes de chat al endpoint de Foundation Model por HTTPS, con tu sesión, y
# MAGIC   regresa el texto del modelo, o `None` si la llamada falla (entonces se usa una línea fija).
# MAGIC
# MAGIC Los prompts están en inglés, con una instrucción para que el modelo responda en español de México.
# MAGIC
# MAGIC En los pasos siguientes, el bloque SQL de cada paso es lo que se ejecuta en tu rama.

# COMMAND ----------

import os, sys
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
ACCOUNT_ID = "CTA-100240"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE_MEMORY = "bank.agent_memory"
TABLE_ACCOUNT = "bank.account"
TABLE_TXN = "bank.txn"
TABLE_CASE = "bank.case_note"

def fm_call(messages, max_tokens=300):
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
        print(f"  (API de FM no disponible: {e}; se usa la respuesta de respaldo)")
        return None

print(f"Cuenta en revisión: {ACCOUNT_ID}, endpoint de FM: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `Cuenta en revisión: CTA-100240, endpoint de FM: databricks-claude-opus-4-8`
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
# MAGIC ### A3. Restablece la cuenta
# MAGIC
# MAGIC Regresa `CTA-100240` a `watch` y borra cualquier retención y memoria de una ejecución anterior, para
# MAGIC que la primera revisión aplique la retención y la segunda la rechace. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'watch' WHERE account_id = 'CTA-100240';
# MAGIC DELETE FROM bank.case_note WHERE account_id = 'CTA-100240' AND action = 'hold_placed';
# MAGIC DELETE FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01' AND content LIKE '%CTA-100240%';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE_ACCOUNT} SET status='watch' WHERE account_id=%s", [ACCOUNT_ID])
        cur.execute(f"DELETE FROM {TABLE_CASE} WHERE account_id=%s AND action='hold_placed'", [ACCOUNT_ID])
        cur.execute(f"DELETE FROM {TABLE_MEMORY} WHERE namespace=%s AND session_id=%s AND content LIKE %s",
                    [NAMESPACE, SESSION_ID, f"%{ACCOUNT_ID}%"])

print(f"Preparada: {ACCOUNT_ID} de vuelta en 'watch', lista para revisión")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Preparada: CTA-100240 de vuelta en 'watch', lista para revisión`
# MAGIC
# MAGIC Esto también borra las filas de `CTA-100240` que escribió Memoria compartida entre agentes, si ya lo hiciste.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Revisa la cuenta
# MAGIC
# MAGIC Consulta la cuenta y su transacción más riesgosa. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, line, type, status, health_pct FROM bank.account WHERE account_id = 'CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT account_id, line, type, status, health_pct FROM {TABLE_ACCOUNT} WHERE account_id=%s", [ACCOUNT_ID])
        acct = cur.fetchone()
        cur.execute(f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s", [ACCOUNT_ID])
        top_score = cur.fetchone()[0]

print(f"Estado inicial:")
print(f"  {ACCOUNT_ID}: {acct[1]} ({acct[2]}), status={acct[3]}, health={acct[4]}%")
print(f"  anomaly_score más alto de sus transacciones: {top_score}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Estado inicial:
# MAGIC   CTA-100240: Credit (retail), status=watch, health=91.00%
# MAGIC   anomaly_score más alto de sus transacciones: 8.70
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el agente parte de datos vivos: una cuenta de crédito de banca minorista en `watch`, con una transacción de puntaje 8.7.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>TypeError: 'NoneType' object is not subscriptable</code>: <code>CTA-100240</code> no está en tu rama. El banco no está cargado; vuelve a ejecutar <code>00-setup/setup_databricks_es</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Herramienta 1: lee el riesgo de la cuenta
# MAGIC
# MAGIC La primera herramienta que llama el agente, `get_account_risk`, lee el estado y el puntaje de
# MAGIC anomalía más alto. Los puntajes van de 0 a 10; el agente toma 8 o más como una señal fuerte de
# MAGIC fraude. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT status FROM bank.account WHERE account_id = 'CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status FROM {TABLE_ACCOUNT} WHERE account_id=%s", [ACCOUNT_ID])
        status = cur.fetchone()[0]
        cur.execute(f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s", [ACCOUNT_ID])
        top_score = cur.fetchone()[0]

print(f"Riesgo de la cuenta: status={status}, anomaly_score más alto={top_score}")
if top_score and float(top_score) >= 8.0:
    print(f"  Señal fuerte de fraude. El agente va a retener la cuenta.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Riesgo de la cuenta: status=watch, anomaly_score más alto=8.70
# MAGIC   Señal fuerte de fraude. El agente va a retener la cuenta.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** una herramienta es solo una consulta. Lo que el agente sabe de la cuenta es exactamente lo que hay en tu rama.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Herramienta 2: retén la cuenta
# MAGIC
# MAGIC La segunda herramienta, `place_hold`, hace una acción lógica con dos escrituras: congela la cuenta y
# MAGIC escribe una fila en `case_note` que registra la retención. Luego el modelo explica la acción en una o
# MAGIC dos oraciones. La nota de caso es un dato del banco y se queda en inglés. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'frozen' WHERE account_id = 'CTA-100240';
# MAGIC INSERT INTO bank.case_note (account_id, writeup, category, finding, action, confidence)
# MAGIC VALUES ('CTA-100240', 'Automated hold: anomaly_score 8.70 on a late-night SPEI transfer to a new beneficiary.',
# MAGIC         'fraud', 'spei_new_beneficiary_anomaly_8.70', 'hold_placed', 0.95);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE_ACCOUNT} SET status='frozen' WHERE account_id=%s", [ACCOUNT_ID])
        cur.execute(
            f"""INSERT INTO {TABLE_CASE} (account_id, writeup, category, finding, action, confidence)
               VALUES (%s, %s, 'fraud', %s, 'hold_placed', 0.95)""",
            [ACCOUNT_ID,
             f"Automated hold: anomaly_score {top_score} on a late-night SPEI transfer to a new beneficiary.",
             f"spei_new_beneficiary_anomaly_{top_score}"]
        )

print(f"Retención aplicada a {ACCOUNT_ID}: cuenta congelada, se escribió la marca en case_note")

# El modelo explica la decisión; si la llamada falla, se usa una línea fija.
narrated = fm_call([
    {"role": "system", "content": (
        "You are a fraud-ops agent at a retail bank. You just read an account's status and "
        "its top transaction anomaly score (0-10, higher is riskier), and placed a hold. "
        "State the action and the reason in one or two sentences. Answer in Spanish (Mexico).")},
    {"role": "user", "content": (
        f"Account {ACCOUNT_ID} status was '{status}', top anomaly_score {top_score}. "
        f"You placed a hold. Summarize.")},
])
response = narrated or (
    f"Se retuvo {ACCOUNT_ID} por un puntaje de anomalía de {top_score} en una transferencia SPEI nocturna "
    f"a un beneficiario nuevo. La cuenta queda congelada hasta verificar con el cliente."
)
print(f"\nRespuesta del agente:\n  {response}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** la retención y luego la explicación del modelo, que cambia en cada ejecución. De una ejecución de prueba:
# MAGIC
# MAGIC ```
# MAGIC Retención aplicada a CTA-100240: cuenta congelada, se escribió la marca en case_note
# MAGIC
# MAGIC Respuesta del agente:
# MAGIC   Se colocó una retención en la cuenta CTA-100240 debido a que su estatus estaba en observación ('watch') y presentó una puntuación de anomalía de 8.70, lo cual indica un riesgo elevado de fraude.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el agente cambió datos reales. La cuenta ahora está `frozen` y la nota de caso dice por qué.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, selecciona tu proyecto y tu rama, y luego la pestaña
# MAGIC     <strong>Tables</strong>. En <code>account</code>, <code>CTA-100240</code> está <code>frozen</code>; en
# MAGIC     <code>case_note</code>, la fila más reciente tiene <code>action = hold_placed</code>.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(API de FM no disponible: 404 Client Error: Not Found for url: ...; se usa la respuesta de respaldo)</code>: el nombre del endpoint está mal o no existe en este workspace. La retención sí se aplicó; solo la explicación es la línea fija. Para usar un modelo, corrige <code>FM_ENDPOINT</code> en A2.</li>
# MAGIC       <li>Un error <code>403</code> en esa misma línea: no tienes permiso para consultar el endpoint. Pídele a tu instructor <code>CAN_QUERY</code> sobre él.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Recuerda la acción
# MAGIC
# MAGIC El agente agrega lo que hizo a la tabla de memoria compartida de Memoria compartida entre agentes. La
# MAGIC fila es un dato y se queda en inglés, porque el paso F la busca por ese texto. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant', 'placed hold on CTA-100240');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TABLE_MEMORY} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", f"placed hold on {ACCOUNT_ID}"]
        )

print(f"La retención quedó registrada en agent_memory")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `La retención quedó registrada en agent_memory`
# MAGIC
# MAGIC **Qué demuestra:** la decisión del agente ya es durable. Cualquier llamada posterior, de este agente o de otro, puede leerla.

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Vuelve a pedirlo: el agente se niega
# MAGIC
# MAGIC Llega una segunda solicitud: revisar `CTA-100240` y actuar sobre la señal de fraude. Antes de llamar
# MAGIC a cualquier herramienta, el agente lee su memoria. Encuentra la retención que ya aplicó, se niega a
# MAGIC aplicar otra y el modelo redacta el rechazo. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT content FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01'
# MAGIC   AND agent_id = 'fraud_advisor' AND content LIKE '%hold on CTA-100240%';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT content FROM {TABLE_MEMORY} "
            f"WHERE namespace=%s AND session_id=%s AND agent_id='fraud_advisor' AND content LIKE %s",
            [NAMESPACE, SESSION_ID, f"%hold on {ACCOUNT_ID}%"]
        )
        prior = cur.fetchone()

if prior:
    print(f"El agente lee su memoria: \"{prior[0]}\"")
    print(f"SE NIEGA: {ACCOUNT_ID} ya tiene una retención. No se repite la acción.")
    # El modelo redacta el rechazo; si la llamada falla, se usa una línea fija.
    refusal = fm_call([
        {"role": "system", "content": (
            "You are a fraud-ops agent. You previously placed a hold on this account. "
            "Decline to act again in one sentence. Answer in Spanish (Mexico).")},
        {"role": "user", "content": f"Prior memory says: a hold is already placed on "
                                     f"{ACCOUNT_ID}. The request is: Review {ACCOUNT_ID} and act on the fraud signal"},
    ])
    print(f"\nRespuesta del agente:\n  {refusal or f'{ACCOUNT_ID} ya tiene una retención. No hace falta repetir la acción.'}")
else:
    print(f"No se encontró una retención previa")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** de una ejecución de prueba (la última oración viene del modelo y cambia):
# MAGIC
# MAGIC ```
# MAGIC El agente lee su memoria: "placed hold on CTA-100240"
# MAGIC SE NIEGA: CTA-100240 ya tiene una retención. No se repite la acción.
# MAGIC
# MAGIC Respuesta del agente:
# MAGIC   No puedo actuar de nuevo, pues ya se colocó una retención previa en la cuenta CTA-100240.
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** revisar la memoria antes de actuar hace que el agente sea idempotente: no hay segunda retención ni segunda nota de caso.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>¿Por qué escribir tanto en account.status como en case_note?</strong></summary>
# MAGIC
# MAGIC Responden preguntas distintas. `account.status = 'frozen'` es lo que revisan otros sistemas antes de
# MAGIC dejar que se mueva el dinero. La fila de `case_note` es el registro de auditoría: quién aplicó la
# MAGIC retención, por qué y con qué confianza. En producción, haz las dos en una sola transacción, para que
# MAGIC nunca quede una cuenta congelada sin motivo, ni un motivo sin congelamiento.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>De pasos fijos a function calling de verdad</strong></summary>
# MAGIC
# MAGIC Para que el modelo elija, le describes cada herramienta (nombre, propósito, argumentos) y ejecutas la
# MAGIC que pida, en un ciclo, hasta que responda. Las herramientas siguen siendo el mismo SQL de este
# MAGIC laboratorio, y la revisión de memoria de F se vuelve una herramienta más que el modelo puede llamar.
# MAGIC Las reglas de los datos (los valores de status, la marca `hold_placed`) son lo que mantiene seguro al
# MAGIC agente, sin importar quién elija las herramientas.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Qué evitó que el agente aplicara una segunda retención?</strong></summary>
# MAGIC
# MAGIC Leyó `agent_memory` antes de actuar, encontró "placed hold on CTA-100240" y se negó.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué parte de este laboratorio hizo el modelo?</strong></summary>
# MAGIC
# MAGIC Explicó la retención y redactó el rechazo. Las llamadas a las herramientas, leer el riesgo y retener la cuenta, son SQL que ejecuta el notebook.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué la retención escribe una fila en case_note además de cambiar el estado?</strong></summary>
# MAGIC
# MAGIC El estado es lo que usan los demás sistemas; la nota de caso registra por qué se aplicó la retención, para las personas y las auditorías.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusión
# MAGIC
# MAGIC En este laboratorio un agente leyó el riesgo de una cuenta, la congeló, registró por qué, recordó la
# MAGIC acción y se negó a repetirla. Puntos clave:
# MAGIC
# MAGIC 1. **Las herramientas de un agente son SQL** en tu rama: una consulta para leer el estado y un par de sentencias para cambiarlo.
# MAGIC 2. **Una acción debe dejar rastro:** el cambio de estado para los sistemas, la nota de caso para las personas.
# MAGIC 3. **La memoria hace idempotentes a los agentes:** revisa lo que ya hiciste antes de actuar.
# MAGIC 4. **El modelo explica; los datos deciden.** Ya sea el código o el modelo quien elija la herramienta, la base de datos tiene la verdad.
# MAGIC
# MAGIC El siguiente recorrido trata de resultados de IA que necesitan a una persona: el modelo extrae
# MAGIC hallazgos de notas de caso, y los dudosos van con un analista.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de agentes:** <a href="$../learning-loop/learning_loop_databricks_es">Revisión humana de los resultados de la IA →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
