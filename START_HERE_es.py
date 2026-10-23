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
# MAGIC Ejecuta una vez el notebook de configuración y después avanza por la Parte 1. En el taller hacemos
# MAGIC la Parte 1 y la ruta de Desarrolladores de aplicaciones. La ruta de Desarrolladores de agentes es para
# MAGIC después del taller. Cada notebook termina con un enlace al siguiente de su ruta y otro para volver a
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
# MAGIC ## Parte 2. Desarrolladores de aplicaciones (en el taller)
# MAGIC
# MAGIC **Esta es la ruta que hacemos juntos durante el taller.** Unas 2 horas.
# MAGIC
# MAGIC | # | Recorrido | Tiempo | Qué vas a hacer |
# MAGIC | - | --------- | ------ | --------------- |
# MAGIC | 1 | <a href="$./journeys/pg-json/pg_json_databricks_es">Datos JSON con JSONB</a> | 20 min | Guarda fichas técnicas variables de instrumentos y fondos como JSONB, consúltalas con SQL e indéxalas con GIN. |
# MAGIC | 2 | <a href="$./journeys/lakebase-search/lakebase_search_databricks_es">Lakebase Search</a> | 35 min | Busca en 40 notas de fraude y PLD por palabras (BM25), por significado (embeddings reales) y de las dos formas a la vez (búsqueda híbrida), con filtros y joins sobre las cuentas. Necesita Lakebase Search activado en tu proyecto (el recorrido explica cómo) y el endpoint de embeddings `databricks-gte-large-en`. |
# MAGIC | 3 | <a href="$./journeys/data-api/data_api_databricks_es">API de datos de Lakebase</a> | 20 min | Consulta tus tablas por HTTPS con un token OAuth y recibe JSON. Necesita el secret scope `lakebase-workshop` que prepara tu instructor. |
# MAGIC | 4 | <a href="$./journeys/capstone-app/capstone_app_databricks_es">Crear una app de Databricks sobre Lakebase</a> | 45 min | Despliega desde un notebook un tablero en FastAPI en Databricks Apps, con Lakebase como backend. Necesita permiso para crear apps. |

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## Después del taller: Desarrolladores de agentes (por tu cuenta)
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">No es parte de la sesión del taller</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Esta ruta no se hace durante el taller. Hazla por tu cuenta después, en este mismo workspace,
# MAGIC     mientras el laboratorio siga disponible. Usa el proyecto y la rama de la configuración; si ya no
# MAGIC     existen, vuelve a ejecutar primero <code>00-setup/setup_databricks_es</code>. Necesita un endpoint de
# MAGIC     Foundation Model. Cerca de 1 hora y 50 minutos.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC | # | Recorrido | Tiempo | Qué vas a hacer |
# MAGIC | - | --------- | ------ | --------------- |
# MAGIC | 1 | <a href="$./journeys/agent-memory/agent_memory_databricks_es">Memoria compartida entre agentes</a> | 20 min | Dos agentes comparten una tabla de memoria: uno escribe una nota de fraude y el otro la lee y actúa. Necesita un endpoint de Foundation Model. |
# MAGIC | 2 | <a href="$./journeys/agentic-work/agentic_work_databricks_es">Agentes que usan herramientas</a> | 20 min | Un agente lee transacciones en vivo con una herramienta, retiene una cuenta marcada y lo recuerda para no retenerla dos veces. Necesita un endpoint de Foundation Model. |
# MAGIC | 3 | <a href="$./journeys/learning-loop/learning_loop_databricks_es">Revisión humana de los resultados de la IA</a> | 25 min | La IA extrae hallazgos de notas de casos con un nivel de confianza; los de baja confianza pasan a un analista. Necesita un endpoint de Foundation Model; reemplaza las notas de caso de tu rama. |
# MAGIC | 4 | <a href="$./journeys/lakebase-search/lakebase_search_databricks_es">Lakebase Search</a> | 35 min | Busca en 40 notas de fraude y PLD por palabras (BM25), por significado (embeddings reales) y de las dos formas a la vez (búsqueda híbrida), con filtros y joins sobre las cuentas. Necesita Lakebase Search activado en tu proyecto (el recorrido explica cómo) y el endpoint de embeddings `databricks-gte-large-en`. |
# MAGIC | 5 | <a href="$./journeys/pg-features/pg_features_databricks_es">Servir features en línea</a> | 10 min | Sirve desde Lakebase las variables de riesgo de fraude de una cuenta con una búsqueda rápida por llave. |
