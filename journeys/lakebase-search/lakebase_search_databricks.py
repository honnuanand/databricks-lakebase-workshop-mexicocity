# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers: Journey 2 of 4 · Agent developers: Journey 4 of 5 · Lakebase Search</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Lakebase Search
# MAGIC #### Duration: 35 minutes
# MAGIC
# MAGIC *Journey 2 of 4 for App developers and 4 of 5 for Agent developers. JSONB matched exact values; this journey finds rows by their words and by their meaning.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC A fraud and AML analyst searches hundreds of alert notes. Sometimes they know the exact term: a
# MAGIC **CLABE**, a **CURP**, the word "chargeback". Sometimes they only know what happened: "the customer lost
# MAGIC control of their account", which the notes describe as a new device, a SIM swap, or a changed phone
# MAGIC number, without ever saying "takeover". One kind of search alone misses half of these.
# MAGIC
# MAGIC **Lakebase Search** puts both inside your Lakebase database, next to the operational data:
# MAGIC `lakebase_text` ranks keyword matches with **BM25**, `lakebase_vector` finds rows by meaning with an
# MAGIC **approximate nearest-neighbor (ANN)** index, and one SQL query fuses the two into a **hybrid search**
# MAGIC that can still filter and join like any other query. In this lab you enable it, embed 40 analyst notes
# MAGIC with a real embedding model, and run all three.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Enable Lakebase Search** on your project and install its extensions.
# MAGIC 2. **Rank keyword matches with BM25**, and see where it beats Postgres's classic `ts_rank`.
# MAGIC 3. **Search by meaning** with real embeddings and a `lakebase_ann` index.
# MAGIC 4. **Fuse both into a hybrid search** with Reciprocal Rank Fusion, filtered and joined to live tables.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Lakebase Search:** a project setting that adds three Postgres extensions: `lakebase_text` (keyword search), `lakebase_vector` (vector search), and `lakebase_tokenizer` (tokenization, including Chinese, Japanese, and Korean).
# MAGIC - **BM25:** the standard relevance score for keyword search. It rewards rare words, repeated words, and short, focused text, using statistics from the whole table. `lakebase_text` computes it with a `lakebase_bm25` index.
# MAGIC - **Embedding:** a list of numbers a model produces for a text, so texts with similar meaning get similar numbers. This journey uses `databricks-gte-large-en`, which returns 1,024 numbers per text.
# MAGIC - **ANN index:** finds the nearest embeddings without comparing against every row. `lakebase_ann` partitions the vectors (IVF) and compresses them (RaBitQ); on a small table it simply compares them all.
# MAGIC - **Hybrid search:** combining keyword and vector results. **Reciprocal Rank Fusion (RRF)** adds `1 / (60 + rank)` from each list, so rows that rank well in both come first.
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your project and branch and load the bank.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute.
# MAGIC     Needs: <strong>Lakebase Search enabled on your project</strong> (step A3 shows how) and the
# MAGIC     <code>databricks-gte-large-en</code> embedding endpoint.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank-alex-kim
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Load the helpers
# MAGIC
# MAGIC This loads `connect()` from `common/scripts/`, which opens a connection to your branch with a login
# MAGIC token from your Databricks identity, and defines two small helpers for the embedding model:
# MAGIC
# MAGIC - `embed(texts)` sends a list of texts to the `databricks-gte-large-en` serving endpoint and returns one
# MAGIC   embedding (1,024 numbers) per text.
# MAGIC - `to_vector(numbers)` writes an embedding in the text form Postgres reads as a `vector`.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

# COMMAND ----------

import os, sys, requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, client

EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "databricks-gte-large-en")

def embed(texts: list[str]) -> list[list[float]]:
    """One embedding per text, from the embedding model's serving endpoint."""
    w = client()
    r = requests.post(f"{w.config.host}/serving-endpoints/{EMBED_ENDPOINT}/invocations",
                      headers=w.config.authenticate(), json={"input": texts}, timeout=120)
    r.raise_for_status()
    return [row["embedding"] for row in r.json()["data"]]

def to_vector(numbers: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in numbers) + "]"

print(f"helpers ready; embedding endpoint: {EMBED_ENDPOINT} ({len(embed(['test'])[0])} dimensions)")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `helpers ready; embedding endpoint: databricks-gte-large-en (1024 dimensions)`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>404 Client Error</code>: the endpoint name is wrong or it doesn't exist in this workspace. Check <strong>Serving</strong> in the left sidebar, and fix <code>EMBED_ENDPOINT</code> in this cell.</li>
# MAGIC       <li><code>403 Client Error</code>: you can't query the endpoint. Ask your instructor for <code>CAN_QUERY</code> on it.</li>
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ### A3. Enable Lakebase Search
# MAGIC
# MAGIC Enable Lakebase Search in your project settings:
# MAGIC
# MAGIC 1. In your Lakebase project, click **Settings** in the left navigation.
# MAGIC 2. Under **Lakebase Search**, click **Enable Lakebase Search**.
# MAGIC
# MAGIC Your project is the one in the `LB_PROJECT` widget, `bank-<your email name>`. Open it from the
# MAGIC **Lakebase Postgres** app.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">Warning: enabling Lakebase Search</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li>Restarts all computes in your project, dropping any active connections</li>
# MAGIC       <li>Makes the <code>lakebase_vector</code>, <code>lakebase_text</code>, and <code>lakebase_tokenizer</code> extensions available to install</li>
# MAGIC       <li>Cannot be turned off once enabled</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC Then run the next cell. It installs the three extensions on your branch; until Lakebase Search is
# MAGIC enabled, it stops and points you back here. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_text;
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE;   -- CASCADE also installs pgvector
# MAGIC CREATE SCHEMA IF NOT EXISTS tokenizer_ext;
# MAGIC CREATE EXTENSION IF NOT EXISTS lakebase_tokenizer WITH SCHEMA tokenizer_ext;
# MAGIC ```

# COMMAND ----------

try:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_text")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE")
            cur.execute("CREATE SCHEMA IF NOT EXISTS tokenizer_ext")
            cur.execute("CREATE EXTENSION IF NOT EXISTS lakebase_tokenizer WITH SCHEMA tokenizer_ext")
            cur.execute("SELECT extname, extversion FROM pg_extension "
                        "WHERE extname LIKE 'lakebase%' ORDER BY extname")
            installed = cur.fetchall()
except Exception as e:
    if "shared_preload_libraries" in str(e):
        raise SystemExit("Lakebase Search isn't enabled on your project yet. Follow the two steps in A3, "
                         "wait for the computes to restart, then rerun this cell.") from None
    raise

print("Lakebase Search is enabled. Extensions installed:")
for name, version in installed:
    print(f"  {name} {version}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Lakebase Search is enabled. Extensions installed:
# MAGIC   lakebase_text 0.1.3
# MAGIC   lakebase_tokenizer 0.2.0
# MAGIC   lakebase_vector 1.1.1
# MAGIC ```
# MAGIC
# MAGIC The version numbers may be newer in your workspace.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Lakebase Search isn't enabled on your project yet</code>: do the two steps above in your own project, then rerun this cell.</li>
# MAGIC       <li>A connection error right after you enable it: the computes are restarting. Wait a few seconds and rerun this cell.</li>
# MAGIC       <li>No <strong>Lakebase Search</strong> section in Settings: your project needs Postgres 16 or later. The workshop project uses 17.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Load the analyst notes

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Load 40 notes
# MAGIC
# MAGIC `search_note`, in this journey's folder, has 40 short notes analysts wrote on alerts: account takeover,
# MAGIC structuring, money mules, card fraud, phishing, disputes, SPEI and CoDi issues, and false positives. Some
# MAGIC are written to make keyword search struggle: several account takeovers never use the word "takeover".
# MAGIC Rerunning is safe; the rows have fixed ids. The SQL, in short:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE IF NOT EXISTS bank.search_note (
# MAGIC     note_id INT PRIMARY KEY, account_id TEXT REFERENCES bank.account,
# MAGIC     category TEXT, ts TIMESTAMPTZ, writeup TEXT);
# MAGIC INSERT INTO bank.search_note VALUES (...) ON CONFLICT (note_id) DO NOTHING;
# MAGIC SELECT category, count(*) FROM bank.search_note GROUP BY category ORDER BY count(*) DESC;
# MAGIC ```

# COMMAND ----------

with open(os.path.join(os.getcwd(), "search_notes.sql")) as f:
    notes_sql = f.read()

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(notes_sql)
        cur.execute("SELECT category, count(*) FROM bank.search_note GROUP BY category ORDER BY count(*) DESC, category")
        by_category = cur.fetchall()

print(f"{sum(n for _, n in by_category)} notes in bank.search_note:")
for category, n in by_category:
    print(f"  {category:10} {n}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC 40 notes in bank.search_note:
# MAGIC   fraud      13
# MAGIC   cleared    9
# MAGIC   aml        6
# MAGIC   dispute    5
# MAGIC   phishing   4
# MAGIC   mule       3
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Add the search columns
# MAGIC
# MAGIC Two new columns on the same rows: `writeup_tsv`, the note's words in the normalized form keyword search
# MAGIC uses (Postgres keeps it up to date by itself), and `embedding`, the note's meaning as 1,024 numbers. The
# MAGIC cell sends the notes that don't have an embedding yet to the model, in one call, and stores the
# MAGIC results. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS writeup_tsv tsvector
# MAGIC   GENERATED ALWAYS AS (to_tsvector('english', writeup)) STORED;
# MAGIC ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS embedding vector(1024);
# MAGIC UPDATE bank.search_note SET embedding = '<1,024 numbers>'::vector WHERE note_id = <id>;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS writeup_tsv tsvector "
                    "GENERATED ALWAYS AS (to_tsvector('english', writeup)) STORED")
        cur.execute("ALTER TABLE bank.search_note ADD COLUMN IF NOT EXISTS embedding vector(1024)")
        cur.execute("SELECT note_id, writeup FROM bank.search_note WHERE embedding IS NULL ORDER BY note_id")
        missing = cur.fetchall()
        if missing:
            for (note_id, _), numbers in zip(missing, embed([w for _, w in missing])):
                cur.execute("UPDATE bank.search_note SET embedding = %s::vector WHERE note_id = %s",
                            [to_vector(numbers), note_id])
        cur.execute("SELECT count(embedding), count(*) FROM bank.search_note")
        with_embedding, total = cur.fetchone()
        cur.execute("SELECT writeup_tsv FROM bank.search_note WHERE note_id = 5")
        sample_tsv = cur.fetchone()[0]

print(f"embedded {len(missing)} notes now; {with_embedding} of {total} have an embedding")
print(f"note 5 as words: {sample_tsv}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** on the first run (rerunning embeds 0 notes):
# MAGIC
# MAGIC ```
# MAGIC embedded 40 notes now; 40 of 40 have an embedding
# MAGIC note 5 as words: 'ad':20 'beneficiari':18 'carrier':6 'code':10 'new':14 'one':8 'one-tim':7 'report':3 'sim':1,15 'swap':2 'time':9 'went':11
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** both kinds of search work from columns on the same row as the note. `writeup_tsv` keeps the words without endings or common words ("carrier" becomes `carrier`, "codes" becomes `code`), with their positions.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Build the search indexes
# MAGIC
# MAGIC Build both indexes **after** the data is loaded: BM25 computes its statistics over the whole table when
# MAGIC the index is built, and `VACUUM` refreshes them after a bulk load. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS search_note_bm25 ON bank.search_note USING lakebase_bm25 (writeup_tsv);
# MAGIC CREATE INDEX IF NOT EXISTS search_note_ann  ON bank.search_note USING lakebase_ann (embedding vector_cosine_ops);
# MAGIC VACUUM bank.search_note;
# MAGIC SELECT lakebase_ann_index_info('bank.search_note_ann');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE INDEX IF NOT EXISTS search_note_bm25 ON bank.search_note USING lakebase_bm25 (writeup_tsv)")
        cur.execute("CREATE INDEX IF NOT EXISTS search_note_ann ON bank.search_note "
                    "USING lakebase_ann (embedding vector_cosine_ops)")
        cur.execute("VACUUM bank.search_note")
        cur.execute("SELECT lakebase_ann_index_info('bank.search_note_ann')")
        ann_info = cur.fetchone()[0]

print("indexes ready: search_note_bm25 (lakebase_bm25), search_note_ann (lakebase_ann)")
print(f"lakebase_ann_index_info: {ann_info}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC indexes ready: search_note_bm25 (lakebase_bm25), search_note_ann (lakebase_ann)
# MAGIC lakebase_ann_index_info: {"default_epsilon":1.899999976158142,"default_probes":[],"lists":[],"version":"_2"}
# MAGIC ```
# MAGIC
# MAGIC `"lists":[]` means the index has no IVF partitions: with 40 rows, `lakebase_ann` compares the query
# MAGIC against every vector, which is exact and fast at this size. With millions of rows it partitions them
# MAGIC and only scans the closest partitions.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Keyword search with BM25

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Find an exact term
# MAGIC
# MAGIC An analyst looks for every note that mentions a **CLABE**. The `<@>` operator returns the BM25 score as a
# MAGIC **negative** number, so the most relevant note has the lowest score and the query orders ascending. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', 'CLABE'), 'bank.search_note_bm25') AS score, writeup
# MAGIC   FROM bank.search_note
# MAGIC  ORDER BY score
# MAGIC  LIMIT 3;
# MAGIC ```

# COMMAND ----------

BM25 = "writeup_tsv <@> to_bm25query(to_tsvector('english', %(q)s), 'bank.search_note_bm25')"

def keyword_search(q: str, limit: int = 5):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT note_id, {BM25} AS score, writeup FROM bank.search_note "
                        f"ORDER BY score LIMIT %(limit)s", {"q": q, "limit": limit})
            return cur.fetchall()

print("BM25 for 'CLABE':")
for note_id, score, writeup in keyword_search("CLABE", 3):
    print(f"  {note_id:>2}  {score:7.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC BM25 for 'CLABE':
# MAGIC   29   -2.864  SPEI transfer returned by the receiving bank because the CLABE had a t
# MAGIC   22   -2.654  Fake invoice email from a supplier changed the CLABE for payment. Comm
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** BM25 finds exact terms, like codes, ids, and names. Only the notes that contain
# MAGIC "CLABE" score; a note that doesn't contain any search word doesn't come back at all.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. BM25 against the classic `ts_rank`
# MAGIC
# MAGIC Postgres has always had keyword search: `@@` matches and `ts_rank` scores. For "account takeover", the
# MAGIC classic query needs **both** words in a note; BM25 ranks every note that has **either** word, weighting
# MAGIC the rare word ("takeover") more than the common one ("account"). The two queries:
# MAGIC
# MAGIC ```sql
# MAGIC -- classic
# MAGIC SELECT note_id, ts_rank(writeup_tsv, plainto_tsquery('english', 'account takeover')) AS rank
# MAGIC   FROM bank.search_note WHERE writeup_tsv @@ plainto_tsquery('english', 'account takeover')
# MAGIC  ORDER BY rank DESC;
# MAGIC -- Lakebase Search
# MAGIC SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', 'account takeover'), 'bank.search_note_bm25') AS score
# MAGIC   FROM bank.search_note ORDER BY score LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT note_id, ts_rank(writeup_tsv, plainto_tsquery('english', %s)) AS rank, writeup "
                    "FROM bank.search_note WHERE writeup_tsv @@ plainto_tsquery('english', %s) "
                    "ORDER BY rank DESC, note_id", ["account takeover", "account takeover"])
        classic = cur.fetchall()

print(f"classic ts_rank: {len(classic)} notes")
for note_id, rank, writeup in classic:
    print(f"  {note_id:>2}  {rank:.3f}  {writeup[:70]}")
print("\nBM25: top 5")
for note_id, score, writeup in keyword_search("account takeover"):
    print(f"  {note_id:>2}  {score:7.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC classic ts_rank: 2 notes
# MAGIC    1  0.099  Account takeover suspected: password reset, then a SPEI transfer to a
# MAGIC    2  0.099  Confirmed account takeover. Customer never requested the credential ch
# MAGIC
# MAGIC BM25: top 5
# MAGIC    2   -4.265  Confirmed account takeover. Customer never requested the credential ch
# MAGIC    1   -4.265  Account takeover suspected: password reset, then a SPEI transfer to a
# MAGIC    9   -1.810  AML review opened for structuring across three accounts owned by the s
# MAGIC   13   -1.673  Possible money mule: a student account receives transfers from strange
# MAGIC   22   -1.612  Fake invoice email from a supplier changed the CLABE for payment. Comm
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** BM25 ranks partial matches instead of dropping them, and weighs each word by how
# MAGIC rare it is in the whole table. But it still only sees words: notes 3 to 7 describe account takeovers
# MAGIC without those words, and neither query finds them.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Search by meaning

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Ask in plain language
# MAGIC
# MAGIC The cell turns the question into an embedding with the same model, then orders the notes by cosine
# MAGIC distance with `<=>` (lower is more similar), using the `lakebase_ann` index. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, embedding <=> '<question embedding>'::vector AS distance, writeup
# MAGIC   FROM bank.search_note
# MAGIC  ORDER BY distance
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

QUESTION = "customer lost control of their account"
question_vector = to_vector(embed([QUESTION])[0])

def semantic_search(vector: str, limit: int = 5):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT note_id, embedding <=> %(v)s::vector AS distance, writeup FROM bank.search_note "
                        "ORDER BY distance LIMIT %(limit)s", {"v": vector, "limit": limit})
            return cur.fetchall()

print(f"Closest in meaning to '{QUESTION}':")
for note_id, distance, writeup in semantic_search(question_vector):
    print(f"  {note_id:>2}  {distance:.3f}  {writeup[:70]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** the order is the same on every run; the last decimal of a distance can vary slightly:
# MAGIC
# MAGIC ```
# MAGIC Closest in meaning to 'customer lost control of their account':
# MAGIC    2  0.250  Confirmed account takeover. Customer never requested the credential ch
# MAGIC    4  0.273  Customer says someone else got into the mobile app; the email on file
# MAGIC    6  0.340  Security questions answered correctly by a caller whose voice did not
# MAGIC    7  0.336  Session cookies reused from a foreign IP address. Customer was asleep
# MAGIC   35  0.352  New phone set up by the customer in the branch, identity checked in pe
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the model connects "lost control of their account" with "someone else got into
# MAGIC the mobile app" and "a caller whose voice did not match", which share no keywords with the question.
# MAGIC Note 35 is a cleared case that only sounds similar; E1 filters it out. Notes 6 and 7 come out slightly
# MAGIC out of order (0.340 before 0.336): the index is *approximate*, comparing compressed vectors first, so
# MAGIC near-ties can swap. That's the trade an ANN index makes for speed on large tables.

# COMMAND ----------

# MAGIC %md
# MAGIC ### D2. Where vectors fall short, and the plan Postgres uses
# MAGIC
# MAGIC The same semantic search for the exact term "CLABE" returns notes that are *about* transfers, not the
# MAGIC ones that contain the code: meaning is the wrong tool for exact terms. The cell also shows the query plan,
# MAGIC to confirm both kinds of search use their index. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN SELECT note_id FROM bank.search_note ORDER BY embedding <=> '<embedding>'::vector LIMIT 5;
# MAGIC ```

# COMMAND ----------

print("Semantic search for 'CLABE':")
for note_id, distance, writeup in semantic_search(to_vector(embed(["CLABE"])[0]), 3):
    print(f"  {note_id:>2}  {distance:.3f}  {writeup[:70]}")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("EXPLAIN SELECT note_id FROM bank.search_note ORDER BY embedding <=> %s::vector LIMIT 5",
                    [question_vector])
        vector_plan = [r[0] for r in cur.fetchall()]
        cur.execute(f"EXPLAIN SELECT note_id FROM bank.search_note ORDER BY {BM25} LIMIT 5",
                    {"q": "account takeover"})
        keyword_plan = [r[0] for r in cur.fetchall()]

print("\nPlans:")
print("  vector: ", next(line.strip() for line in vector_plan if "Index Scan" in line))
print("  keyword:", next(line.strip() for line in keyword_plan if "Index Scan" in line))

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Semantic search for 'CLABE':
# MAGIC    8  0.443  Structuring pattern: SPEI transfers just under the internal reporting
# MAGIC   34  0.466  Payroll run triggered a velocity alert: two hundred transfers to emplo
# MAGIC    9  0.466  AML review opened for structuring across three accounts owned by the s
# MAGIC
# MAGIC Plans:
# MAGIC   vector:  ->  Index Scan using search_note_ann on search_note  (cost=0.00..8.50 rows=40 width=12)
# MAGIC   keyword: ->  Index Scan using search_note_bm25 on search_note  (cost=0.00..8.50 rows=40 width=12)
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** keyword search and vector search each fail where the other succeeds, which is
# MAGIC why the next step combines them. Both are ordinary index scans inside Postgres.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Hybrid search

# COMMAND ----------

# MAGIC %md
# MAGIC ### E1. Fuse both rankings, filter, and join
# MAGIC
# MAGIC One query takes the top 20 from each search, gives each note `1 / (60 + rank)` from each list it
# MAGIC appears in (**Reciprocal Rank Fusion**), drops cleared cases with a normal `WHERE`, and joins the account
# MAGIC to show its live status. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC WITH v AS (SELECT note_id, RANK() OVER (ORDER BY d) AS rank FROM (
# MAGIC              SELECT note_id, embedding <=> '<question embedding>'::vector AS d
# MAGIC                FROM bank.search_note ORDER BY d LIMIT 20) x),
# MAGIC      k AS (SELECT note_id, RANK() OVER (ORDER BY s) AS rank FROM (
# MAGIC              SELECT note_id, writeup_tsv <@> to_bm25query(to_tsvector('english', '<question>'), 'bank.search_note_bm25') AS s
# MAGIC                FROM bank.search_note ORDER BY s LIMIT 20) y)
# MAGIC SELECT n.note_id, n.category, a.status AS account_status, v.rank AS vector_rank, k.rank AS keyword_rank,
# MAGIC        COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf
# MAGIC   FROM bank.search_note n
# MAGIC   JOIN bank.account a USING (account_id)
# MAGIC   LEFT JOIN v USING (note_id)
# MAGIC   LEFT JOIN k USING (note_id)
# MAGIC  WHERE (v.note_id IS NOT NULL OR k.note_id IS NOT NULL)
# MAGIC    AND n.category <> 'cleared'
# MAGIC  ORDER BY rrf DESC, n.note_id
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

HYBRID = f"""
WITH v AS (SELECT note_id, RANK() OVER (ORDER BY d) AS rank FROM (
             SELECT note_id, embedding <=> %(v)s::vector AS d
               FROM bank.search_note ORDER BY d LIMIT 20) x),
     k AS (SELECT note_id, RANK() OVER (ORDER BY s) AS rank FROM (
             SELECT note_id, {BM25} AS s
               FROM bank.search_note ORDER BY s LIMIT 20) y)
SELECT n.note_id, n.category, a.status, v.rank, k.rank,
       COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf, n.writeup
  FROM bank.search_note n
  JOIN bank.account a USING (account_id)
  LEFT JOIN v USING (note_id)
  LEFT JOIN k USING (note_id)
 WHERE (v.note_id IS NOT NULL OR k.note_id IS NOT NULL)
   AND n.category <> 'cleared'
 ORDER BY rrf DESC, n.note_id
 LIMIT 5
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(HYBRID, {"q": QUESTION, "v": question_vector})
        hybrid = cur.fetchall()

print(f"Hybrid search for '{QUESTION}' (cleared cases excluded):")
print(f"  {'note':>4}  {'category':9} {'account':14} {'vector':>6} {'keyword':>7}  {'rrf':>6}")
for note_id, category, status, vrank, krank, rrf, writeup in hybrid:
    print(f"  {note_id:>4}  {category:9} {status:14} {vrank or '-':>6} {krank or '-':>7}  {rrf:.4f}  {writeup[:45]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Hybrid search for 'customer lost control of their account' (cleared cases excluded):
# MAGIC   note  category  account        vector keyword     rrf
# MAGIC      2  fraud     good_standing       1       2  0.0325  Confirmed account takeover. Customer never re
# MAGIC      1  fraud     watch               6       5  0.0305  Account takeover suspected: password reset, t
# MAGIC      7  fraud     watch               3      11  0.0300  Session cookies reused from a foreign IP addr
# MAGIC     39  aml       watch               7      10  0.0292  Customer cannot explain the source of a large
# MAGIC     21  phishing  watch              19       1  0.0291  Caller posing as bank security asked the cust
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** notes that both searches rank well come first. Note 7 is only 11th by keywords
# MAGIC but 3rd by meaning, and note 21 is 1st by keywords but 19th by meaning; fused, both make the top 5. The
# MAGIC cleared false positive from D1 (note 35) is gone, and each row shows its account's live status. Filtering
# MAGIC and joining work like in any other query, because the search runs inside the same database as the accounts.

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Typos in ids

# COMMAND ----------

# MAGIC %md
# MAGIC ### F1. Find an account from a mistyped id
# MAGIC
# MAGIC BM25 and vectors work on words and meaning; for short codes with a typo, Postgres's `pg_trgm` compares
# MAGIC three-character pieces. An analyst types `CTA-10234`, missing a digit. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS pg_trgm;
# MAGIC SELECT account_id, similarity(account_id, 'CTA-10234') AS sim
# MAGIC   FROM bank.account
# MAGIC  ORDER BY sim DESC
# MAGIC  LIMIT 3;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        cur.execute("SELECT account_id, similarity(account_id, %s) AS sim FROM bank.account "
                    "ORDER BY sim DESC, account_id LIMIT 3", ["CTA-10234"])
        matches = cur.fetchall()

print("Accounts closest to 'CTA-10234':")
for account_id, sim in matches:
    print(f"  {account_id}  similarity={sim:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Accounts closest to 'CTA-10234':
# MAGIC   CTA-100234  similarity=0.750
# MAGIC   CTA-100235  similarity=0.500
# MAGIC   CTA-100240  similarity=0.400
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the right account comes first despite the typo. Each kind of search has its job:
# MAGIC BM25 for words, vectors for meaning, trigrams for spelling.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Lakebase Search or Databricks Vector Search?</strong></summary>
# MAGIC
# MAGIC Use Lakebase Search to search **live operational rows** inside your app's database, where results must
# MAGIC reflect the latest writes and join to other tables, as here. Use Databricks Vector Search for large
# MAGIC document collections synced from the lakehouse in batches, such as thousands of PDFs.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Tuning</strong></summary>
# MAGIC
# MAGIC - **BM25:** `k1` (default 1.2) controls how much repeated words count; `b` (default 0.75) controls how much
# MAGIC   long notes are penalized. Set them with `CREATE INDEX ... WITH (k1 = 1.5)` or `ALTER INDEX ... SET`.
# MAGIC - **Vectors:** `SET lakebase_ann.probes` scans more partitions for better recall on large tables, and
# MAGIC   `SET lakebase_ann.prefilter = on` applies cheap filters before the search.
# MAGIC - **RRF:** the constant 60 and the top-20 lists are starting points; tune them on real questions from your
# MAGIC   analysts.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Indexes and scale to zero</strong></summary>
# MAGIC
# MAGIC Both indexes are stored with the data, so they survive when your compute suspends and come back with
# MAGIC the next query; nothing is rebuilt. After a large bulk load, run `VACUUM` so BM25's statistics include
# MAGIC the new rows.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Why does `<@>` return a negative number?</strong></summary>
# MAGIC
# MAGIC It's the BM25 score with its sign flipped, so ordering ascending, like a distance, puts the most relevant note first.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Which search finds the notes about a CLABE, and which finds "lost control of their account"?</strong></summary>
# MAGIC
# MAGIC BM25 finds the exact term CLABE; vector search finds the account takeovers described in other words. Hybrid search gets both.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why build the BM25 index after loading the data?</strong></summary>
# MAGIC
# MAGIC BM25 computes its statistics over the whole table when the index is built; `VACUUM` refreshes them after more rows are loaded.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusion
# MAGIC
# MAGIC In this lab you enabled Lakebase Search, embedded 40 notes with a real model, and searched them three
# MAGIC ways. Key takeaways:
# MAGIC
# MAGIC 1. **Lakebase Search is a project setting plus three extensions,** inside the same Postgres as your data.
# MAGIC 2. **BM25 (`lakebase_text`) is for exact words,** and ranks better than the classic `ts_rank`.
# MAGIC 3. **Vectors (`lakebase_vector`) are for meaning,** with real embeddings and an ANN index.
# MAGIC 4. **Hybrid search is one SQL query:** RRF fuses both rankings, and filters and joins work as usual.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next**, depending on your track:
# MAGIC
# MAGIC - App developers: <a href="$../data-api/data_api_databricks">Lakebase Data API →</a>
# MAGIC - Agent developers: <a href="$../pg-features/pg_features_databricks">Online Feature Serving →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
