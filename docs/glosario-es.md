# Glosario (es-MX)

Términos fijos de los notebooks en español del taller. Úsalos siempre igual, para que todos los
notebooks se lean como uno solo. Varios términos técnicos se quedan en inglés, porque así aparecen en
la documentación y la interfaz de Databricks; la primera vez que aparecen en un notebook, van con la
traducción entre paréntesis. Los nombres de productos (Lakebase, Unity Catalog, Databricks), de
la interfaz (por ejemplo, la pestaña **Branches**) y del código (tablas, columnas, funciones, estados
como `ACTIVE` e `IDLE`) se quedan en inglés.

## Lakebase y Databricks

| Inglés | Español | Nota |
| --- | --- | --- |
| branch | **rama** | `production` es la rama compartida; `u-tunombre` es la tuya. |
| fork (a branch) | **bifurcar** (verbo), **el fork** (sustantivo) | "Bifurcas tu rama" crea un fork: una rama nueva a partir de ella. |
| copy-on-write | **copy-on-write** (copia en escritura) | La rama nueva comparte los datos y solo escribe las páginas que cambias. |
| endpoint, compute | **endpoint**, **cómputo** | El servidor de Postgres al que te conectas. |
| control plane | **control plane** (plano de control) | Las acciones de administración (crear o borrar ramas) que se hacen con la API, no con SQL. |
| point-in-time restore (PITR) | **restauración a un punto en el tiempo** | Crear una rama de la base de datos como estaba en un momento anterior. |
| recovery branch | **rama de recuperación** | |
| history window | **ventana de historial** | Qué tan atrás puedes restaurar: 7 días por defecto. |
| write-ahead log (WAL) | **write-ahead log (WAL)** (registro de escritura anticipada) | |
| LSN | **LSN (número de secuencia del registro)** | |
| scale to zero | **escalar a cero** | |
| suspend timeout | **suspend timeout** (tiempo de suspensión) | Minutos sin consultas antes de que el cómputo se suspenda: 5 en el proyecto del taller. |
| cold wake / warm query | **arranque en frío** / **consulta en caliente** | |
| capacity unit (CU) | **unidad de capacidad (CU)** | |
| serverless compute | **cómputo serverless** | Como aparece en la interfaz de Databricks. |
| login token | **token de inicio de sesión** | Válido por cerca de una hora. |
| widget | **widget** | Los campos de la parte superior del notebook. |
| notebook | **notebook** | |
| lakehouse | **lakehouse** | |
| foreign catalog | **foreign catalog** (catálogo externo) | Un catálogo de Unity Catalog cuyas tablas viven en otra base de datos. |

## PostgreSQL

| Inglés | Español | Nota |
| --- | --- | --- |
| schema (namespace) | **esquema** | Una carpeta de tablas, como `bank`. |
| `information_schema` | **`information_schema`** | Las vistas estándar que describen la propia base de datos. |
| wire protocol | **wire protocol** (protocolo de comunicación) | El "idioma" de red entre un cliente y la base de datos. |
| driver | **driver** | `psycopg` es el driver de Postgres para Python. |
| ORM, BI tool | **ORM**, **herramienta de BI** | |
| query | **consulta** | |
| row, column, table | **fila**, **columna**, **tabla** | |

## Banca

| Inglés | Español | Nota |
| --- | --- | --- |
| bank branch | **sucursal** | La tabla `branch` (`BR-CDMX`, ...). No confundir con una **rama** de Lakebase. |
| account | **cuenta** | Ids `CTA-...`. |
| transaction | **transacción** | La tabla `txn`. |
| SPEI transfer | **transferencia SPEI** | |
| card payment | **pago con tarjeta** | `channel = 'tarjeta'`. |
| fraud score | **puntaje de fraude** | La columna `fraud_risk`. |
| trade, settlement | **operación**, **liquidación** | Las tablas `trade` y `settlement`. |
| fund, instrument, holding | **fondo**, **instrumento**, **posición del fondo** | |
| counterparty, custodian | **contraparte**, **custodio** | |
| case note | **nota de caso** | |
| freeze (an account) | **congelar** | `status = 'frozen'`. |
| hold (on an account) | **retención**, **retener** | La acción del agente en Agentes que usan herramientas; termina en `status = 'frozen'`. |
| AML (anti-money laundering) | **PLD** (prevención de lavado de dinero) | La categoría `AML` de las notas de caso se queda en inglés. |
| dispute | **aclaración** | `event_type = 'dispute'`. |
| chargeback | **contracargo** | |
| beneficiary | **beneficiario** | |
| anomaly score | **puntaje de anomalía** | La columna `anomaly_score`, de 0 a 10. |

## IA y agentes

| Inglés | Español | Nota |
| --- | --- | --- |
| agent | **agente** | |
| agent memory | **memoria del agente** | Filas de `bank.agent_memory`. |
| tool | **herramienta** | Una función que el agente puede llamar; aquí, SQL en tu rama. |
| function calling | **function calling** (llamadas a funciones) | Cuando el modelo elige la herramienta y sus argumentos. |
| prompt | **prompt** | |
| Foundation Model endpoint | **endpoint de Foundation Model** | Un modelo servido por Model Serving, como `databricks-claude-opus-4-8`. |
| grounding | **grounding** (anclar la respuesta en los datos) | |
| fallback | **respuesta de respaldo** | Lo que imprime el notebook si falla la llamada al modelo. |
| idempotent | **idempotente** | |
| audit trail | **registro de auditoría** | |
| confidence, threshold | **confianza**, **umbral** | El umbral de confianza de Revisión humana es 0.75. |
| human in the loop | **human in the loop** (revisión humana) | |
| drift | **drift** (deriva) | |
| embedding | **embedding** | |
| feature (of a model) | **feature** (variable del modelo) | Femenino: "las features". |
| materialize | **materializar** | |
| online serving | **servir en línea** | |
| freshness | **frescura** | La columna `computed_at`. |
| primary key | **llave primaria** | |
| lookup | **búsqueda** | Una búsqueda por llave primaria. |
