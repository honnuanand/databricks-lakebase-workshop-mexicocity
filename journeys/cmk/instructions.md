# Customer-Managed Keys, how to configure and test

This is a reference guide for setting up and testing CMK in your Lakebase instance. Unlike other
journeys, this is **not a runnable script**, CMK setup happens at the workspace/admin level, not
in a user branch. But you can follow these steps to understand the configuration, and optionally
test with a test key if your workspace admin has enabled it.

## Prerequisites

- **Workspace admin access.** CMK is configured by workspace administrators.
- **KMS access.** You need access to your cloud provider's KMS to create keys and manage policies.
- **For testing:** a non-production Lakebase instance (or at least a non-critical one) to test
  key revocation without affecting live workloads.

## Setting up CMK on AWS KMS

### Step 1, create a KMS key

In the AWS console, go to AWS Key Management Service (KMS) and create a customer-managed key:

```
Region: <your-workspace-region>
Key type: Symmetric (Lakebase uses a single key for encrypt/decrypt)
Key usage: Encrypt and Decrypt
Key material origin: AWS KMS
```

Note the key ARN (e.g., `arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789012`).

### Step 2, create a key policy allowing Databricks

The key policy must grant Databricks' AWS service role permission to use the key. Databricks
provides the service role ARN during onboarding. The policy should include:

```json
{
  "Sid": "AllowDatabricksLakebaseEncryption",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::123456789:role/databricks-lakebase-cmk-role"
  },
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey",
    "kms:DescribeKey"
  ],
  "Resource": "*"
}
```

### Step 3, provide the key ARN to Databricks

Contact your Databricks workspace admin or account team with the key ARN. They'll configure the
workspace to use it. Once configured, all new Lakebase instances use the key.

## Setting up CMK on Azure Key Vault

### Step 1, create a key

In Azure Key Vault, create a key:

```
Key type: RSA or EC
Key size: 2048 or higher
Operations: Encrypt, Decrypt
```

Note the key URI (e.g., `https://my-vault.vault.azure.net/keys/my-key/version`).

### Step 2, grant Databricks managed identity

Grant the Databricks-provided managed identity (object ID) permission on the key:

```
Permissions: Get, Decrypt, Sign, Verify, WrapKey, UnwrapKey
```

### Step 3, provide the key URI to Databricks

Provide the key URI to your Databricks workspace admin to configure the workspace.

## Setting up CMK on GCP Cloud KMS

### Step 1, create a key

In GCP Cloud KMS, create a key:

```
Location: <your-workspace-region>
Key ring: create or select existing
Key type: Symmetric encryption (Google Cloud KMS)
Key rotation: annual (recommended)
```

Note the key resource ID (e.g., `projects/my-project/locations/us-central1/keyRings/my-ring/cryptoKeys/my-key`).

### Step 2, grant Databricks service account

Grant the Databricks-provided service account the following IAM roles:

- `roles/cloudkms.cryptoKeyEncrypter`
- `roles/cloudkms.cryptoKeyDecrypter`

### Step 3, provide the key resource ID to Databricks

Provide the key resource ID to your Databricks workspace admin.

## Testing CMK (after setup)

Once your workspace admin has configured CMK, you can test it without revoking keys. Connect to
a Lakebase instance using the CMK-enabled workspace:

```bash
python lakebase.py --sql "SELECT 1"
```

Queries run normally. The decryption happens in the background, calling your KMS. You won't see
the KMS call in normal operation.

### Testing: Monitor KMS audit logs

After running a query, check your KMS audit logs to confirm the Decrypt or GenerateDataKey API
was called:

- **AWS CloudTrail:** log in to AWS console, go to CloudTrail, filter for KMS API calls.
- **Azure Activity Log:** go to Activity Log in Azure portal, filter for Key Vault operations.
- **GCP Cloud Audit Logs:** use `gcloud logging read` to query audit logs.

You should see entries like `kms:Decrypt` or `GenerateDataKey` from the Lakebase service principal.

### Testing: Simulate key revocation (non-production only!)

If you have a test instance, you can test revocation without affecting production:

1. Create a test key (separate from your production key).
2. Configure the test instance to use the test key.
3. Create some data on the test instance.
4. In your KMS, disable or delete the test key.
5. Try to query the test instance. It should fail with a KMS permission error.

This confirms that revoking the key immediately stops Lakebase access.

## Rotating keys

### Automatic rotation

Configure automatic key rotation in your KMS (typically annual). Your KMS generates new key
versions; Lakebase picks them up automatically for new writes. Old data continues being decrypted
with the old key version until it's rewritten.

### Manual rotation

If you want to rotate immediately:

1. In your KMS, create a new key version (AWS KMS, GCP) or activate a new version (Azure).
2. Tell your Databricks account team or workspace admin to update the Lakebase workspace
   configuration to the new key version.
3. Lakebase uses the new key for new writes. Old data is gradually re-encrypted as it's
   compacted.

## Revoking keys (kill-switch)

To immediately stop all access to encrypted data:

1. In your KMS, disable or delete the key.
2. Lakebase instances encrypted with that key will fail on the next query with a KMS permission
   error.
3. To restore access, re-enable the key in your KMS.

Test this in a non-production environment first!

## Troubleshooting

### Queries fail with "KMS permission denied"

Check:
- Does the Databricks service role/identity still have permissions on the key in your KMS?
- Is the key enabled (not disabled or deleted)?
- Is the key in the same region as Lakebase?

### Decryption latency is high

Each decrypt call to your KMS adds a few milliseconds. If you see unusually high latency:
- Check KMS service health.
- Verify network connectivity between your Databricks deployment and your KMS.
- Consider enabling KMS caching (if your KMS provider supports it).

### Can't find CMK settings in workspace admin console

CMK is not available for all Databricks tiers or cloud providers. Confirm:
- Your workspace is Enterprise-tier.
- CMK is available in your cloud provider (GA on AWS/Azure, limited on GCP).
- Contact your Databricks account team for availability.

## Security best practices

- **Audit and log:** monitor KMS audit logs for access and rotations.
- **Least privilege:** limit who can manage keys in your KMS.
- **Automate rotation:** set up automatic key rotation in your KMS.
- **Test recovery:** periodically test key recovery scenarios (revoke and re-enable).
- **Document:** document your key management process and disaster recovery steps.
- **Separate keys for environments:** use different keys for dev, staging, and production.

## No runnable artifact

This journey is a configuration reference, not a runnable script. The setup is a one-time
workspace-admin task. Once configured, Lakebase works normally with CMK; the encryption and
decryption are transparent.

## Wrapping up

CMK gives you cryptographic control: your keys in your KMS, your rotation policy, your revocation
switch. For regulated industries, this is often a requirement. For others, it's a security best
practice. Once enabled, CMK is invisible to users; queries work the same way, but with the
confidence that your data is encrypted under your control.
