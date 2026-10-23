# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 4 de 4 · Crear una app de Databricks sobre Lakebase</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Crear una app de Databricks sobre Lakebase
# MAGIC #### Duración: 45 minutos
# MAGIC
# MAGIC *Recorrido 4 de 4 de la ruta de Desarrolladores de aplicaciones. Los recorridos anteriores usaron Lakebase desde un notebook; este pone todo lo que construiste detrás de una app web real.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC El equipo de fraude quiere una consola para sus analistas, que lea datos en vivo de Lakebase y corra
# MAGIC dentro de Databricks, sin un servidor aparte que mantener. El taller ya la incluye: una **consola del
# MAGIC analista de fraude** (un backend en FastAPI y una interfaz de una sola página, en español) en la carpeta
# MAGIC `app/` de este recorrido. Cada una de sus cuatro pestañas resume una parte del taller, sobre tu propia
# MAGIC rama, y muestra el SQL o la llamada REST que acaba de ejecutar:
# MAGIC
# MAGIC 1. **Tu base de datos** (Parte 1): tu proyecto, tu rama, su endpoint de cómputo y su estado, y quién es la app.
# MAGIC 2. **Búsqueda** (Lakebase Search): las mismas 40 notas, buscadas por palabras (BM25), por significado (vectores), de forma híbrida (RRF) o con las tres lado a lado.
# MAGIC 3. **Cuenta** (API de datos de Lakebase): una cuenta leída por la Data API, y sus transacciones por SQL.
# MAGIC 4. **Instrumentos** (Datos JSON con JSONB): instrumentos filtrados por su ficha técnica JSONB con `@>`.
# MAGIC
# MAGIC En este laboratorio la despliegas en **Databricks Apps** desde este notebook, le das su propio acceso a
# MAGIC tu rama y al modelo de embeddings, y la abres. No escribes código de la app.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Crear una Databricks App** y encontrar el service principal con el que corre.
# MAGIC 2. **Darle a la app acceso a Lakebase y a un modelo:** permiso en el proyecto, un rol de Postgres en tu rama que la Data API pueda usar, y el endpoint de embeddings como recurso de la app.
# MAGIC 3. **Desplegar la app desde una carpeta del workspace,** indicándole qué proyecto y qué rama atender.
# MAGIC 4. **Explicar cómo una app se autentica en Lakebase** con credenciales de corta duración, sin contraseña.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Databricks App:** una app web (aquí FastAPI) que Databricks hospeda y ejecuta por ti, con su propia URL. Solo los usuarios con sesión iniciada en el workspace pueden abrirla.
# MAGIC - **Service principal:** una identidad no humana. Cada app recibe una al crearse y corre como ella, así que necesita sus propios permisos, aparte de los tuyos.
# MAGIC - **Tres tipos de acceso:** un permiso del workspace sobre el proyecto de Lakebase (`CAN_USE`, para que la app encuentre tu rama y obtenga credenciales), un rol de Postgres en la rama (para que la base de datos la deje leer las tablas de `bank`, y la Data API pueda actuar como ella) y el endpoint de embeddings (`CAN_QUERY`, para que pueda convertir una búsqueda en un vector).
# MAGIC - **Recurso de la app:** algo que la app usa, declarado en la propia app, como un endpoint de Model Serving. Databricks le da al service principal de la app el permiso que indiques.
# MAGIC - **Despliegue:** una copia de la carpeta del código de la app, arrancada en cómputo de Databricks. Volver a desplegar toma los cambios.
# MAGIC
# MAGIC Encontrarás más términos en `docs/glosario-es.md`, en la carpeta del taller.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Configuración
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Antes de empezar</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Ejecuta una vez <code>00-setup/setup_databricks_es</code>, y haz antes los recorridos anteriores de esta ruta:
# MAGIC     la pestaña de búsqueda de la app usa las notas, los embeddings y los índices de <em>Lakebase Search</em> (A3 lo revisa).
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>.
# MAGIC     Necesitas permiso para crear Databricks Apps en este workspace. Eres dueño de tu proyecto de Lakebase, así
# MAGIC     que puedes darle acceso a la app. Crear la app y su primer despliegue tardan unos minutos.
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
# MAGIC ### A2. Ponle nombre a tu app y ubica su código
# MAGIC
# MAGIC Tu app se llama como tu rama, así que cada participante tiene la suya. Su código es la carpeta `app/`
# MAGIC junto a este notebook en el workspace: `app.yaml` (cómo arrancarla), `requirements.txt` y `backend/`
# MAGIC (el código de FastAPI y la interfaz).

# COMMAND ----------

import os, sys, re, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint
from databricks.sdk.service.apps import (App, AppDeployment, AppResource, AppResourceServingEndpoint,
                                        AppResourceServingEndpointServingEndpointPermission, EnvVar)
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
from databricks.sdk.errors import NotFound
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
EMBED_ENDPOINT = "databricks-gte-large-en"   # el modelo que usó Lakebase Search para las notas
w = client()

# Nombres de app: minúsculas, dígitos y guiones, hasta 30 caracteres.
APP_NAME = re.sub(r"[^a-z0-9-]+", "-", ("bank-dash-" + MINE.removeprefix("u-")).lower())[:30].strip("-")
SOURCE = os.path.join(os.getcwd(), "app")
if not SOURCE.startswith("/Workspace"):
    SOURCE = "/Workspace" + SOURCE

print("nombre de la app:", APP_NAME)
print("atiende:         ", f"proyecto {PROJECT}, rama {MINE}, esquema {SCHEMA}")
print("código fuente:   ", SOURCE)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** el nombre de tu app, el proyecto y la rama que atenderá, y la ruta de su código:
# MAGIC
# MAGIC ```
# MAGIC nombre de la app: bank-dash-alex-kim
# MAGIC atiende:          proyecto bank-alex-kim, rama u-alex-kim, esquema bank
# MAGIC código fuente:    /Workspace/Users/alex.kim@example.com/<carpeta>/journeys/capstone-app/app
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> o <code>KeyError: 'LB_PROJECT'</code>: las celdas de A1 no se ejecutaron en esta sesión. Ejecuta las tres celdas de A1 y luego esta.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A3. Revisa que los datos de la ruta estén listos
# MAGIC
# MAGIC La app lee lo que los recorridos anteriores dejaron en tu rama. Esta celda revisa las tres cosas que
# MAGIC necesita: las notas de *Lakebase Search* con sus embeddings y los dos índices de búsqueda, y la Data API,
# MAGIC que activó la configuración. El SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT count(*), count(embedding) FROM bank.search_note;
# MAGIC SELECT to_regclass('bank.search_note_bm25'), to_regclass('bank.search_note_ann');
# MAGIC ```

# COMMAND ----------

from lakebase import run_sql

try:
    notes, embedded = run_sql(f"SELECT count(*), count(embedding) FROM {SCHEMA}.search_note")[0]
    bm25, ann = run_sql(f"SELECT to_regclass('{SCHEMA}.search_note_bm25'), to_regclass('{SCHEMA}.search_note_ann')")[0]
except Exception:
    notes = embedded = 0
    bm25 = ann = None
if not (notes and embedded and bm25 and ann):
    raise SystemExit("Faltan en tu rama las notas de búsqueda, sus embeddings o sus índices. "
                     "Haz primero el recorrido Lakebase Search y vuelve a ejecutar esta celda.")
try:
    data_api = w.postgres.get_data_api(
        name=f"{branch_name(PROJECT, MINE)}/databases/databricks-postgres/data-api").status.url
except Exception:
    raise SystemExit("La Data API no está activada en tu rama. Vuelve a ejecutar 00-setup/setup_databricks_es "
                     "(paso 5) y luego esta celda.") from None

print(f"notas de búsqueda: {notes} ({embedded} con embedding), índices: {bm25}, {ann}")
print(f"Data API:          {data_api}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC notas de búsqueda: 40 (40 con embedding), índices: search_note_bm25, search_note_ann
# MAGIC Data API:          https://ep-....database.us-west-2.cloud.databricks.com/api/2.0/workspace/<id del workspace>/rest/databricks_postgres
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Faltan en tu rama las notas de búsqueda...</code>: haz <em>Lakebase Search</em> en esta rama y luego esta celda. Si reiniciaste tu rama después, vuelve a hacerlo: un reinicio parte de <code>production</code>, que no tiene las notas.</li>
# MAGIC       <li><code>La Data API no está activada en tu rama</code>: vuelve a ejecutar la configuración, que la activa en <code>production</code> y en tu rama.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Crea la app

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Crea la app
# MAGIC
# MAGIC Crear una app reserva su nombre y su URL, arranca su cómputo y crea el **service principal** con el que
# MAGIC va a correr. La celda también declara el endpoint de embeddings como **recurso de la app** con
# MAGIC `CAN_QUERY`, para que la app pueda convertir una búsqueda en un vector con el mismo modelo que usaron las
# MAGIC notas. Si tu app ya existe de una ejecución anterior, la celda la reutiliza y le agrega el recurso si falta.

# COMMAND ----------

model = AppResource(name="embedding-model", serving_endpoint=AppResourceServingEndpoint(
    name=EMBED_ENDPOINT, permission=AppResourceServingEndpointServingEndpointPermission.CAN_QUERY))
try:
    app = w.apps.get(APP_NAME)
    print(f"la app {APP_NAME} ya existe; se reutiliza")
    if not any(r.serving_endpoint and r.serving_endpoint.name == EMBED_ENDPOINT for r in app.resources or []):
        app = w.apps.update(name=APP_NAME, app=App(name=APP_NAME, resources=(app.resources or []) + [model]))
except NotFound:
    t0 = time.time()
    app = w.apps.create_and_wait(App(name=APP_NAME, description="Lakebase workshop: fraud analyst console",
                                     resources=[model]))
    print(f"app {APP_NAME} creada en {time.time() - t0:.0f}s")

SP = app.service_principal_client_id
print("service principal:", SP)
print("URL de la app:    ", app.url)
print("recursos:         ", [f"{r.serving_endpoint.name} ({r.serving_endpoint.permission.value})"
                             for r in app.resources or [] if r.serving_endpoint])

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `app bank-dash-alex-kim creada en ...s` (unos dos minutos; `ya existe; se reutiliza` si vuelves a
# MAGIC ejecutar), y luego el id del service principal de la app (un UUID), su URL, como
# MAGIC `https://bank-dash-alex-kim-<id del workspace>.aws.databricksapps.com`, y `recursos: ['databricks-gte-large-en (CAN_QUERY)']`.
# MAGIC
# MAGIC **Qué demuestra:** la app existe y tiene su propia identidad, que puede llamar al modelo de embeddings. Todavía no puede leer tus datos: el service principal no tiene acceso a tu proyecto.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Error de permisos:</strong> no puedes crear apps en este workspace. Pídeselo a tu instructor.</li>
# MAGIC       <li><strong>El nombre ya está ocupado:</strong> alguien más tiene una app con ese nombre. Cambia <code>APP_NAME</code> en A2 por algo único y vuelve a ejecutar.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Dale a la app acceso a tu rama

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Permiso en el proyecto
# MAGIC
# MAGIC La app busca tu rama y pide una credencial de base de datos de corta duración, las dos cosas a través de
# MAGIC la API de Lakebase. Para eso necesita `CAN_USE` en el proyecto, el menor privilegio que lo permite.

# COMMAND ----------

w.permissions.update("database-projects", PROJECT, access_control_list=[
    AccessControlRequest(service_principal_name=SP, permission_level=PermissionLevel.CAN_USE)])
print(f"se otorgó CAN_USE en el proyecto {PROJECT} al service principal de la app")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `se otorgó CAN_USE en el proyecto bank-alex-kim al service principal de la app`

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Un rol de Postgres en tu rama
# MAGIC
# MAGIC La base de datos también tiene que conocer a la app. `databricks_create_role()` crea un rol de Postgres
# MAGIC ligado al service principal, para que pueda iniciar sesión con credenciales de Databricks; luego recibe
# MAGIC acceso de lectura a las tablas de `bank`. Otorgar el rol a `authenticator` deja que la Data API actúe como
# MAGIC la app, cosa que no hace por ti, el dueño del proyecto. El SQL que se ejecuta en tu rama:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS databricks_auth;
# MAGIC SELECT databricks_create_role('<id del service principal>', 'SERVICE_PRINCIPAL');
# MAGIC GRANT USAGE ON SCHEMA bank TO "<id del service principal>";
# MAGIC GRANT SELECT ON ALL TABLES IN SCHEMA bank TO "<id del service principal>";
# MAGIC GRANT "<id del service principal>" TO authenticator;   -- para la Data API
# MAGIC ```

# COMMAND ----------

host, eid, _ = branch_endpoint(w, PROJECT, MINE)
cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, MINE)}/endpoints/{eid}")
with psycopg.connect(host=host, port=5432, dbname="databricks_postgres", user=w.current_user.me().user_name,
                     password=cred.token, sslmode="require", autocommit=True) as conn, conn.cursor() as cur:
    cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [SP])
    if cur.fetchone():
        print("el rol de Postgres de la app ya existe")
    else:
        cur.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", [SP])
        print("rol de Postgres de la app creado")
    cur.execute(f'GRANT USAGE ON SCHEMA {SCHEMA} TO "{SP}"')
    cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO "{SP}"')
    print(f"se otorgó acceso de lectura al esquema {SCHEMA}")
    cur.execute(f'GRANT "{SP}" TO authenticator')
    print("se otorgó el rol de la app a authenticator, para que la Data API pueda actuar como la app")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `el rol de Postgres de la app ya existe` si vuelves a ejecutar; si no:
# MAGIC
# MAGIC ```
# MAGIC rol de Postgres de la app creado
# MAGIC se otorgó acceso de lectura al esquema bank
# MAGIC se otorgó el rol de la app a authenticator, para que la Data API pueda actuar como la app
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el acceso se otorga en tres lugares, el modelo, el workspace y la base de datos, y cada uno está acotado: la app puede consultar un modelo y leer las tablas de `bank` de tu rama, y nada más.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Despliega la app

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Despliega
# MAGIC
# MAGIC Desplegar toma una copia de la carpeta `app/` y la arranca. La celda le pasa el proyecto, la rama, el
# MAGIC esquema y el endpoint de embeddings como variables de entorno, así que la app atiende **tu** rama.

# COMMAND ----------

t0 = time.time()
dep = w.apps.deploy_and_wait(APP_NAME, AppDeployment(
    source_code_path=SOURCE,
    env_vars=[EnvVar(name="LAKEBASE_PROJECT", value=PROJECT),
              EnvVar(name="LAKEBASE_BRANCH", value=MINE),
              EnvVar(name="LAKEBASE_SCHEMA", value=SCHEMA),
              EnvVar(name="EMBED_ENDPOINT", value=EMBED_ENDPOINT)]))
print(f"despliegue {dep.deployment_id}: {dep.status.state.value} en {time.time() - t0:.0f}s")
print(dep.status.message)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `despliegue ...: SUCCEEDED en 13s` en una ejecución de prueba, y luego `App started successfully`.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre <strong>Compute</strong> → <strong>Apps</strong> y selecciona tu app. La pestaña <strong>Deployments</strong> muestra este despliegue, y <strong>Logs</strong> muestra cómo arranca la app.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>FAILED</code>: abre los <strong>Logs</strong> de la app en la interfaz. Ahí aparece un paquete que falta o un error en <code>app.yaml</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Abre la app

# COMMAND ----------

# MAGIC %md
# MAGIC ### E1. Abre la app
# MAGIC
# MAGIC Databricks Apps solo acepta la sesión del navegador de un usuario con sesión iniciada (o un token OAuth),
# MAGIC así que abres la app en una pestaña nueva del navegador y no desde este notebook. La celda imprime el
# MAGIC enlace a la consola y a la pequeña API JSON detrás de cada pestaña, útil para ver exactamente qué devuelve.

# COMMAND ----------

app = w.apps.get(APP_NAME)
print("estado de la app:", app.app_status.state.value if app.app_status else "?",
      "| cómputo:", app.compute_status.state.value if app.compute_status else "?")
print()
print("Abre en una pestaña nueva del navegador:")
for path, what in [("/", "la consola, con sus cuatro pestañas"),
                   ("/api/health", "pestaña 1: tu proyecto, tu rama, el endpoint y la identidad de la app"),
                   ("/api/search?mode=compare&q=customer%20lost%20control%20of%20their%20account",
                    "pestaña 2: la misma pregunta por palabras, por significado y de forma híbrida"),
                   ("/api/accounts/CTA-100240", "pestaña 3: la cuenta por la Data API, sus transacciones por SQL"),
                   ("/api/instruments?filter=%7B%22sector%22%3A%20%22tech%22%7D", "pestaña 4: los instrumentos cuya ficha JSONB tiene sector tech")]:
    print(f"  {app.url}{path}")
    print(f"      {what}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `estado de la app: RUNNING | cómputo: ACTIVE` y cinco enlaces. En la consola, una ejecución de
# MAGIC prueba mostró:
# MAGIC
# MAGIC - **Tu base de datos:** tu proyecto y tu rama (bifurcada de `production`), el endpoint `primary` en `ACTIVE` o `IDLE` (1 CU, se suspende después de 5 minutos) y la identidad de la app: su service principal, no tú.
# MAGIC - **Búsqueda:** para "customer lost control of their account", la búsqueda híbrida devuelve primero las notas 2, 1 y 7. Compara "CLABE" (solo la encuentra la búsqueda por palabras) con "money sent to strangers" (solo la encuentra la búsqueda por significado).
# MAGIC - **Cuenta:** `CTA-100240`, en observación, con su CLABE `999180000001002407`, leída por la Data API, y sus transacciones por SQL, incluida la transferencia SPEI de MXN 38,500.
# MAGIC - **Instrumentos:** `{"sector": "tech"}` devuelve Quetzal Tecnologia y Zafiro Software con sus fichas técnicas JSONB.
# MAGIC
# MAGIC **Qué demuestra:** la app lee tu rama con su propia identidad, y cada pestaña usa lo que construyó un recorrido: la misma rama, los mismos índices de búsqueda, la misma Data API y la misma columna JSONB.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Un error que menciona <code>permission denied</code> o <code>password authentication failed</code>:</strong> vuelve a ejecutar C1 y C2, y recarga la página.</li>
# MAGIC       <li><strong>Búsqueda dice que el endpoint de embeddings no responde:</strong> vuelve a ejecutar B1, que agrega el modelo como recurso de la app, y luego D1. La búsqueda por palabras funciona sin él.</li>
# MAGIC       <li><strong>Cuenta muestra <code>la Data API respondió 403</code>:</strong> vuelve a ejecutar C2, que otorga el rol de la app a <code>authenticator</code>.</li>
# MAGIC       <li><strong><code>503</code> con "has no host yet":</strong> tu rama no está lista. Revísala en la configuración y recarga.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Limpieza (opcional)

# COMMAND ----------

# MAGIC %md
# MAGIC ### F1. Borra la app cuando termines
# MAGIC
# MAGIC Una app en ejecución mantiene su cómputo encendido. Cuando termines, bórrala: se eliminan la app, su URL
# MAGIC y su service principal. Quita el `#` de la celda siguiente y ejecútala solo cuando ya no necesites el tablero.

# COMMAND ----------

# w.apps.delete(APP_NAME); print(f"app {APP_NAME} eliminada")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** nada mientras la línea siga comentada; con el `#` quitado, `app bank-dash-... eliminada`.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Con qué identidad lee la app tu rama?</strong></summary>
# MAGIC
# MAGIC Con su propio service principal, que se creó junto con la app; no con la tuya.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Qué permisos necesita la app?</strong></summary>
# MAGIC
# MAGIC `CAN_QUERY` en el endpoint de embeddings (como recurso de la app), `CAN_USE` en el proyecto de Lakebase y un rol de Postgres en la rama con acceso de lectura a `bank`, otorgado a `authenticator` para la Data API.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿Por qué no hay contraseña en ninguna parte?</strong></summary>
# MAGIC
# MAGIC La app le pide a Lakebase una credencial de corta duración cada vez que se conecta, con su identidad de Databricks.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusión
# MAGIC
# MAGIC En este laboratorio creaste una Databricks App, le diste acceso a tu rama y a un modelo, la desplegaste
# MAGIC y abriste una consola que junta toda la ruta. Puntos clave:
# MAGIC
# MAGIC 1. **Una app corre como su propio service principal,** así que tiene exactamente el acceso que le das.
# MAGIC 2. **El acceso se acota en tres lugares:** el modelo como recurso de la app, `CAN_USE` en el proyecto de Lakebase y un rol de Postgres en la rama.
# MAGIC 3. **Sin contraseñas:** la app le pide a Lakebase una credencial de corta duración cada vez que se conecta.
# MAGIC 4. **Desplegar es una llamada** desde una carpeta del workspace; la misma app puede atender cualquier
# MAGIC    rama a la que la apuntes.
# MAGIC
# MAGIC Aquí termina la ruta de Desarrolladores de aplicaciones.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Terminaste la ruta de Desarrolladores de aplicaciones.**
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
