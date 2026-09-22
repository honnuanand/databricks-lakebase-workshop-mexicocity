# Customer-Managed Keys, FAQ

## Setup and configuration questions

### Do I need CMK?

Probably not, unless you're in a regulated industry (medical, financial, aerospace) or have
strict data governance requirements. For most workloads, Databricks-managed keys are sufficient.

CMK is required if:
- Compliance regulations (HIPAA, PCI-DSS, FedRAMP, ITAR) mandate customer-controlled keys.
- You're running a multi-tenant SaaS and customers demand cryptographic isolation.
- Your data is IP or trade secrets that you want to keep completely opaque to the cloud provider.

### Can I enable CMK after my Lakebase instance is already created?

It depends on your cloud provider and Databricks offering. Typically:

- CMK is configured at the **workspace level**, not per instance.
- Once enabled, all **new** instances use CMK.
- **Existing instances** may need to be migrated (re-encrypted); ask your Databricks account
  team.

For production, enable CMK at workspace setup time if possible, to avoid migration overhead.

### Who sets up CMK? Is it a user or admin task?

CMK setup is a **workspace-admin task**. Users cannot enable it. The workflow is:

1. Your KMS team (AWS/Azure/GCP) creates the key and policies.
2. Your workspace admin (Databricks) configures the workspace to use that key.
3. You (as a user) continue using Lakebase normally; the encryption is transparent.

If you need CMK, work with your workspace admin and cloud provider.

### What if I have multiple cloud providers (AWS, Azure, GCP)?

Lakebase deployments typically run on one cloud provider. CMK is provider-specific:

- Workspace on AWS → use AWS KMS
- Workspace on Azure → use Azure Key Vault
- Workspace on GCP → use GCP Cloud KMS

You can't use AWS KMS for an Azure deployment, etc. If you have multi-cloud, set up CMK on each
cloud according to that provider's offering.

## Security questions

### Does CMK encrypt data in flight (during queries)?

No. CMK encrypts data **at rest** (on disk in storage). Data in flight (between your client and
Lakebase, and between Lakebase components) must be encrypted with **TLS**, which you configure
separately.

### What if my KMS key is compromised?

If an attacker gains access to your KMS key, they can decrypt all your Lakebase data encrypted
with that key. This is why KMS access should be strictly controlled with IAM policies. If you
suspect compromise:

1. Create a new key immediately.
2. Tell your Databricks workspace admin to rotate to the new key.
3. Revoke the old key in your KMS.
4. Monitor audit logs for suspicious KMS access.

### Does Databricks have access to my keys?

No. Databricks cannot see or access your keys. Lakebase **calls your KMS** to encrypt/decrypt,
but the key material stays in your KMS. Databricks engineers cannot bypass this; the KMS API
enforces it.

### What happens if I lose my key?

If you accidentally delete your KMS key and didn't keep a backup:

- All data encrypted with that key becomes permanently inaccessible.
- Lakebase will refuse to decrypt; you'll see KMS errors.
- Recovery is only possible if your KMS provider has a recovery window (e.g., AWS KMS has a
  7-30 day recovery window after deletion).

**Always keep a secure backup of your key outside your KMS, or rely on your KMS provider's
automatic backup.** Check your KMS documentation.

## Operational questions

### Does key rotation cause downtime?

No. Key rotation is zero-downtime. When you activate a new key version:

1. Lakebase uses the new key for new writes.
2. Old data is decrypted with the old key version (still available).
3. As data is rewritten (during compaction), it's re-encrypted with the new key.
4. No restarts, no migrations.

### How long does key rotation take?

Activation is instant. However, re-encryption of old data is gradual (happens during normal
storage compaction). For a 1 TB database, full re-encryption might take days or weeks depending
on write activity. If you need faster re-encryption, contact Databricks.

### What if the KMS service is down?

If your KMS is temporarily unavailable, Lakebase instances using that KMS will fail on decrypt
attempts. Queries will return errors. Once the KMS recovers, queries resume. This is why you
should:

- Set up KMS monitoring and alerting.
- Use a KMS provider with high availability (AWS, Azure, GCP all have regional redundancy).
- Consider a multi-region KMS setup if your workload is mission-critical.

### Can I switch keys without downtime?

Yes, as described above. Rotation is zero-downtime. However, this assumes the new key is in the
same KMS and region. If you're switching KMS providers entirely (e.g., AWS KMS to Azure Key Vault),
that's a bigger migration and requires Databricks involvement.

## Compliance and auditing questions

### How do I prove to auditors that CMK is enabled?

Ask your workspace admin to provide:

1. Workspace settings screenshot showing CMK is configured.
2. KMS key details (key ARN/URI, creation date, rotation policy).
3. Sample audit logs showing KMS Decrypt operations from Lakebase.

These demonstrate to auditors that encryption is customer-controlled.

### Does CMK help with compliance frameworks?

CMK supports compliance in several ways:

- **HIPAA:** customer-controlled keys are often required for HIPAA. CMK enables that.
- **PCI-DSS:** requires strong encryption of sensitive data. CMK satisfies that requirement.
- **FedRAMP:** federal deployments often require customer-managed encryption. CMK is required for
  FedRAMP.
- **GDPR:** data residency and encryption. CMK ensures encryption; data residency is a separate
  configuration.

But CMK alone doesn't make you compliant; it's one piece of a larger compliance program. Work
with your compliance and security teams.

### Who should have access to manage the KMS key?

Restrict KMS key access to:

- Your security/KMS team (who manages the key policies and rotations).
- Workspace admins (in an emergency, to update workspace settings).

**Not** regular users or developers. Use IAM roles to enforce this.

## Troubleshooting

### Queries started failing with "KMS permission denied"

Possible causes:

1. **Key was revoked/deleted:** check if the key exists in your KMS. If revoked intentionally,
   you're in "kill-switch" mode (expected).
2. **Databricks service role lost permissions:** check KMS key policy. Does the Databricks role
   still have Decrypt permission?
3. **Key was disabled:** check KMS console. Re-enable if accidental.
4. **KMS service is down:** check your KMS provider's status page.

### KMS audit logs are missing Decrypt operations

Possible causes:

1. **Audit logging not enabled:** enable audit logging in your KMS console.
2. **Lakebase isn't using CMK:** confirm with workspace admin that CMK is configured.
3. **No queries are running:** if nobody's querying Lakebase, there are no decrypts.

### Setup failed: "Key policy doesn't grant Databricks permission"

The KMS key policy must explicitly grant the Databricks service role/identity the Decrypt and
GenerateDataKey permissions. Check the policy:

- **AWS:** key policy should include the Databricks role ARN and actions kms:Decrypt,
  kms:GenerateDataKey, kms:DescribeKey.
- **Azure:** managed identity should have Get, Decrypt, WrapKey, UnwrapKey permissions on the
  key.
- **GCP:** service account should have roles/cloudkms.cryptoKeyEncrypter and
  roles/cloudkms.cryptoKeyDecrypter.

Have your KMS admin review the policy against your cloud provider's documentation.

### Setup failed: "CMK not available for this tier"

CMK is only available for Enterprise-tier Databricks deployments. If you have a Standard or
Premium tier, you cannot use CMK. Upgrade to Enterprise if CMK is required for your use case.

## No runnable artifact

This journey is a reference guide; there's no Python script or SQL to run. The configuration
happens in your KMS and Databricks workspace settings. The setup is a one-time admin task.
