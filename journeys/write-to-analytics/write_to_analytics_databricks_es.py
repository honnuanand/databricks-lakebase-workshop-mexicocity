# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 1 · Recorrido 3 de 5 · Datos de Lakebase en el Lakehouse</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Datos de Lakebase en el Lakehouse
# MAGIC #### Duración: unos 20 minutos
# MAGIC
# MAGIC *Recorrido 3 de 5. Los dos primeros recorridos cambiaron tu rama con Postgres. Este ve las mismas filas desde el lado analítico.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC De madrugada, la cuenta `CTA-100240` envía MXN 38,500 por SPEI a un beneficiario al que nunca le había
# MAGIC pagado, y la utilización de su crédito ya está muy alta. El proceso de autorización tiene milisegundos
# MAGIC para decidir, mientras la analítica del equipo de fraude corre en el lakehouse. En la arquitectura
# MAGIC habitual, las transacciones se copian a un almacén analítico cada cierto tiempo, así que el puntaje de
# MAGIC fraude que ve el lado operativo siempre está un poco desactualizado.
# MAGIC
# MAGIC Con Lakebase, las filas operativas y la analítica trabajan sobre la misma copia. En este laboratorio
# MAGIC registras la transacción con Postgres, calculas a partir de ella un puntaje de fraude y lo escribes en
# MAGIC la misma fila. Después ves cómo el lakehouse lee esas filas a través de Unity Catalog, sin pipelines.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Escribir una fila operativa** con Postgres, como lo hace una aplicación.
# MAGIC 2. **Calcular un valor analítico** a partir de esa fila y guardarlo en la misma fila.
# MAGIC 3. **Leer el puntaje** a velocidad operativa, sin ninguna copia de por medio.
# MAGIC 4. **Explicar cómo el lakehouse lee las tablas de Lakebase** a través de un catálogo de Unity Catalog.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Trabajo operativo vs. analítico:** el trabajo operativo (OLTP) son muchas lecturas y escrituras pequeñas y rápidas, como registrar una transacción. El trabajo analítico recorre muchas filas para encontrar patrones, como calcular el riesgo de fraude de todas las transacciones.
# MAGIC - **Lakehouse:** la plataforma analítica de Databricks: tablas en almacenamiento en la nube, consultadas con SQL warehouses y Spark.
# MAGIC - **Unity Catalog:** la capa de gobierno de datos de Databricks: un solo lugar para nombrar, proteger y auditar los datos en toda la plataforma. Las tablas se nombran `catálogo.esquema.tabla`.
# MAGIC - **Foreign catalog (catálogo externo):** un catálogo de Unity Catalog cuyas tablas viven en otra base de datos, aquí Lakebase. Las consultas leen los datos donde están; no se copia nada.
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
# MAGIC     Si acabas de hacer Restauración a un punto en el tiempo, asegúrate de haber ejecutado su celda de reinicio.
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
# MAGIC ### A2. Carga el módulo de ayuda
# MAGIC
# MAGIC Esta celda carga `run_sql()` de `common/scripts/`. Abre una conexión a tu rama, ejecuta una sentencia
# MAGIC SQL y devuelve las filas, si hay.
# MAGIC
# MAGIC Por dentro, `run_sql()` le pide a la API de Lakebase el nombre de host de tu rama, obtiene un token de
# MAGIC inicio de sesión con tu identidad de Databricks (válido por cerca de una hora) y abre una conexión
# MAGIC estándar de Postgres con `psycopg`, un driver de Postgres para Python.
# MAGIC
# MAGIC En los pasos siguientes, el bloque de SQL de cada paso es la sentencia que se ejecuta en tu rama. La
# MAGIC celda de Python de abajo solo envía esa sentencia e imprime el resultado.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql
print("listo")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `listo`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Registra una transacción con Postgres
# MAGIC
# MAGIC Primero agrega una columna para guardar el puntaje y después registra la nueva transacción de
# MAGIC `CTA-100240`: MXN 38,500 por SPEI (por eso no tiene código de categoría de comercio), puntaje de
# MAGIC anomalía de 8.7 sobre 10 y la cuenta al 92% de utilización. Es una escritura operativa normal, de las
# MAGIC que una aplicación hace todo el día:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1);
# MAGIC INSERT INTO bank.txn (account_id, ts, amount, channel, anomaly_score, mcc, util_pct)
# MAGIC VALUES ('CTA-100240', now(), 38500.00, 'SPEI', 8.7, NULL, 92.0) RETURNING txn_id;
# MAGIC ```

# COMMAND ----------

run_sql("ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1)")
r = run_sql("""INSERT INTO bank.txn
  (account_id, ts, amount, channel, anomaly_score, mcc, util_pct)
  VALUES ('CTA-100240', now(), 38500.00, 'SPEI', 8.7, NULL, 92.0)
  RETURNING txn_id, amount, anomaly_score""")
rid = r[0][0]
print("txn_id insertado", r[0])

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `txn_id insertado (6, Decimal('38500.00'), Decimal('8.70'))`. El primer número es
# MAGIC el `txn_id` de la fila nueva: 6 en una rama recién cargada, y uno más cada vez que ejecutas la celda.
# MAGIC
# MAGIC **Qué demuestra:** la transacción es una fila normal de Postgres, escrita como la escribiría cualquier aplicación.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego A2 y esta.</li>
# MAGIC       <li><code>relation "bank.txn" does not exist</code>: el banco no está cargado en esta rama. Ejecuta <code>00-setup/setup_databricks_es</code> y regresa.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Calcula el puntaje y escríbelo en la fila
# MAGIC
# MAGIC Calcula un puntaje de fraude a partir de la fila y guárdalo en la misma fila. En un sistema real, el
# MAGIC puntaje vendría de un modelo; aquí es una fórmula sencilla para que puedas comprobar el número a mano.
# MAGIC Suma dos partes, cada una de hasta 100: el puntaje de anomalía (sobre 10) y la utilización (sobre 100).
# MAGIC El total va de 0 a 200.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.txn
# MAGIC SET fraud_risk = ROUND(100 * (anomaly_score / 10.0 + util_pct / 100.0), 1)
# MAGIC WHERE txn_id = <rid>;
# MAGIC ```

# COMMAND ----------

run_sql(f"UPDATE bank.txn SET fraud_risk = "
        f"ROUND(100*(anomaly_score/10.0 + util_pct/100.0),1) WHERE txn_id={rid}")
row = run_sql(f"SELECT txn_id, account_id, amount, anomaly_score, util_pct, fraud_risk "
              f"FROM bank.txn WHERE txn_id={rid}")[0]
print("puntaje calculado y escrito:", row)

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:**
# MAGIC `puntaje calculado y escrito: (6, 'CTA-100240', Decimal('38500.00'), Decimal('8.70'), Decimal('92.00'), Decimal('179.0'))`
# MAGIC
# MAGIC El puntaje es `ROUND(100 × (8.7 / 10 + 92 / 100), 1)` = `ROUND(100 × 1.79, 1)` = **179.0** de 200,
# MAGIC cerca del máximo. Queda guardado en la fila que escribiste en B, así que el proceso de autorización
# MAGIC puede leerlo en su siguiente consulta.
# MAGIC
# MAGIC **Qué demuestra:** el valor analítico vive en la fila operativa. Nada copió la transacción a otro lugar para calcular el puntaje, y nada tiene que copiar el puntaje de regreso.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## D. Lee las mismas filas desde el lakehouse
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Explicación: este paso no se ejecuta en este notebook</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Para leer Lakebase desde un SQL warehouse, la base de datos tiene que estar registrada como catálogo
# MAGIC     en Unity Catalog, y para eso se necesita permiso para crear catálogos. Las cuentas del taller
# MAGIC     normalmente no lo tienen, así que esta sección muestra los pasos y la consulta en lugar de inventar
# MAGIC     el resultado. Todo lo de B y C se ejecutó de verdad en tu rama.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC **1. Registra la base de datos** (una vez, alguien con permiso para crear catálogos): en
# MAGIC **Catalog Explorer**, elige **Create catalog**, selecciona el tipo **Lakebase Postgres** y elige el
# MAGIC proyecto, la rama y la base de datos `databricks_postgres`. Unity Catalog muestra entonces los esquemas
# MAGIC y las tablas de la base de datos, incluida `bank.txn`.
# MAGIC
# MAGIC **2. Consúltala desde un SQL warehouse:**
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, ts, amount, anomaly_score, fraud_risk
# MAGIC FROM <tu_catalogo>.bank.txn
# MAGIC WHERE account_id = 'CTA-100240'
# MAGIC ORDER BY ts DESC
# MAGIC LIMIT 1;
# MAGIC ```
# MAGIC
# MAGIC **Lo que esperarías ver:** la transacción que escribiste en B, con el puntaje de 179.0 de C, porque el
# MAGIC catálogo lee la tabla de Lakebase donde está. Esta consulta no se ejecutó en el workspace del taller,
# MAGIC por el permiso que se menciona arriba.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Cómo lee el lakehouse los datos de Lakebase sin copiarlos</strong></summary>
# MAGIC
# MAGIC El catálogo registrado es un **foreign catalog**: Unity Catalog conoce los esquemas y las tablas de la
# MAGIC base de datos, pero los datos se quedan en Lakebase. Cuando lo consultas, Databricks le envía a
# MAGIC Lakebase las partes de la consulta que Postgres puede ejecutar, como filtros y agregaciones, y recibe
# MAGIC solo los resultados.
# MAGIC
# MAGIC Por eso no hay retraso que esperar: no se copia nada. La contraparte es que la velocidad de la consulta
# MAGIC depende del cómputo de Lakebase. Para analítica grande y repetida, una copia en el lakehouse puede
# MAGIC seguir siendo la mejor opción; para datos operativos recientes, leerlos directamente evita por completo
# MAGIC un pipeline.
# MAGIC
# MAGIC El acceso al catálogo se gobierna con Unity Catalog como cualquier otro catálogo: permisos, linaje y
# MAGIC registros de auditoría.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Dónde se guarda el puntaje de fraude?</strong></summary>
# MAGIC
# MAGIC En la misma fila de `txn` que la transacción, en la columna `fraud_risk`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué necesita el lakehouse para poder consultar estas filas?</strong></summary>
# MAGIC
# MAGIC Que la base de datos de Lakebase esté registrada como catálogo en Unity Catalog. Después, un SQL warehouse o Spark pueden consultar `<catálogo>.bank.txn`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué importa evitar una copia para el puntaje de fraude?</strong></summary>
# MAGIC
# MAGIC Un puntaje copiado solo está tan actualizado como la última copia. Con una sola copia, el proceso operativo siempre lee el puntaje más reciente.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio registraste una transacción con Postgres, calculaste su puntaje, lo escribiste en
# MAGIC la misma fila y viste cómo la lee el lakehouse. Puntos clave:
# MAGIC
# MAGIC 1. **Una sola copia sirve a los dos lados:** la escritura operativa y el puntaje analítico viven en la
# MAGIC    misma fila.
# MAGIC 2. **Sin pipeline de por medio:** nada copia la transacción a un almacén analítico y de regreso.
# MAGIC 3. **El proceso operativo lee el puntaje a la velocidad de la base de datos,** en su siguiente consulta.
# MAGIC 4. **El lakehouse puede leer las mismas tablas** cuando la base de datos está registrada en Unity Catalog
# MAGIC    como foreign catalog, gobernado como cualquier otro catálogo.
# MAGIC
# MAGIC El siguiente recorrido trata del costo: cuánto cuesta esta base de datos cuando nadie la usa.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la Parte 1:** <a href="$../scale-to-zero/scale_to_zero_databricks_es">Escalar a cero →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
