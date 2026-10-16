# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de agentes · Recorrido 5 de 5 · Servir features en línea</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Servir features en línea
# MAGIC #### Duración: unos 10 minutos
# MAGIC
# MAGIC *Recorrido 5 de 5. Búsqueda por similitud de vectores encontró elementos relacionados por su significado. Este último recorrido sirve los números que necesita un modelo de fraude, en el momento en que los necesita.*
# MAGIC
# MAGIC ## Descripción general
# MAGIC
# MAGIC Cuando llega un pago con tarjeta o una transferencia SPEI, un modelo de fraude tiene unos cuantos
# MAGIC milisegundos para calificarla. No puede sumar en ese momento el último mes de actividad de la cuenta.
# MAGIC Necesita las **features** (variables del modelo) de esa cuenta: cuántas transacciones lleva este mes,
# MAGIC cuántas aclaraciones, su puntaje de anomalía promedio, ya calculadas y listas para leer.
# MAGIC
# MAGIC En este laboratorio lo construyes en dos pasos en tu rama. Primero, el paso offline: agregar 10,000
# MAGIC eventos crudos en una fila de features por cuenta. Luego, el paso en línea: buscar la fila de una
# MAGIC cuenta por su llave, 100 veces, y medir cada búsqueda.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio, vas a poder:
# MAGIC
# MAGIC 1. **Generar un flujo de eventos crudos** con SQL, como sustituto del historial de transacciones de una cuenta.
# MAGIC 2. **Materializar features:** agregar los eventos en una tabla con una fila por cuenta.
# MAGIC 3. **Servir features en línea** con una búsqueda por llave primaria, y medir su latencia.
# MAGIC 4. **Explicar la división:** calcular las features por adelantado (offline) y leerlas al momento de decidir (en línea).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Feature (variable del modelo):** un número que usa un modelo para tomar una decisión, como `disputes_this_month` de una cuenta.
# MAGIC - **Materializar:** calcular las features por adelantado y guardarlas en una tabla, en vez de calcularlas en cada solicitud.
# MAGIC - **Servir en línea:** leer una fila de features al momento de decidir, por su llave, lo bastante rápido para caber dentro de la autorización de un pago.
# MAGIC - **Frescura:** qué tan recientes son las features. La columna `computed_at` registra cuándo se calculó cada fila.
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
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>. No necesitas un endpoint de modelo. El
# MAGIC     laboratorio crea dos tablas propias en tu rama, <code>account_events_for_features</code> y
# MAGIC     <code>account_features_online</code>, y las reemplaza en cada ejecución; las tablas del banco no se tocan.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 150" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="130" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="45" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">account_events_for_features</text>
# MAGIC   <text x="125" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">10,000 eventos crudos</text>
# MAGIC   <rect x="290" y="45" width="190" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="385" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">account_features_online</text>
# MAGIC   <text x="385" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">1 fila por cuenta</text>
# MAGIC   <rect x="550" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="620" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">modelo de fraude</text>
# MAGIC   <text x="620" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">búsqueda por llave</text>
# MAGIC   <line x1="220" y1="73" x2="282" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="282,67 290,73 282,79" fill="#1B5162"/>
# MAGIC   <line x1="480" y1="73" x2="542" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="542,67 550,73 542,79" fill="#1B5162"/>
# MAGIC   <text x="255" y="122" text-anchor="middle" font-size="11" fill="#5A6F77">offline: agregar</text>
# MAGIC   <text x="515" y="122" text-anchor="middle" font-size="11" fill="#5A6F77">en línea: milisegundos</text>
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
# MAGIC ### A2. Conéctate a tu rama
# MAGIC
# MAGIC Esto carga el helper compartido de `common/scripts/` y nombra las dos tablas. `connect()` le pide a la
# MAGIC API de Lakebase el nombre de host de tu rama, obtiene un token de inicio de sesión de tu identidad de
# MAGIC Databricks (válido por cerca de una hora) y abre una conexión de Postgres con `psycopg`, un driver de
# MAGIC Postgres para Python.
# MAGIC
# MAGIC En los pasos siguientes, el bloque SQL de cada paso es lo que se ejecuta en tu rama.

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

SCHEMA = _env('LB_SCHEMA', 'bank')
EVENTS_TABLE = 'account_events_for_features'
ONLINE_TABLE = 'account_features_online'

print('Listo.')

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Listo.`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Construye los eventos crudos
# MAGIC
# MAGIC ### B1. Crea la tabla de eventos
# MAGIC
# MAGIC Una fila por evento: qué cuenta, cuándo, de qué tipo, por cuánto, y los puntajes que registraría un
# MAGIC sistema de fraude. La celda borra la tabla primero, para que cada ejecución empiece limpia. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE bank.account_events_for_features (
# MAGIC     event_id      BIGSERIAL PRIMARY KEY,
# MAGIC     account_id    TEXT NOT NULL,
# MAGIC     event_ts      TIMESTAMPTZ DEFAULT now(),
# MAGIC     event_type    TEXT,
# MAGIC     amount        NUMERIC(12,2),
# MAGIC     anomaly_score NUMERIC(6,2),
# MAGIC     util_pct      NUMERIC(6,2)
# MAGIC );
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{EVENTS_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{EVENTS_TABLE} (
                event_id BIGSERIAL PRIMARY KEY,
                account_id TEXT NOT NULL,
                event_ts TIMESTAMPTZ DEFAULT now(),
                event_type TEXT,
                amount NUMERIC(12,2),
                anomaly_score NUMERIC(6,2),
                util_pct NUMERIC(6,2)
            )
        """)
        print(f'✓ Se creó la tabla de eventos crudos')

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `✓ Se creó la tabla de eventos crudos`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Genera 10,000 eventos
# MAGIC
# MAGIC `generate_series` crea 10,000 eventos sintéticos de 100 cuentas, de `CTA-900000` a `CTA-900099`
# MAGIC (separadas de las cuentas reales del banco), repartidos en los últimos 100 días, con una mezcla de
# MAGIC compras, transferencias, aclaraciones y contracargos. El SQL, abreviado:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.account_events_for_features (account_id, event_ts, event_type, amount, anomaly_score, util_pct)
# MAGIC SELECT 'CTA-' || (900000 + g % 100),
# MAGIC        now() - ((g / 100) || ' days')::interval,
# MAGIC        (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + ((g / 100) % 4)],
# MAGIC        ...
# MAGIC FROM generate_series(1, 10000) g;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{EVENTS_TABLE}(account_id, event_ts, event_type, amount, anomaly_score, util_pct)
            SELECT
                'CTA-' || (900000 + g % 100),
                now() - ((g / 100) || ' days')::interval,
                (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + ((g / 100) % 4)],
                (g % 5000) + (g % 100)::numeric / 100,
                ((g / 100) % 10)::numeric + (g % 100)::numeric / 100,
                30 + (g % 70)::numeric
            FROM generate_series(1, 10000) g
        """)
        print(f'✓ Se cargaron 10k eventos de 100 cuentas')

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `✓ Se cargaron 10k eventos de 100 cuentas`
# MAGIC
# MAGIC **Qué demuestra:** un historial de transacciones es una tabla como cualquier otra. Lakebase guarda los eventos crudos junto a los datos del banco.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Materializa las features (offline)
# MAGIC
# MAGIC ### C1. Crea la tabla de features
# MAGIC
# MAGIC Una fila por cuenta, con `account_id` como llave. La llave primaria le da a Postgres un índice, que es
# MAGIC lo que hace rápidas las búsquedas de D. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE bank.account_features_online (
# MAGIC     account_id          TEXT PRIMARY KEY,
# MAGIC     txns_this_month     INT,
# MAGIC     disputes_this_month INT,
# MAGIC     avg_anomaly_score   NUMERIC(8,2),
# MAGIC     avg_util_pct        NUMERIC(8,2),
# MAGIC     total_amount        NUMERIC(12,2),
# MAGIC     computed_at         TIMESTAMPTZ
# MAGIC );
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{ONLINE_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{ONLINE_TABLE} (
                account_id TEXT PRIMARY KEY,
                txns_this_month INT,
                disputes_this_month INT,
                avg_anomaly_score NUMERIC(8,2),
                avg_util_pct NUMERIC(8,2),
                total_amount NUMERIC(12,2),
                computed_at TIMESTAMPTZ
            )
        """)
        print(f'✓ Se creó la tabla de features en línea')

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `✓ Se creó la tabla de features en línea`

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Calcula las features
# MAGIC
# MAGIC Agrega los eventos de los últimos 30 días en una fila por cuenta. Cerca del 31% de los eventos cae en
# MAGIC esa ventana, unos 30 por cuenta. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.account_features_online
# MAGIC SELECT e.account_id,
# MAGIC        COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
# MAGIC        COUNT(CASE WHEN e.event_type = 'dispute'  THEN 1 END),
# MAGIC        AVG(e.anomaly_score), AVG(e.util_pct), SUM(e.amount), now()
# MAGIC FROM bank.account_events_for_features e
# MAGIC WHERE e.event_ts >= now() - interval '30 days'
# MAGIC GROUP BY e.account_id;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{ONLINE_TABLE}
            SELECT
                e.account_id,
                COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
                COUNT(CASE WHEN e.event_type = 'dispute' THEN 1 END),
                AVG(e.anomaly_score),
                AVG(e.util_pct),
                SUM(e.amount),
                now()
            FROM {SCHEMA}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.account_id
        """)
        print(f'✓ Se materializaron las features a partir de los eventos (paso offline)')

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `✓ Se materializaron las features a partir de los eventos (paso offline)`
# MAGIC
# MAGIC **Qué demuestra:** el trabajo pesado, recorrer y agregar eventos, se hace una vez y por adelantado. En una ejecución de prueba, cada cuenta tuvo unas 7 compras y 7 aclaraciones en la ventana.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, selecciona tu proyecto y tu rama, luego la pestaña
# MAGIC     <strong>Tables</strong>, y abre <code>account_features_online</code>: 100 filas, una por cuenta, cada
# MAGIC     una con su hora de <code>computed_at</code>.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Sirve las features (en línea)
# MAGIC
# MAGIC Busca cada una de las 100 cuentas por su llave, una consulta a la vez, y mide cada búsqueda. Esta es
# MAGIC la consulta que ejecutaría un modelo de fraude al momento de autorizar:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account_features_online WHERE account_id = 'CTA-900000';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        latencies = []
        for account_id in range(100):
            t0 = time.perf_counter()
            cur.execute(f"SELECT * FROM {SCHEMA}.{ONLINE_TABLE} WHERE account_id = %s", [f'CTA-{900000 + account_id}'])
            row = cur.fetchone()
            latencies.append((time.perf_counter() - t0) * 1000)

        if latencies:
            avg_ms = sum(latencies) / len(latencies)
            min_ms = min(latencies)
            max_ms = max(latencies)
            print(f'✓ Se midieron {len(latencies)} búsquedas:')
            print(f'  Promedio: {avg_ms:.2f} ms')
            print(f'  Mínimo:   {min_ms:.2f} ms')
            print(f'  Máximo:   {max_ms:.2f} ms')
            print(f'  Resultado: latencia de un solo dígito en milisegundos, lista para calificar fraude')

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** de una ejecución de prueba (tus números van a variar):
# MAGIC
# MAGIC ```
# MAGIC ✓ Se midieron 100 búsquedas:
# MAGIC   Promedio: 1.74 ms
# MAGIC   Mínimo:   1.54 ms
# MAGIC   Máximo:   4.08 ms
# MAGIC   Resultado: latencia de un solo dígito en milisegundos, lista para calificar fraude
# MAGIC ```
# MAGIC
# MAGIC Otras ejecuciones promediaron entre 1.59 y 5.63 ms. Una búsqueda lenta de vez en cuando (hasta unos 20 ms) es normal.
# MAGIC
# MAGIC **Qué demuestra:** leer las features de una cuenta por su llave toma unos cuantos milisegundos desde un notebook en el workspace, lo bastante rápido para caber dentro de la decisión de un pago.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Latencia mucho más alta</strong> (decenas de milisegundos en promedio): puede que el cómputo de tu rama acabe de despertar (ver Escalar a cero). Vuelve a ejecutar la celda. Desde una laptop, espera unos 100 ms por búsqueda: es el viaje de ida y vuelta por la red, no la base de datos.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>De dónde salen las features en un sistema real</strong></summary>
# MAGIC
# MAGIC Aquí los dos pasos se ejecutan en Lakebase para que los veas lado a lado. En un sistema completo, el
# MAGIC paso offline suele ejecutarse en el lakehouse, sobre todo el historial de transacciones, de forma
# MAGIC programada; esos mismos datos entrenan el modelo. Luego las filas de features más recientes se
# MAGIC sincronizan a Lakebase para servirlas, y `computed_at` le dice al modelo qué tan frescas son. Datos de
# MAGIC Lakebase en el Lakehouse, en la Parte 1, muestra la conexión entre los dos lados.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Por qué no calcular las features en el momento en que llega un pago?</strong></summary>
# MAGIC
# MAGIC Eso significa recorrer los eventos recientes de la cuenta en cada solicitud. Materializar hace ese trabajo una vez, así que el pago solo necesita una fila.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué hace rápida la búsqueda?</strong></summary>
# MAGIC
# MAGIC `account_id` es la llave primaria, así que Postgres encuentra la fila con un índice, sin recorrer la tabla.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Qué le dice computed_at al modelo?</strong></summary>
# MAGIC
# MAGIC Cuándo se calcularon las features de la fila, para que sepa qué tan frescas son.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio agregaste 10,000 eventos en una fila de features por cuenta y luego serviste esas
# MAGIC filas por llave en unos cuantos milisegundos. Puntos clave:
# MAGIC
# MAGIC 1. **Calcula antes, lee rápido:** materializa las features offline y sírvelas en línea por llave.
# MAGIC 2. **Una llave primaria es todo el índice que necesitas** para búsquedas de una sola fila.
# MAGIC 3. **Aquí Lakebase tiene los dos lados,** los eventos crudos y las features servidas, en una sola base de datos.
# MAGIC 4. **La frescura también es un dato:** guarda cuándo se calculó cada fila de features.
# MAGIC
# MAGIC Con esto termina la ruta de Desarrolladores de agentes: memoria, herramientas, revisión humana,
# MAGIC búsqueda por similitud y servicio de features, todo en una sola rama de Postgres.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Terminaste la ruta de Desarrolladores de agentes.**
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
