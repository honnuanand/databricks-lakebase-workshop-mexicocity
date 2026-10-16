# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 6 de 6 · Crear una app de Databricks sobre Lakebase</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Crear una app de Databricks sobre Lakebase
# MAGIC #### Duración: 45 minutos
# MAGIC
# MAGIC *Recorrido 6 de 6 de la ruta de Desarrolladores de aplicaciones. Los recorridos anteriores usaron Lakebase desde un notebook; este pone una app web real frente a tu rama.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC El equipo de fraude quiere un tablero sencillo: las cuentas y su estado, las transacciones recientes de
# MAGIC una cuenta, las posiciones de un fondo a todos sus niveles y una búsqueda en las notas de caso. Tiene
# MAGIC que leer datos en vivo de Lakebase y correr dentro de Databricks, sin un servidor aparte que mantener.
# MAGIC
# MAGIC El taller ya incluye esa app: un backend en FastAPI y una interfaz de una sola página, en la carpeta
# MAGIC `app/` de este recorrido. En este laboratorio la despliegas en **Databricks Apps** desde este notebook,
# MAGIC le das su propio acceso a tu rama y la abres para ver cómo lee el banco. No escribes código de la app.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Crear una Databricks App** y encontrar el service principal con el que corre.
# MAGIC 2. **Darle a la app acceso a Lakebase:** permiso en el proyecto y un rol de Postgres en tu rama.
# MAGIC 3. **Desplegar la app desde una carpeta del workspace,** indicándole qué proyecto y qué rama atender.
# MAGIC 4. **Explicar cómo una app se autentica en Lakebase** con credenciales de corta duración, sin contraseña.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **Databricks App:** una app web (aquí FastAPI) que Databricks hospeda y ejecuta por ti, con su propia URL. Solo los usuarios con sesión iniciada en el workspace pueden abrirla.
# MAGIC - **Service principal:** una identidad no humana. Cada app recibe una al crearse y corre como ella, así que necesita sus propios permisos, aparte de los tuyos.
# MAGIC - **Dos capas de acceso:** un permiso del workspace sobre el proyecto de Lakebase (`CAN_USE`, para que la app encuentre tu rama y obtenga credenciales) y un rol de Postgres en la rama (para que la base de datos la deje leer las tablas de `bank`).
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
# MAGIC     Ejecuta una vez <code>00-setup/setup_databricks_es</code> para crear tu rama y cargar el banco.
# MAGIC     Conecta este notebook a cómputo <strong>serverless</strong>.
# MAGIC     Necesitas permiso para crear Databricks Apps en este workspace y <code>CAN_MANAGE</code> en el proyecto
# MAGIC     de Lakebase (la configuración de la clase te da los dos). Crear la app y su primer despliegue tardan unos minutos.
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
# MAGIC ### A2. Ponle nombre a tu app y ubica su código
# MAGIC
# MAGIC Tu app se llama como tu rama, así que cada participante tiene la suya. Su código es la carpeta `app/`
# MAGIC junto a este notebook en el workspace: `app.yaml` (cómo arrancarla), `requirements.txt` y `backend/`
# MAGIC (el código de FastAPI y la interfaz).

# COMMAND ----------

import os, sys, re, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint
from databricks.sdk.service.apps import App, AppDeployment, EnvVar
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
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
# MAGIC atiende:          proyecto bank, rama u-alex-kim, esquema bank
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
# MAGIC ## B. Crea la app

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Crea la app
# MAGIC
# MAGIC Crear una app reserva su nombre y su URL, arranca su cómputo y crea el **service principal** con el que
# MAGIC va a correr. Si tu app ya existe de una ejecución anterior, la celda la reutiliza.

# COMMAND ----------

try:
    app = w.apps.get(APP_NAME)
    print(f"la app {APP_NAME} ya existe; se reutiliza")
except Exception:
    t0 = time.time()
    app = w.apps.create_and_wait(App(name=APP_NAME, description="Lakebase workshop: bank dashboard"))
    print(f"app {APP_NAME} creada en {time.time() - t0:.0f}s")

SP = app.service_principal_client_id
print("service principal:", SP)
print("URL de la app:    ", app.url)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `app bank-dash-alex-kim creada en 135s` en una ejecución de prueba (unos dos minutos), y luego el
# MAGIC id del service principal de la app (un UUID) y su URL, como
# MAGIC `https://bank-dash-alex-kim-<id del workspace>.aws.databricksapps.com`.
# MAGIC
# MAGIC **Qué demuestra:** la app existe y tiene su propia identidad. Todavía nada puede leer tus datos: el service principal no tiene permisos.
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
# MAGIC **Resultado esperado:** `se otorgó CAN_USE en el proyecto bank al service principal de la app`

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Un rol de Postgres en tu rama
# MAGIC
# MAGIC La base de datos también tiene que conocer a la app. `databricks_create_role()` crea un rol de Postgres
# MAGIC ligado al service principal, para que pueda iniciar sesión con credenciales de Databricks; luego recibe
# MAGIC acceso de lectura a las tablas de `bank`. El SQL que se ejecuta en tu rama:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS databricks_auth;
# MAGIC SELECT databricks_create_role('<id del service principal>', 'SERVICE_PRINCIPAL');
# MAGIC GRANT USAGE ON SCHEMA bank TO "<id del service principal>";
# MAGIC GRANT SELECT ON ALL TABLES IN SCHEMA bank TO "<id del service principal>";
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

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** ```
# MAGIC rol de Postgres de la app creado
# MAGIC se otorgó acceso de lectura al esquema bank
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el acceso se otorga en dos lugares, el workspace y la base de datos, y los dos están acotados: la app puede leer las tablas de `bank` de tu rama, y nada más.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Despliega la app

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Despliega
# MAGIC
# MAGIC Desplegar toma una copia de la carpeta `app/` y la arranca. La celda le pasa el proyecto, la rama y el
# MAGIC esquema como variables de entorno, así que la app atiende **tu** rama.

# COMMAND ----------

t0 = time.time()
dep = w.apps.deploy_and_wait(APP_NAME, AppDeployment(
    source_code_path=SOURCE,
    env_vars=[EnvVar(name="LAKEBASE_PROJECT", value=PROJECT),
              EnvVar(name="LAKEBASE_BRANCH", value=MINE),
              EnvVar(name="LAKEBASE_SCHEMA", value=SCHEMA)]))
print(f"despliegue {dep.deployment_id}: {dep.status.state.value} en {time.time() - t0:.0f}s")
print(dep.status.message)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `despliegue ...: SUCCEEDED en 16s` en una ejecución de prueba, y luego `App started successfully`.
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
# MAGIC así que abres la app en una pestaña nueva del navegador y no desde este notebook. La celda imprime los
# MAGIC enlaces. La app también tiene una pequeña API JSON junto a su interfaz, útil para ver exactamente qué lee.

# COMMAND ----------

app = w.apps.get(APP_NAME)
print("estado de la app:", app.app_status.state.value if app.app_status else "?",
      "| cómputo:", app.compute_status.state.value if app.compute_status else "?")
print()
print("Abre en una pestaña nueva del navegador:")
for path, what in [("/", "la interfaz del tablero"),
                   ("/api/health", "quién es la app y qué rama atiende"),
                   ("/api/accounts", "todas las cuentas, leídas de tu rama"),
                   ("/api/accounts/CTA-100240", "una cuenta y sus transacciones recientes"),
                   ("/api/holdings/FUND-GROWTH-A", "las posiciones de un fondo a todos sus niveles (SQL recursivo)"),
                   ("/api/casenotes?q=SPEI", "búsqueda de texto completo en las notas de caso")]:
    print(f"  {app.url}{path}")
    print(f"      {what}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** `estado de la app: RUNNING | cómputo: ACTIVE` y seis enlaces. Abiertos en el navegador, una
# MAGIC ejecución de prueba devolvió:
# MAGIC
# MAGIC - `/api/health`: `{"ok":true,"identity":"<id del service principal de la app>","project":"bank","branch":"u-tunombre","schema":"bank"}`
# MAGIC - `/api/accounts`: las 8 cuentas, empezando por `{"account_id":"CTA-100234","branch_id":"BR-CDMX","line":"Checking",...}`
# MAGIC - `/api/accounts/CTA-100240`: la cuenta con su CLABE (`999180000001002407`) y sus transacciones recientes, incluida la transferencia SPEI de MXN 38,500
# MAGIC - `/api/holdings/FUND-GROWTH-A`: el efectivo, la canasta de acciones y Zafiro Software del fondo en el nivel 1, y lo que contiene la canasta en el nivel 2
# MAGIC - `/api/casenotes?q=SPEI`: las dos notas de caso que mencionan SPEI
# MAGIC
# MAGIC **Qué demuestra:** la app lee tu rama con su propia identidad: `/api/health` muestra el service principal, no a ti, y los datos son tu banco.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Solución de problemas</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Un error que menciona <code>permission denied</code> o <code>password authentication failed</code>:</strong> vuelve a ejecutar C1 y C2, y recarga la página.</li>
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
# MAGIC <summary><strong>2. ¿Qué dos permisos necesita la app?</strong></summary>
# MAGIC
# MAGIC `CAN_USE` en el proyecto de Lakebase y un rol de Postgres en la rama con acceso de lectura a `bank`.
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
# MAGIC En este laboratorio creaste una Databricks App, le diste acceso a tu rama, la desplegaste y la
# MAGIC abriste. Puntos clave:
# MAGIC
# MAGIC 1. **Una app corre como su propio service principal,** así que tiene exactamente el acceso que le das.
# MAGIC 2. **El acceso tiene dos capas:** `CAN_USE` en el proyecto de Lakebase y un rol de Postgres en la rama.
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
