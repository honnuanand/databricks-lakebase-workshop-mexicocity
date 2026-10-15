# Customer-Managed Keys: encryption under your control

> ## What you'll learn
>
> **Key takeaways**
>
> - Customer-Managed Keys (CMK) let you store encryption keys in your own cloud provider's key management service (AWS KMS, Azure Key Vault, GCP Cloud KMS), not Databricks' infrastructure. Lakebase never sees the key; your cloud provider keeps it.
> - Encryption happens at rest (database files on disk are encrypted with your key). Rotation is zero-downtime: you rotate the key in your KMS, and Lakebase picks up the new key without restarting or migrating data.
> - Revoking access is a kill-switch: revoke the key in your KMS, and even Databricks engineers cannot access your data. This is the strongest form of data isolation for regulated industries.
>
> **You'll be able to:** understand how CMK works with Lakebase, when to enable it, and how to rotate and revoke keys.
>
> **Time:** about 15 minutes (reading + setup understanding)  ·  **Status:** live

## The scenario

You run a bank, one of the most heavily regulated industries there is. Your data includes customer
account details, transaction histories, and trading positions. Legal, compliance, and your
regulators require that you, not the cloud provider, control the encryption keys.

Lakebase's default: keys are managed by Databricks and stored in AWS/Azure/GCP. For regulated
use cases, this isn't enough. You need keys in your own KMS, keys you can rotate, keys you can
revoke if a data breach is suspected.

That's what Customer-Managed Keys (CMK) provides.

## What CMK is and how it works

By default, Lakebase encrypts your data at rest (in storage) with keys that Databricks manages.
Those keys are rotated automatically, but they're in Databricks infrastructure.

With CMK enabled, you create a key in your cloud provider's key management system (AWS KMS, Azure
Key Vault, or GCP Cloud KMS). You give Lakebase permission to *use* that key for encryption, but
you *own and control* it. Lakebase encrypts all new data with your key, and stores that key
identifier with the encrypted data. When Lakebase needs to decrypt, it asks your KMS service to
do the decryption using your key.

The key never leaves your KMS service. Databricks engineers cannot see it. Even if your Lakebase
instance is compromised, the data is useless without your key.

### Encryption at rest

Data written to Lakebase storage (the page server's disks) is encrypted using your CMK. The
encrypted bytes are stored as-is; decryption only happens when Lakebase queries the data.

### Key rotation

You can rotate your key in your KMS without stopping Lakebase. When you rotate, you mark the old
key as "deprecated" and activate a new key. Lakebase continues using the old key to decrypt old
data, and uses the new key for new writes. Over time, as new data is written and old data is
re-encrypted (during compaction), the new key becomes dominant. Zero downtime, no migrations.

### Key revocation

If you suspect a breach or want to shut off access immediately, you can revoke the key in your
KMS. The next time Lakebase tries to decrypt with that key, the KMS refuses. Your data becomes
inaccessible, even to Databricks. This is the strongest isolation guarantee: you hold the kill
switch.

## The business case

CMK is required (or strongly recommended) for:

- **Regulated industries:** financial services, healthcare, aerospace, defense. Compliance
  (PCI DSS, SOX, GLBA, GDPR) often requires customer-controlled keys.
- **Multi-tenant SaaS:** if you're running a SaaS app on Lakebase and your customers demand
  isolation, CMK provides cryptographic proof of separation.
- **Sensitive data assets:** customer PII, account and card numbers, or trading strategies where
  the data itself is the crown jewel.

CMK is optional (default encryption is fine) for:

- Development and testing environments.
- Public data or non-sensitive workloads.
- Organizations without compliance requirements.

## How to enable CMK

CMK is configured at the workspace level, not per instance. To enable:

1. Create a key in your cloud provider's KMS.
   - **AWS:** Create a key in AWS KMS, then create a key policy that allows the Databricks
     service role to use (Encrypt, Decrypt, GenerateDataKey) the key.
   - **Azure:** Create a key in Azure Key Vault, grant Databricks managed identity the key
     permissions.
   - **GCP:** Create a key in Cloud KMS, grant the Lakebase service account the cryptoKeyEncrypter
     and cryptoKeyDecrypter roles.

2. Provide the key identifier to Databricks during workspace creation or update. This is an
   admin/workspace-setup task, not a user action.

3. All new Lakebase instances in that workspace use the key automatically. Existing instances
   continue with Databricks-managed keys unless migrated.

Once enabled, CMK is transparent to users: queries run the same way. The only visible difference
is that decryption calls your KMS, adding a few milliseconds of latency (typically negligible).

## Key rotation and lifecycle

**Rotating a key (zero-downtime):**

1. In your KMS, create a new key version (AWS KMS) or update the key (Azure/GCP) to activate
   the new version.
2. Lakebase automatically picks up the new key for new writes.
3. Old data encrypted with the previous key is decrypted with the previous key (still available).
4. Over time, as Lakebase compacts and rewrites data, old data gets re-encrypted with the new key.

No Lakebase instance restarts, no downtime.

**Revoking a key (immediate kill-switch):**

1. In your KMS, disable or delete the key.
2. The next time Lakebase tries to decrypt data encrypted with that key, the KMS refuses.
3. Your data becomes unreadable to Lakebase and to anyone else without the key.

This is instant and absolute.

## Security considerations

**Threat model:** CMK protects against:

- Storage-level compromise (an attacker gains access to the storage backend).
- Databricks infrastructure compromise (an attacker compromises Databricks' systems).
- Insider threats (Databricks employees trying to read your data).

CMK does **not** protect against:

- Network eavesdropping during normal queries (data in flight must still be encrypted with TLS,
  which you enable separately).
- Application-level compromise (an attacker compromises your app and can query Lakebase as a
  valid user).
- Key compromise (if an attacker steals your key from your KMS, all data is compromised).

**Best practices:**

- **Audit KMS access:** monitor who rotates or accesses your keys in the KMS.
- **Use strong IAM policies:** limit who in your organization can manage keys in your KMS.
- **Automate rotation:** set up key rotation policies in your KMS (e.g., rotate annually).
- **Test revocation:** periodically test revoking a key and confirming Lakebase can't decrypt.

## Monitoring and troubleshooting

CMK operations (encrypt, decrypt, rotate) are logged in your cloud provider's audit logs (AWS
CloudTrail, Azure Activity Log, GCP Cloud Audit Logs). Monitor for:

- Failed decryption attempts (indicates key revocation or permission issues).
- Unusual key rotation patterns.
- KMS access from unexpected principals.

If decryption fails, check:

1. **Key permissions:** does Lakebase still have permission to use the key?
2. **Key status:** is the key active, or has it been disabled/deleted?
3. **Key region:** is the key in the same region as Lakebase?
4. **KMS service health:** is the KMS service reachable and healthy?

## Prerequisites and status

- **Availability:** CMK is GA (General Availability) on AWS and Azure for Enterprise deployments,
  limited availability on GCP. Check with Databricks for your cloud provider.
- **Setup:** requires workspace-admin access to configure KMS and Databricks workspace settings.
- **Cost:** no additional Databricks charges, but your cloud provider may charge for KMS API calls.

This is a read-only explainer journey: there's no runnable artifact or SQL to execute. The
configuration happens at the workspace/admin level, not in your user-level Lakebase instance.

## Wrapping up

CMK moves the encryption key responsibility from Databricks to your organization, in your KMS.
For regulated or high-security use cases, this is non-negotiable: you own the cryptographic
keys, you control access, and you can revoke instantly. For most users, Databricks-managed keys
are sufficient; for your data to be truly secure in a regulated environment, CMK is the way.

For technical details and step-by-step KMS setup (create key policies, configure workspace), see
the Databricks security documentation referenced in [`resources.md`](resources.md).
