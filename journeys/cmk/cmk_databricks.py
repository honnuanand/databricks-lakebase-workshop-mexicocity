# Databricks notebook source
# MAGIC %md
# MAGIC # Customer-Managed Keys (CMK), how they work
# MAGIC
# MAGIC This journey is an explainer and configuration reference, not a runnable lab. Customer-Managed Keys (CMK) are configured at the workspace and instance level by administrators. Once configured, Lakebase uses your keys transparently; you query normally.
# MAGIC
# MAGIC This notebook teaches the concepts and shows you how to verify your configuration. If you are not a workspace admin, share this with your admin and return after CMK is enabled.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

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

# MAGIC %md
# MAGIC ## What CMK is
# MAGIC
# MAGIC Encryption at rest means your data on disk is encrypted. By default, Databricks (or your cloud provider) holds the encryption keys. With CMK, you hold your own keys in your KMS (Key Management Service):
# MAGIC
# MAGIC - **AWS:** AWS KMS (Key Management Service)
# MAGIC - **Azure:** Azure Key Vault
# MAGIC - **GCP:** Google Cloud KMS
# MAGIC
# MAGIC Databricks requests a decrypt operation from your KMS for each read. If you revoke the key, Databricks cannot decrypt, and all access stops immediately. It is your kill-switch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Why CMK matters
# MAGIC
# MAGIC In regulated industries (healthcare, finance, government), your compliance requirements may mandate:
# MAGIC
# MAGIC - You must control the encryption keys (no third-party key holders).
# MAGIC - You must be able to revoke access instantly.
# MAGIC - You must audit who accessed the keys and when.
# MAGIC - You must rotate keys on a schedule you define.
# MAGIC
# MAGIC CMK lets you meet all of these in Lakebase.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Latency impact
# MAGIC
# MAGIC Each query makes decrypt calls to your KMS. This adds a few milliseconds per request:
# MAGIC
# MAGIC - Direct Lakebase query: typically 10-50 ms round trip. With CMK, add 5-10 ms for KMS calls.
# MAGIC - Multi-round-trip workloads: if your workload makes many small queries, KMS latency compounds.
# MAGIC
# MAGIC In practice, for most workloads, the overhead is unnoticeable. For extremely latency-sensitive applications (sub-millisecond), measure with CMK enabled in a staging environment first.

# COMMAND ----------

# MAGIC %md
# MAGIC ## How to set it up (admin task)
# MAGIC
# MAGIC ### AWS KMS
# MAGIC
# MAGIC 1. Create a symmetric encryption key in AWS KMS in the region where your workspace is deployed.
# MAGIC 2. Attach a key policy that allows the Databricks service role (provided during account setup) to call Decrypt, GenerateDataKey, and DescribeKey.
# MAGIC 3. Give the key ARN to your Databricks account team. They configure the workspace.
# MAGIC 4. All new Lakebase instances in that workspace use the key from that point on.
# MAGIC
# MAGIC ### Azure Key Vault
# MAGIC
# MAGIC 1. Create a key in Azure Key Vault.
# MAGIC 2. Grant the Databricks managed identity Decrypt, Encrypt, and other required permissions.
# MAGIC 3. Provide the key URI to your Databricks account team.
# MAGIC
# MAGIC ### GCP Cloud KMS
# MAGIC
# MAGIC 1. Create a key in Cloud KMS.
# MAGIC 2. Grant the Databricks service account the cloudkms.cryptoKeyEncrypter and cloudkms.cryptoKeyDecrypter roles.
# MAGIC 3. Provide the key resource ID to your Databricks account team.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Testing CMK (non-destructive)

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

from lakebase import connect

# A normal query. If CMK is enabled, Lakebase decrypts using your KMS in the background.
# You will not see the KMS call; it is transparent.

print("If CMK is enabled on your instance:")
print("  - This query will work normally.")
print("  - Behind the scenes, Lakebase called your KMS to decrypt the data pages.")
print("  - Check your KMS audit logs to see the decrypt calls.")
print()

try:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            print(f"Query result: {result}")
            print("Connection successful.")
except Exception as e:
    print(f"Error: {e}")
    print("If you see 'KMS permission denied', your KMS or key configuration has an issue.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key rotation

# COMMAND ----------

# MAGIC %md
# MAGIC ### Automatic rotation
# MAGIC
# MAGIC Enable automatic key rotation in your KMS (typically annual). Your KMS generates new key versions; Lakebase uses the latest for new writes. Old data is decrypted with old key versions until it is rewritten.
# MAGIC
# MAGIC ### Manual rotation
# MAGIC
# MAGIC If you want to rotate immediately:
# MAGIC
# MAGIC 1. Create a new key version in your KMS.
# MAGIC 2. Contact your Databricks account team to update the workspace config to the new key version.
# MAGIC 3. Lakebase uses the new key for new writes. Old data is gradually re-encrypted during compaction.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Revoking the key (kill-switch)
# MAGIC
# MAGIC To immediately stop all access to encrypted data:
# MAGIC
# MAGIC 1. In your KMS, **disable** or **delete** the key.
# MAGIC 2. Lakebase instances encrypted with that key will fail on the next query with a KMS permission error.
# MAGIC 3. To restore access, re-enable the key in your KMS.
# MAGIC
# MAGIC This is your compliance kill-switch: no Lakebase API call needed, just your KMS controls.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting
# MAGIC
# MAGIC ### Query fails with 'KMS permission denied'
# MAGIC
# MAGIC Check:
# MAGIC - Does the Databricks service role/identity still have permissions on the key in your KMS?
# MAGIC - Is the key enabled (not disabled or deleted)?
# MAGIC - Is the key in the same region as Lakebase?
# MAGIC - If using AWS cross-region replication, check that the replica key is also enabled.
# MAGIC
# MAGIC ### Decryption latency is high
# MAGIC
# MAGIC Each decrypt call to your KMS adds a few milliseconds. If you see unusually high latency:
# MAGIC - Check your KMS service health in the cloud console.
# MAGIC - Verify network connectivity between your Databricks region and your KMS region.
# MAGIC - Consider enabling KMS request batching or caching (if your KMS provider supports it).
# MAGIC - Measure in a non-production environment to set baselines.
# MAGIC
# MAGIC ### CMK settings not visible in workspace console
# MAGIC
# MAGIC CMK is available only on:
# MAGIC - Enterprise-tier Databricks workspaces.
# MAGIC - Supported cloud providers (GA on AWS and Azure, limited availability on GCP).
# MAGIC - Workspaces provisioned after CMK enablement.
# MAGIC
# MAGIC Contact your Databricks account team to confirm availability.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Security best practices
# MAGIC
# MAGIC 1. **Audit and log:** Enable and monitor KMS audit logs for all access and rotations.
# MAGIC 2. **Least privilege:** Limit who can manage keys in your KMS. Use IAM roles / RBAC strictly.
# MAGIC 3. **Automate rotation:** Set up automatic key rotation in your KMS (typically annual).
# MAGIC 4. **Test recovery:** Periodically test revoking and re-enabling the key in a non-production environment to verify your runbook.
# MAGIC 5. **Document:** Document your key management process, rotation schedule, and disaster recovery steps.
# MAGIC 6. **Separate keys for environments:** Use different keys for dev, staging, and production. This limits blast radius if a key is compromised.
# MAGIC 7. **Backup:** If your KMS supports it, set up key material backup (some KMS providers offer this for recovery).

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC CMK gives you full cryptographic control: your keys in your KMS, your rotation policy, your revocation kill-switch. Once enabled, CMK is invisible to users; queries work the same way, but with the confidence that your data is encrypted under your control. This is typically required in regulated industries and a security best practice for all organizations. For questions on your specific setup, contact your Databricks account team.
