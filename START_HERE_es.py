# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Comienza aquí</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Comienza aquí
# MAGIC
# MAGIC Ejecuta una vez el notebook de configuración y después avanza por la Parte 1 y la Parte 2, la ruta de
# MAGIC Desarrolladores de aplicaciones. Cada notebook termina con un enlace al siguiente y otro para volver a
# MAGIC esta página.
# MAGIC
# MAGIC *English version:* <a href="$./START_HERE">Start Here</a>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Cómo funcionan los notebooks</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Conecta cada notebook a cómputo <strong>serverless</strong> y ejecútalo de arriba abajo, una celda a
# MAGIC     la vez. Cada recorrido se ejecuta en tu propia rama, dentro de tu propio proyecto de Lakebase, así que
# MAGIC     nada de lo que hagas afecta a nadie más. Todos empiezan con las mismas tres celdas de configuración y muestran
# MAGIC     el resultado esperado debajo de cada celda.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## Antes de empezar
# MAGIC
# MAGIC <a href="$./00-setup/setup_databricks_es">Configuración: crea tu proyecto y tu rama</a>: crea tu propio
# MAGIC proyecto de Lakebase, carga en él la base de datos del banco, crea tu rama y comprueba la conexión.
# MAGIC Ejecútalo una vez, de arriba abajo.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parte 1. Capacidades principales de Lakebase
# MAGIC
# MAGIC **Unos 60 minutos.** Lo que hace a Lakebase diferente de una base de datos Postgres tradicional.
# MAGIC
# MAGIC | # | Recorrido | Qué vas a hacer |
# MAGIC | - | --------- | --------------- |
# MAGIC | 1 | <a href="$./journeys/branch-the-brain/branch_the_brain_databricks_es">Ramas de base de datos</a> | Bifurca toda la base de datos del banco en segundos, congela una cuenta en el fork y después descártalo sin tocar tu rama. |
# MAGIC | 2 | <a href="$./journeys/break-and-rewind/break_and_rewind_databricks_es">Restauración a un punto en el tiempo</a> | Borra a propósito operaciones y liquidaciones, y recupéralas del momento anterior al error. Sin trabajos de respaldo. |
# MAGIC | 3 | <a href="$./journeys/write-to-analytics/write_to_analytics_databricks_es">Datos de Lakebase en el Lakehouse</a> | Registra una transferencia SPEI con Postgres, calcula un puntaje de fraude, escríbelo en la misma fila y ve la consulta con la que el lakehouse la lee. |
# MAGIC | 4 | <a href="$./journeys/scale-to-zero/scale_to_zero_databricks_es">Escalar a cero</a> | El cómputo inactivo se suspende solo y no cuesta nada; la siguiente consulta lo despierta. |
# MAGIC | 5 | <a href="$./journeys/pg-integration/pg_integration_databricks_es">Conectar herramientas de Postgres</a> | Ejecuta las consultas con las que cualquier herramienta de Postgres o de BI descubre el esquema del banco. |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parte 2. Desarrolladores de aplicaciones
# MAGIC
# MAGIC **Unas 2 horas.** Llega hasta una app de Databricks sobre Lakebase que usa todo lo de esta ruta.
# MAGIC
# MAGIC | # | Recorrido | Tiempo | Qué vas a hacer |
# MAGIC | - | --------- | ------ | --------------- |
# MAGIC | 1 | <a href="$./journeys/pg-json/pg_json_databricks_es">Datos JSON con JSONB</a> | 20 min | Guarda fichas técnicas variables de instrumentos y fondos como JSONB, consúltalas con SQL e indéxalas con GIN. |
# MAGIC | 2 | <a href="$./journeys/lakebase-search/lakebase_search_databricks_es">Lakebase Search</a> | 35 min | Busca en 40 notas de fraude y PLD por palabras (BM25), por significado (embeddings reales) y de las dos formas a la vez (búsqueda híbrida), con filtros y joins sobre las cuentas. Necesita Lakebase Search activado en tu proyecto (el recorrido explica cómo) y el endpoint de embeddings `databricks-gte-large-en`. |
# MAGIC | 3 | <a href="$./journeys/data-api/data_api_databricks_es">API de datos de Lakebase</a> | 20 min | Consulta tus tablas por HTTPS con un token OAuth y recibe JSON. Necesita el secret scope `lakebase-workshop` que prepara tu instructor. |
# MAGIC | 4 | <a href="$./journeys/capstone-app/capstone_app_databricks_es">Crear una app de Databricks sobre Lakebase</a> | 45 min | Despliega desde un notebook un tablero en FastAPI en Databricks Apps, con Lakebase como backend. Necesita permiso para crear apps. |
