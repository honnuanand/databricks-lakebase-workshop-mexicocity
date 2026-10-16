# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de agentes · Recorrido 3 de 5 · Revisión humana de los resultados de la IA</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Revisión humana de los resultados de la IA
# MAGIC #### Duración: unos 25 minutos
# MAGIC
# MAGIC *Recorrido 3 de 5. En Agentes que usan herramientas, el agente estaba seguro de sí mismo. Aquí el modelo dice qué tan seguro está, y las respuestas dudosas van con una persona.*
# MAGIC
# MAGIC ## Descripción general
# MAGIC
# MAGIC Los analistas de fraude y de PLD (prevención de lavado de dinero) escriben notas de caso con prisa:
# MAGIC texto libre, abreviaturas, ideas a medias. El equipo de investigaciones quiere datos estructurados
# MAGIC de cada nota (categoría, hallazgo, acción) para contar y enrutar casos. Un modelo puede extraerlos,
# MAGIC pero nadie va a confiar en él con las notas vagas, y nadie quiere volver a revisar las obvias.
# MAGIC
# MAGIC En este laboratorio un modelo lee cinco notas de caso y regresa una extracción con un puntaje de
# MAGIC confianza. Las notas claras se aceptan automáticamente; las dudosas se mandan a un analista, que
# MAGIC corrige una. Las notas, el resultado de la IA, el enrutamiento y la corrección viven en una sola
# MAGIC tabla en tu rama, y esa misma tabla responde después las preguntas de precisión.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio, vas a poder:
# MAGIC
# MAGIC 1. **Guardar el resultado de la IA junto a su origen**, escribiendo la extracción del modelo en la misma fila de la que salió.
# MAGIC 2. **Enrutar por confianza:** aceptar automáticamente las extracciones claras y mandar a revisión las dudosas.
# MAGIC 3. **Registrar una corrección humana** en la misma fila, con un estado que muestra que la cambió una persona.
# MAGIC 4. **Medir el ciclo con SQL** sobre la tabla operativa, sin una copia aparte para analítica.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Extracción:** convertir texto libre en campos. Aquí, `category`, `finding`, `action` y `confidence` a partir de cada `writeup`.
# MAGIC - **Umbral de confianza:** el puntaje a partir del cual una extracción se acepta sin revisión. Este laboratorio usa **0.75**.
# MAGIC - **Human in the loop (revisión humana):** una persona revisa lo que el modelo no tiene claro, y su corrección se guarda.
# MAGIC - **Estado:** `auto_accepted`, `needs_review` o `corrected`. Una sola columna convierte la tabla en una cola de revisión y en un registro de auditoría.
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
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. El paso de extracción llama al endpoint
# MAGIC     de Foundation Model <code>databricks-claude-opus-4-8</code> (barra lateral izquierda,
# MAGIC     <strong>Serving</strong>); si no está disponible, el notebook usa extracciones fijas. Este laboratorio
# MAGIC     <strong>reemplaza todas las notas de caso de tu rama</strong> (ver B).
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 170" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="150" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="50" width="120" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="90" y="74" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">nota de caso</text>
# MAGIC   <text x="90" y="93" text-anchor="middle" font-size="11" fill="#5A6F77">texto libre</text>
# MAGIC   <rect x="180" y="50" width="120" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="240" y="74" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">modelo</text>
# MAGIC   <text x="240" y="93" text-anchor="middle" font-size="11" fill="#5A6F77">campos + confianza</text>
# MAGIC   <rect x="340" y="25" width="150" height="46" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="415" y="53" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">auto_accepted</text>
# MAGIC   <rect x="340" y="88" width="150" height="46" rx="8" fill="#FFF3E0" stroke="#FF9800" stroke-width="2"/>
# MAGIC   <text x="415" y="116" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">needs_review</text>
# MAGIC   <rect x="530" y="88" width="160" height="46" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="610" y="110" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">corrected</text>
# MAGIC   <text x="610" y="126" text-anchor="middle" font-size="11" fill="#5A6F77">por un analista</text>
# MAGIC   <line x1="150" y1="78" x2="172" y2="78" stroke="#1B5162" stroke-width="2"/><polygon points="172,72 180,78 172,84" fill="#1B5162"/>
# MAGIC   <line x1="300" y1="70" x2="332" y2="52" stroke="#1B5162" stroke-width="2"/><polygon points="329,46 340,48 334,57" fill="#1B5162"/>
# MAGIC   <line x1="300" y1="86" x2="332" y2="106" stroke="#FF9800" stroke-width="2"/><polygon points="334,100 340,110 329,111" fill="#FF9800"/>
# MAGIC   <line x1="490" y1="111" x2="522" y2="111" stroke="#1B5162" stroke-width="2"/><polygon points="522,105 530,111 522,117" fill="#1B5162"/>
# MAGIC   <text x="316" y="40" text-anchor="middle" font-size="11" fill="#5A6F77">≥ 0.75</text>
# MAGIC   <text x="316" y="140" text-anchor="middle" font-size="11" fill="#5A6F77">&lt; 0.75</text>
# MAGIC   <text x="600" y="50" text-anchor="middle" font-size="11" fill="#5A6F77">todo en una fila de bank.case_note</text>
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
# MAGIC Esta celda carga el helper compartido de `common/scripts/` y fija el umbral de confianza en 0.75.
# MAGIC
# MAGIC - `connect()` abre una conexión de Postgres a tu rama. Por dentro, le pide a la API de Lakebase el
# MAGIC   nombre de host de la rama, obtiene un token de inicio de sesión de tu identidad de Databricks
# MAGIC   (válido por cerca de una hora) y se conecta con `psycopg`, un driver de Postgres para Python.
# MAGIC - `fm_call()` envía mensajes de chat al endpoint de Foundation Model por HTTPS, con tu sesión, y
# MAGIC   regresa el texto del modelo, o `None` si la llamada falla (entonces se usan las extracciones fijas).

# COMMAND ----------

import os, sys, json
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
CONF_THRESHOLD = 0.75
TABLE = "bank.case_note"

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
        print(f"  (API de FM no disponible: {e}; se usan las extracciones de respaldo)")
        return None

print("Ciclo de revisión: cargar -> extraer -> enrutar -> corregir -> analizar")
print(f"Endpoint de FM: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Ciclo de revisión: cargar -> extraer -> enrutar -> corregir -> analizar
# MAGIC Endpoint de FM: databricks-claude-opus-4-8
# MAGIC ```
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

# MAGIC %md-sandbox
# MAGIC ## B. Carga las notas de caso
# MAGIC
# MAGIC La celda agrega una columna `status` a `case_note` si todavía no existe (el esquema base no tiene
# MAGIC columna de enrutamiento; una app la agregaría igual) y luego reemplaza las filas de la tabla con cinco
# MAGIC notas de analistas: dos claras y tres no tanto. Las notas son datos del banco y se quedan en inglés.
# MAGIC La primera, como SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.case_note ADD COLUMN IF NOT EXISTS status TEXT;
# MAGIC DELETE FROM bank.case_note;
# MAGIC INSERT INTO bank.case_note (account_id, writeup)
# MAGIC VALUES ('CTA-100240', 'Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue.');
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">Esto borra todas las notas de caso de tu rama</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Se eliminan las cuatro notas de caso de la configuración y cualquier nota de retención de Agentes
# MAGIC     que usan herramientas. Solo se afecta tu rama. Búsqueda de texto completo y aproximada y Crear una app de Databricks
# MAGIC     sobre Lakebase (ruta de Desarrolladores de aplicaciones) buscan en esas notas: si las vas a hacer
# MAGIC     después, reconstruye tu rama al terminar con <code>branch.reset()</code>, como en la sección E2 de
# MAGIC     Restauración a un punto en el tiempo.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# Agrega la columna status si todavía no existe (idempotente).
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS status TEXT")

# Cuentas reales y las notas de caso de sus analistas.
writeups = [
    ("CTA-100240", "Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue."),
    ("CTA-300421", "Four outbound SPEI transfers in two days to a CLABE registered yesterday, each just under the reporting threshold. Possible structuring, referred to the PLD (AML) team."),
    ("CTA-200311", "Customer disputes a CoDi payment they say was charged twice at a Monterrey store; the merchant's receipt is ambiguous. Needs a closer look at the settlement records."),
    ("CTA-100235", "A few small USD charges followed by a larger one, same online merchant. Could be card testing, or the customer is traveling in the US. Hold for review."),
    ("CTA-100240", "Something looked off on the account this morning, maybe a login from another city? not sure, flagging it."),
]

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE}")
        for mid, writeup in writeups:
            cur.execute(f"INSERT INTO {TABLE} (account_id, writeup) VALUES (%s, %s)", [mid, writeup])

print(f"Se cargaron {len(writeups)} notas de caso de analistas")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Se cargaron 5 notas de caso de analistas`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Vuelve a leer las notas
# MAGIC
# MAGIC El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id, writeup FROM bank.case_note ORDER BY note_id;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT note_id, account_id, writeup FROM {TABLE} ORDER BY note_id")
        rows = cur.fetchall()

print(f"Notas de caso de analistas ({len(rows)} en total):")
for note_id, mid, writeup in rows:
    short = writeup[:70] + "..." if len(writeup) > 70 else writeup
    print(f"  {note_id} {mid}: {short}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** cinco notas. Los ids siguen después de las cuatro notas de la configuración
# MAGIC (y de la nota de retención, si hiciste antes Agentes que usan herramientas), y siguen contando en
# MAGIC cada nueva ejecución.
# MAGIC
# MAGIC ```
# MAGIC Notas de caso de analistas (5 en total):
# MAGIC   6 CTA-100240: Three card-not-present charges overnight to a foreign merchant the cus...
# MAGIC   7 CTA-300421: Four outbound SPEI transfers in two days to a CLABE registered yesterd...
# MAGIC   8 CTA-200311: Customer disputes a CoDi payment they say was charged twice at a Monte...
# MAGIC   9 CTA-100235: A few small USD charges followed by a larger one, same online merchant...
# MAGIC   10 CTA-100240: Something looked off on the account this morning, maybe a login from a...
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la entrada cruda son filas comunes. El resultado del modelo va a ir a las columnas vacías de esas mismas filas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Extrae y enruta por confianza
# MAGIC
# MAGIC Para cada nota, el modelo recibe una sola instrucción: regresar la categoría (fraud, AML, dispute u
# MAGIC other), el hallazgo como una etiqueta corta, la acción tomada y qué tan seguro está, en JSON. Las
# MAGIC etiquetas son datos y quedan en inglés. La celda escribe la extracción y un estado en la fila de la
# MAGIC nota: `auto_accepted` con 0.75 o más, `needs_review` por debajo. El SQL de cada nota:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.case_note
# MAGIC SET category = 'fraud', finding = 'card_compromise', action = 'froze_and_reissued',
# MAGIC     confidence = 0.90, status = 'auto_accepted'
# MAGIC WHERE note_id = 6;
# MAGIC ```
# MAGIC
# MAGIC El modelo pone su propia confianza, así que tus etiquetas y puntajes pueden variar un poco de una
# MAGIC ejecución a otra.

# COMMAND ----------

EXTRACT_PROMPT = (
    "You are a fraud/AML triage assistant. From a free-text analyst case note, "
    "extract category (fraud, AML, dispute, or other), finding (the specific issue, as a short "
    "snake_case label such as card_compromise or possible_structuring), "
    "action (what was done), and confidence (0-1, how certain you are the extraction "
    "is correct and unambiguous). "
    "Respond with ONLY a JSON object: {\"category\": \"...\", \"finding\": \"...\", "
    "\"action\": \"...\", \"confidence\": 0.X}"
)

# Respaldo, uno por nota de caso en orden de note_id, solo si falla la llamada al modelo. Imitan
# lo que el modelo regresa para notas así de claras y así de vagas: las de fraude con tarjeta y PLD
# no dejan dudas, las demás sí.
fallback = [
    {"category": "fraud",   "finding": "card_compromise",       "action": "froze_and_reissued", "confidence": 0.93},
    {"category": "AML",     "finding": "possible_structuring",  "action": "referred_to_aml",    "confidence": 0.88},
    {"category": "dispute", "finding": "double_charge_claim",   "action": "review_settlement",  "confidence": 0.64},
    {"category": "fraud",   "finding": "possible_card_testing", "action": "hold_for_review",    "confidence": 0.66},
    {"category": "fraud",   "finding": "unclear",               "action": "investigate",        "confidence": 0.28},
]

def extract(writeup, i):
    """Pide una extracción al modelo; interpreta su JSON, o usa el respaldo."""
    response = fm_call([{"role": "system", "content": EXTRACT_PROMPT},
                        {"role": "user", "content": writeup}])
    if response is None:
        return dict(fallback[i])
    try:
        e = json.loads(response[response.find("{"):response.rfind("}") + 1])
    except Exception:
        e = {"category": "?", "finding": "(parse failed)", "action": "?", "confidence": 0.3}
    e["confidence"] = max(0.0, min(1.0, float(e.get("confidence", 0.5))))
    return e

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT note_id, writeup FROM {TABLE} ORDER BY note_id")
        notes = cur.fetchall()

extractions = [extract(writeup, i) for i, (_, writeup) in enumerate(notes)]

with connect() as conn:
    with conn.cursor() as cur:
        for (note_id, _), e in zip(notes, extractions):
            status = "auto_accepted" if e["confidence"] >= CONF_THRESHOLD else "needs_review"
            e["status"] = status
            cur.execute(
                f"UPDATE {TABLE} SET category=%s, finding=%s, action=%s, confidence=%s, status=%s WHERE note_id=%s",
                [e["category"], e["finding"], e["action"], e["confidence"], status, note_id])

auto_count = sum(1 for e in extractions if e["status"] == "auto_accepted")
review_count = sum(1 for e in extractions if e["status"] == "needs_review")

print(f"Resultados de la extracción:")
print(f"  Aceptadas automáticamente (conf >= {CONF_THRESHOLD}): {auto_count}")
print(f"  Necesitan revisión        (conf <  {CONF_THRESHOLD}): {review_count}")

print(f"\nAceptadas automáticamente:")
for e in extractions:
    if e["status"] == "auto_accepted":
        print(f"  {e['category']}/{e['finding']}: conf={e['confidence']:.2f}")

print(f"\nNecesitan revisión:")
for e in extractions:
    if e["status"] == "needs_review":
        print(f"  {e['category']}/{e['finding']}: conf={e['confidence']:.2f}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** de una ejecución de prueba (las etiquetas y los puntajes cambian):
# MAGIC
# MAGIC ```
# MAGIC Resultados de la extracción:
# MAGIC   Aceptadas automáticamente (conf >= 0.75): 3
# MAGIC   Necesitan revisión        (conf <  0.75): 2
# MAGIC
# MAGIC Aceptadas automáticamente:
# MAGIC   fraud/card_compromise: conf=0.93
# MAGIC   AML/possible_structuring: conf=0.90
# MAGIC   dispute/possible_duplicate_charge: conf=0.78
# MAGIC
# MAGIC Necesitan revisión:
# MAGIC   fraud/possible_card_testing: conf=0.55
# MAGIC   other/possible_unauthorized_login: conf=0.30
# MAGIC ```
# MAGIC
# MAGIC En todas las ejecuciones de prueba, las notas de fraude con tarjeta y de estructuración sacaron 0.90 o
# MAGIC más, la aclaración de CoDi alrededor de 0.78, y la de cargos en USD y la nota vaga del inicio de
# MAGIC sesión 0.55 o menos.
# MAGIC
# MAGIC **Qué demuestra:** la confianza del modelo hace el triaje. Las notas claras no necesitan a nadie; las vagas quedan en fila para una persona.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(API de FM no disponible: 404 Client Error: Not Found for url: ...; se usan las extracciones de respaldo)</code>, una vez por nota: el nombre del endpoint está mal o no existe en este workspace. Se usan las extracciones fijas (2 aceptadas automáticamente, 3 en revisión). Para usar un modelo, corrige <code>FM_ENDPOINT</code> en A2.</li>
# MAGIC       <li>Una entrada como <code>?/(parse failed): conf=0.30</code>: el modelo no regresó un JSON válido para esa nota. Se manda a revisión, que es lo más seguro. Vuelve a ejecutar la celda para intentarlo otra vez.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Un analista corrige una nota dudosa
# MAGIC
# MAGIC El analista toma la nota `needs_review` con la confianza más baja, la lee y fija a mano la categoría y
# MAGIC el hallazgo. La corrección sobrescribe los campos de la IA en la misma fila y pone
# MAGIC `status = 'corrected'`. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.case_note
# MAGIC SET category = 'fraud', finding = 'account_takeover_suspected', status = 'corrected'
# MAGIC WHERE note_id = (SELECT note_id FROM bank.case_note WHERE status = 'needs_review'
# MAGIC                  ORDER BY confidence ASC NULLS FIRST LIMIT 1);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT note_id FROM {TABLE} WHERE status='needs_review' ORDER BY confidence ASC NULLS FIRST LIMIT 1")
        row = cur.fetchone()
        if row:
            note_id = row[0]
            cur.execute(
                f"UPDATE {TABLE} SET category=%s, finding=%s, status=%s WHERE note_id=%s",
                ["fraud", "account_takeover_suspected", "corrected", note_id])
            print(f"El analista corrigió note_id={note_id}: category=fraud, finding=account_takeover_suspected, status=corrected")
        else:
            print("No hay entradas needs_review que corregir")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `El analista corrigió note_id=10: category=fraud, finding=account_takeover_suspected, status=corrected`
# MAGIC (la nota vaga del inicio de sesión; tu id puede ser otro).
# MAGIC
# MAGIC **Qué demuestra:** la decisión de la persona se guarda donde estaba la de la IA, con un estado que dice que la tomó una persona. La confianza del modelo se queda en la fila, así que puedes ver en qué tenía dudas.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, selecciona tu proyecto y tu rama, luego la pestaña
# MAGIC     <strong>Tables</strong>, y abre <code>case_note</code>. Cada fila muestra la nota, la extracción, la
# MAGIC     confianza y su estado.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Mide el ciclo
# MAGIC
# MAGIC La misma tabla responde lo que pregunta un líder de equipo: cuántas notas se aceptaron, se revisaron o
# MAGIC se corrigieron, y qué tan seguro estaba el modelo en cada grupo. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT status, COUNT(*) FROM bank.case_note WHERE status IS NOT NULL GROUP BY status;
# MAGIC SELECT AVG(confidence) FROM bank.case_note WHERE status = 'auto_accepted';
# MAGIC SELECT AVG(confidence) FROM bank.case_note WHERE status = 'needs_review';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status, COUNT(*) FROM {TABLE} WHERE status IS NOT NULL GROUP BY status")
        by_status = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute(f"SELECT AVG(confidence) FROM {TABLE} WHERE status='auto_accepted'")
        avg_auto = cur.fetchone()[0]
        cur.execute(f"SELECT AVG(confidence) FROM {TABLE} WHERE status='needs_review'")
        avg_review = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE status IS NOT NULL")
        total = cur.fetchone()[0]

print("=== Analítica del ciclo de revisión ===")
print(f"\nProcesadas: {total}")
print(f"  Aceptadas automáticamente: {by_status.get('auto_accepted', 0)}")
print(f"  Necesitan revisión:        {by_status.get('needs_review', 0)}")
print(f"  Corregidas:                {by_status.get('corrected', 0)}")
if avg_auto is not None:
    print(f"\nConfianza promedio (aceptadas automáticamente): {float(avg_auto):.3f}")
if avg_review is not None:
    print(f"Confianza promedio (necesitan revisión):        {float(avg_review):.3f}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** de la misma ejecución de prueba:
# MAGIC
# MAGIC ```
# MAGIC === Analítica del ciclo de revisión ===
# MAGIC
# MAGIC Procesadas: 5
# MAGIC   Aceptadas automáticamente: 3
# MAGIC   Necesitan revisión:        1
# MAGIC   Corregidas:                1
# MAGIC
# MAGIC Confianza promedio (aceptadas automáticamente): 0.870
# MAGIC Confianza promedio (necesitan revisión):        0.550
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** la tabla operativa también es la fuente de la analítica. Sin exportar nada, sin un segundo almacén.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cómo elegir el umbral y vigilar el drift</strong></summary>
# MAGIC
# MAGIC El umbral cambia tiempo de los analistas por riesgo. Si lo subes, más notas van a revisión; si lo
# MAGIC bajas, más se aceptan tal cual. Elígelo con datos: mide qué tan seguido los analistas cambian una
# MAGIC extracción en cada nivel de confianza, y pon el umbral donde las correcciones se vuelven raras.
# MAGIC
# MAGIC Las mismas consultas, agrupadas por semana, muestran el drift (deriva): si sube la proporción de notas
# MAGIC `needs_review` o `corrected`, cambiaron las notas o cambió el modelo, y toca revisar. Como las
# MAGIC correcciones se guardan junto a las notas originales, también son un conjunto de evaluación listo
# MAGIC para el siguiente modelo.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Por qué la nota vaga del inicio de sesión fue a revisión, y la de estructuración no?</strong></summary>
# MAGIC
# MAGIC El modelo le dio una confianza baja (menos de 0.75), así que la regla de enrutamiento la mandó con una persona. La nota de estructuración era clara y sacó cerca de 0.90.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Dónde se guarda la corrección del analista?</strong></summary>
# MAGIC
# MAGIC En la misma fila de `case_note` que la nota y la extracción de la IA, con `status = 'corrected'`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué tus conteos pueden ser distintos al resultado esperado?</strong></summary>
# MAGIC
# MAGIC El modelo pone su propia confianza en cada ejecución. Una nota cerca de 0.75, como la aclaración de CoDi, puede caer de cualquier lado.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusión
# MAGIC
# MAGIC En este laboratorio un modelo extrajo hallazgos estructurados de cinco notas de caso, las seguras se
# MAGIC aceptaron, las dudosas quedaron en fila y un analista corrigió una, todo en una sola tabla. Puntos
# MAGIC clave:
# MAGIC
# MAGIC 1. **Guarda el resultado de la IA junto a su origen:** la nota, la extracción y la confianza en una fila.
# MAGIC 2. **Enruta por confianza** para que las personas solo revisen lo que el modelo no tiene claro.
# MAGIC 3. **Guarda las correcciones donde escribió la IA,** con un estado, para distinguir siempre entre máquina y persona.
# MAGIC 4. **Mide con SQL sobre la misma tabla:** precisión y drift sin mover datos.
# MAGIC
# MAGIC El siguiente recorrido encuentra elementos parecidos por su significado: búsqueda por similitud de
# MAGIC vectores con `pgvector`, junto a los mismos datos del banco.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de agentes:** <a href="$../pg-vector/pg_vector_databricks_es">Búsqueda por similitud de vectores →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
