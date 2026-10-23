# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Taller de Lakebase</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Parte 2 · Desarrolladores de aplicaciones · Recorrido 3 de 4 · API de datos de Lakebase</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # API de datos de Lakebase
# MAGIC #### Duración: 20 minutos
# MAGIC
# MAGIC *Recorrido 3 de 4 de la ruta de Desarrolladores de aplicaciones. Hasta ahora cada consulta pasó por una conexión de Postgres; este recorrido lee las mismas tablas por HTTPS.*
# MAGIC
# MAGIC ## Resumen
# MAGIC
# MAGIC Un equipo de banca móvil quiere los datos de las cuentas en su app, pero un teléfono no debería tener una
# MAGIC conexión a la base de datos ni un driver de Postgres. Habla HTTPS y JSON.
# MAGIC
# MAGIC La **Data API de Lakebase** expone tus tablas como una API REST: `GET <url>/bank/account` devuelve filas
# MAGIC en JSON, con filtros y selección de columnas como parámetros de la URL, y se autentica con un token
# MAGIC OAuth de Databricks. En este laboratorio encuentras la Data API de tu rama, obtienes un token y la
# MAGIC llamas.
# MAGIC
# MAGIC Un detalle: la Data API rechaza las solicitudes del dueño del proyecto, y tú eres dueño de tu proyecto.
# MAGIC Así que la llamas como lo haría una app real, con un **service principal**: el del taller, al que
# MAGIC `00-setup/setup_databricks_es` le dio acceso de solo lectura a tu banco.
# MAGIC
# MAGIC ## Objetivos de aprendizaje
# MAGIC
# MAGIC Al terminar este laboratorio podrás:
# MAGIC
# MAGIC 1. **Encontrar la URL de la Data API de tu rama** y lo que hay que configurar para usarla.
# MAGIC 2. **Autenticarte como service principal** con un token OAuth en el encabezado `Authorization`.
# MAGIC 3. **Leer y filtrar filas por HTTPS** con parámetros REST.
# MAGIC 4. **Comparar la llamada REST con el SQL** que reemplaza, y saber cuándo conviene cada uno.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conceptos clave
# MAGIC
# MAGIC - **API REST:** una interfaz HTTPS: haces `GET` a una URL y recibes JSON. Cualquier lenguaje o dispositivo que hable HTTPS puede usarla, sin driver de base de datos.
# MAGIC - **Data API:** la interfaz REST de Lakebase a tus tablas (compatible con PostgREST). Se habilita por rama y solo expone los esquemas que elijas.
# MAGIC - **Token OAuth (JWT):** un token firmado de corta duración que demuestra quién eres. La Data API lo necesita en el encabezado `Authorization: Bearer`.
# MAGIC - **Rol `authenticator`:** el rol de Postgres con el que se conecta la Data API. En cada solicitud cambia al rol de quien llama, así que ese rol tiene que estar otorgado a `authenticator`. No se le puede otorgar el rol del dueño del proyecto, y por eso el dueño no puede llamar a la Data API.
# MAGIC - **Service principal:** una identidad de Databricks para una app o un script, no para una persona. Inicia sesión con un client id y un secreto. El service principal del taller tiene un rol de Postgres en tu rama con `SELECT` sobre las tablas de `bank`, creado por la configuración.
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
# MAGIC     Necesitas: el secret scope <code>lakebase-workshop</code> con el client id y el secreto del service
# MAGIC     principal del taller, que tu instructor crea antes de la sesión. Con eso, el paso 5 de la configuración
# MAGIC     habilita la Data API y crea el rol del service principal. Sin eso, los pasos REST se omiten solos.
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
# MAGIC ### A2. Carga el cliente HTTP
# MAGIC
# MAGIC Esta celda carga `httpx` si está instalado, o un pequeño sustituto hecho con `requests`, además de los
# MAGIC módulos de ayuda del taller.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

# Usa httpx si está instalado; si no, usa requests
try:
    import httpx
except ImportError:
    import requests
    
    class _RequestsClient:
        def __init__(self, timeout=10):
            self._s = requests.Session()
            self._timeout = timeout
        
        def __enter__(self):
            return self
        
        def __exit__(self, *a):
            self._s.close()
        
        def get(self, url, headers=None, params=None):
            return self._s.get(url, headers=headers, params=params, timeout=self._timeout)
        
        def post(self, url, headers=None, json=None):
            return self._s.post(url, headers=headers, json=json, timeout=self._timeout)
    
    class httpx:
        Client = _RequestsClient

from lakebase import client, branch_endpoint, _env

print("Cliente HTTP listo (httpx o el sustituto con requests).")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Cliente HTTP listo (httpx o el sustituto con requests).`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Conéctate

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Encuentra la URL de la Data API de tu rama
# MAGIC
# MAGIC La Data API se habilita por rama. Su URL base sale de la configuración de la Data API de la rama, y las
# MAGIC solicitudes van a `<url>/<esquema>/<tabla>`, por ejemplo `<url>/bank/account`.

# COMMAND ----------

import json

project = _env("LB_PROJECT", required=True)
branch = _env("LB_BRANCH", required=True)

w = client()   # in a notebook, signs in as you; no CLI profile needed
host, endpoint_id, _ = branch_endpoint(w, project, branch)

try:
    rest_url = w.postgres.get_data_api(
        name=f"projects/{project}/branches/{branch}/databases/databricks-postgres/data-api").status.url
except Exception:
    rest_url = ""

print(f"Datos de conexión:")
print(f"  Proyecto: {project}")
print(f"  Rama: {branch}")
print(f"  Host: {host}")
print(f"  Data API URL: {rest_url or '(la Data API no está habilitada en esta rama)'}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:** tu proyecto y tu rama, el host del endpoint y la URL de la Data API, o `(la Data API no está
# MAGIC habilitada en esta rama)`:
# MAGIC
# MAGIC ```
# MAGIC Datos de conexión:
# MAGIC   Proyecto: bank-alex-kim
# MAGIC   Rama: u-alex-kim
# MAGIC   Host: ep-....database.us-east-2.cloud.databricks.com
# MAGIC   Data API URL: https://ep-....database.us-east-2.cloud.databricks.com/api/2.0/workspace/<id del workspace>/rest/databricks_postgres
# MAGIC ```
# MAGIC
# MAGIC **Qué demuestra:** el endpoint REST pertenece a tu rama: está en el mismo host al que te has conectado con SQL.
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
# MAGIC ### B2. Obtén un token OAuth para el service principal
# MAGIC
# MAGIC La Data API acepta un token OAuth de Databricks (un JWT) en el encabezado `Authorization: Bearer`. Esta
# MAGIC celda lee el client id y el secreto del service principal del taller del secret scope
# MAGIC `lakebase-workshop` y los cambia por un token en el endpoint OAuth del workspace, `/oidc/v1/token`. Es
# MAGIC el flujo OAuth *client credentials* que usan las apps y los scripts. El token es válido por cerca de una hora.

# COMMAND ----------

import requests

def get_oauth_token() -> str:
    """Get a Databricks OAuth token (a JWT) for the workshop service principal."""
    client_id = dbutils.secrets.get("lakebase-workshop", "sp-client-id")
    client_secret = dbutils.secrets.get("lakebase-workshop", "sp-client-secret")
    response = requests.post(f"{w.config.host}/oidc/v1/token", auth=(client_id, client_secret),
                             data={"grant_type": "client_credentials", "scope": "all-apis"}, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]

try:
    token = get_oauth_token()
    print(f"Token OAuth obtenido para el service principal del taller.")
    print(f"  Token: {token[:20]}... (recortado)")
except Exception as e:
    token = ""
    print(f"Sin token: {str(e)[:200]}")
    print("  Revisa que exista el secret scope lakebase-workshop y que puedas leerlo.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Token OAuth obtenido para el service principal del taller.` y los primeros caracteres
# MAGIC del token. Los notebooks ocultan los valores de los secretos en su salida, así que el secreto nunca se imprime.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Llama a la API

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Comprueba que la Data API responde
# MAGIC
# MAGIC Un `GET` de una cuenta. La respuesta te dice qué falta, si falta algo:
# MAGIC
# MAGIC - **200:** lista.
# MAGIC - **No habilitada, o sin token:** el paso 5 de la configuración no se ejecutó; la celda imprime qué hacer.
# MAGIC - **406:** el esquema `bank` no está expuesto.
# MAGIC - **403 `permission denied to set role`:** el rol de Postgres de quien llama no está otorgado a
# MAGIC   `authenticator`. Es lo que recibe el dueño del proyecto, y por eso este recorrido usa el service principal.

# COMMAND ----------

headers = {"Authorization": f"Bearer {token}"}
data_api_enabled = False

if not rest_url or not token:
    print("La Data API no está configurada en tu rama, o no hay token del service principal.")
    print("  Pídele a tu instructor el secret scope lakebase-workshop y vuelve a ejecutar")
    print("  00-setup/setup_databricks_es (paso 5) y este notebook desde el paso B1.")
else:
    url = f"{rest_url}/bank/account"
    print(f"Revisando la Data API:")
    print(f"  URL: {url}")
    print(f"  Método: GET")
    print()
    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers, params={"limit": 1})
        if response.status_code == 200:
            print("ÉXITO: la Data API responde para bank.account")
            data_api_enabled = True
        elif response.status_code == 403:
            print("403: el rol de Postgres del service principal no está configurado en tu rama.")
            print("  Vuelve a ejecutar 00-setup/setup_databricks_es (paso 5), que lo crea en production;")
            print("  una rama creada antes no lo tiene, así que después reinicia la tuya.")
            print(f"  Respuesta: {response.text[:200]}")
        elif response.status_code == 406:
            print("406: el esquema bank no está expuesto. En la configuración de la Data API de tu rama, agrega bank")
            print("  en Exposed schemas y vuelve a ejecutar esta celda.")
        else:
            print(f"Respuesta inesperada: {response.status_code}")
            print(f"Respuesta: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Resultado esperado:**
# MAGIC
# MAGIC ```
# MAGIC Revisando la Data API:
# MAGIC   URL: https://ep-....database.us-west-2.cloud.databricks.com/api/2.0/workspace/<id del workspace>/rest/databricks_postgres/bank/account
# MAGIC   Método: GET
# MAGIC
# MAGIC ÉXITO: la Data API responde para bank.account
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Velo en la interfaz (opcional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Abre la app <strong>Lakebase Postgres</strong>, luego tu proyecto y tu rama, y elige <strong>Data API</strong>: muestra si la API está habilitada, su URL y los esquemas expuestos.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Lee todas las cuentas por HTTPS
# MAGIC
# MAGIC ```
# MAGIC GET <url>/bank/account
# MAGIC ```

# COMMAND ----------

if not data_api_enabled:
    print("Se omite: la Data API no está lista en tu rama (ver C1).")
else:
    url = f"{rest_url}/bank/account"

    print(f"Obteniendo todas las cuentas:")
    print(f"  URL: {url}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers)
            response.raise_for_status()
            accounts = response.json()
            print(f"Resultado: {len(accounts)} cuentas")
            if accounts:
                print(f"\nPrimera cuenta:")
                print(f"  {accounts[0]}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Resultado: 8 cuentas` y luego la primera en JSON, como
# MAGIC `{'account_id': 'CTA-100234', 'branch_id': 'BR-CDMX', 'line': 'Checking', ...}`. Si C1 no tuvo éxito, la
# MAGIC celda imprime `Se omite`.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C3. Filtra y elige columnas
# MAGIC
# MAGIC Los parámetros REST hacen el trabajo de `WHERE` y `SELECT`: `status=eq.good_standing` filtra y
# MAGIC `select=account_id,status` elige las columnas.
# MAGIC
# MAGIC ```
# MAGIC GET <url>/bank/account?select=account_id,status&status=eq.good_standing
# MAGIC ```

# COMMAND ----------

if not data_api_enabled:
    print("Se omite: la Data API no está lista en tu rama.")
else:
    url = f"{rest_url}/bank/account"
    params = {"select": "account_id,status", "status": "eq.good_standing"}

    print(f"Obteniendo solo las cuentas good_standing:")
    print(f"  URL: {url}")
    print(f"  Parámetros: {params}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers, params=params)
            response.raise_for_status()
            accounts = response.json()
            print(f"Resultado: {len(accounts)} cuentas good_standing")
            print(f"\nCuentas de ejemplo:")
            for account in accounts[:3]:
                print(f"  {account}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** `Resultado: 5 cuentas good_standing` y tres de ellas, como `{'account_id': 'CTA-100234', 'status': 'good_standing'}`.
# MAGIC Si C1 no tuvo éxito, la celda imprime `Se omite`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. REST y SQL

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. La misma pregunta en SQL
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status FROM bank.account WHERE status = 'good_standing';
# MAGIC ```

# COMMAND ----------

from lakebase import connect

if not data_api_enabled:
    print("Se omite: la Data API no está habilitada.")
else:
    print("Equivalente en SQL:")
    print("  SELECT account_id, status FROM bank.account WHERE status = 'good_standing'")
    print()

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT account_id, status FROM bank.account WHERE status = 'good_standing'")
            sql_rows = cur.fetchall()
            print(f"Resultado en SQL: {len(sql_rows)} filas")
            print(f"\nFilas de ejemplo:")
            for row in sql_rows[:3]:
                print(f"  {row}")

    print(f"\nREST y SQL devuelven los mismos datos. REST es útil para clientes web y móviles.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Resultado esperado:** cuando la Data API está lista, `Resultado en SQL: 5 filas` y las mismas cuentas que en C3. Si no,
# MAGIC `Se omite: la Data API no está habilitada.`
# MAGIC
# MAGIC **Qué demuestra:** la llamada REST y el SQL leen las mismas filas; la Data API es otra puerta a las mismas tablas.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPANDE PARA VER NOTAS ADICIONALES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>¿REST o SQL?</strong></summary>
# MAGIC
# MAGIC Usa la Data API para clientes que no pueden, o no deberían, tener una conexión a la base de datos:
# MAGIC navegadores, apps móviles, integraciones con socios. Respeta los mismos roles de Postgres y la misma
# MAGIC seguridad a nivel de fila que el SQL. Usa SQL para uniones, trabajo masivo y todo lo que dependa del
# MAGIC rendimiento, donde una consulta le gana a muchas llamadas HTTP.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Comprueba lo que aprendiste
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. ¿Qué URL devuelve la tabla `bank.account`?</strong></summary>
# MAGIC
# MAGIC `<la URL de la Data API de tu rama>/bank/account`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. ¿Por qué este recorrido llama a la Data API como service principal y no como tú?</strong></summary>
# MAGIC
# MAGIC Eres dueño de tu proyecto, y la Data API rechaza al dueño: se conecta como `authenticator` y cambia al rol de quien llama, y el rol del dueño no se puede otorgar a `authenticator`. El service principal tiene un rol normal que sí se puede otorgar.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. ¿A qué corresponden `status=eq.good_standing` y `select=account_id,status` en SQL?</strong></summary>
# MAGIC
# MAGIC A `WHERE status = 'good_standing'` y `SELECT account_id, status`.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusión
# MAGIC
# MAGIC En este laboratorio encontraste la Data API de tu rama, obtuviste un token y la llamaste. Puntos clave:
# MAGIC
# MAGIC 1. **La Data API convierte tablas en endpoints REST,** `<url>/<esquema>/<tabla>`, que devuelven JSON.
# MAGIC 2. **Se habilita por rama** y solo expone los esquemas que elijas.
# MAGIC 3. **Cada llamada lleva un token OAuth,** y la API actúa como el rol de Postgres de quien llama, así que
# MAGIC    aplican los permisos y la seguridad a nivel de fila de siempre. El dueño del proyecto no puede ser quien
# MAGIC    llama, así que las apps la llaman como un service principal con solo los permisos que necesitan.
# MAGIC 4. **REST conviene para clientes sin driver de base de datos;** SQL sigue siendo lo mejor para consultas
# MAGIC    pesadas.
# MAGIC
# MAGIC El último recorrido de esta ruta pone una app web completa sobre el mismo banco.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Siguiente en la ruta de Desarrolladores de aplicaciones:** <a href="$../capstone-app/capstone_app_databricks_es">Crear una app de Databricks sobre Lakebase →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE_es">← Volver al índice</a>
