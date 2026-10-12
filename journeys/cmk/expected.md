# Customer-Managed Keys, expected results and references

This journey is a reference guide without runnable steps, so there is no "expected output" from
running a script. Instead, this page documents what you should expect to see when CMK is
configured and in use.

## What successful CMK setup looks like

### 1. Workspace configuration shows CMK enabled

If you have workspace admin access, the workspace settings should show CMK is configured:

```
Encryption: Customer-Managed Keys
KMS Key ARN/URI/ID: (visible to admins)
Key Rotation: Automatic (annual)
```

### 2. KMS audit logs show Decrypt/GenerateDataKey calls

After running a Lakebase query, check your cloud provider's [Key Management Service](../../docs/glossary.md) audit logs:

**AWS CloudTrail:**
```
Event: kms:Decrypt
Principal: arn:aws:iam::123456789:role/databricks-lakebase-cmk-role
Resource: arn:aws:kms:us-east-1:123456789:key/...
Result: Success
```

**Azure Activity Log:**
```
Operation: Decrypt (Microsoft.KeyVault/vaults/keys/decrypt/action)
Caller: databricks-managed-identity
Status: Succeeded
```

**GCP Cloud Audit Logs:**
```
protoPayload.methodName: cloudkms.projects.locations.keyRings.cryptoKeys.decrypt
actor.principalEmail: lakebase-sa@my-project.iam.gserviceaccount.com
status.code: 0 (success)
```

### 3. Queries run normally

From a user perspective, Lakebase works the same with CMK as with Databricks-managed keys:

```bash
python lakebase.py --sql "SELECT count(*) FROM bank.account"
```

Output:

```text
(45,)
```

No difference in latency or behavior (unless you're monitoring at sub-millisecond precision; CMK
adds a few ms for KMS calls).

### 4. Key rotation shows in audit logs

If you rotate a key, your KMS audit logs will show:

**AWS:**
```
Event: CreateGrant (new key version created)
Event: RetireGrant (old key version deprecated)
```

**Azure:**
```
Operation: Update (key properties modified)
```

**GCP:**
```
protoPayload.methodName: cloudkms.projects.locations.keyRings.cryptoKeys.versions.create
```

## What to expect after key revocation (kill-switch)

If you revoke/disable a CMK in your KMS and then try to query a Lakebase instance using that key,
you should see:

### Database connection succeeds, query fails

```bash
python lakebase.py --sql "SELECT 1"
```

Output:

```text
Error: KMS permission denied
Details: The KMS service denied access to the key.
```

Or a more specific error depending on your cloud provider:

**AWS:**
```
AccessDenied: User: arn:aws:iam::123456789:role/databricks-lakebase-cmk-role
is not authorized to perform: kms:Decrypt on resource: ...
```

**Azure:**
```
The key is disabled. (Keyvault.KeyDisabled)
```

**GCP:**
```
PERMISSION_DENIED: Permission denied on resource.
```

### Re-enabling the key restores access

Once you re-enable the key in your KMS, Lakebase queries resume working.

## Numbers that matter

| Aspect | Expected | Why it matters |
| ------ | -------- | -------------- |
| Decryption latency added | 5-50 ms per query | KMS call overhead; typically negligible |
| Key rotation overhead | zero | old key continues decrypting old data; new key used for new writes |
| Recovery time after key revocation | immediate | KMS denies access on the next decrypt attempt |
| Setup time (one-time) | 30-60 minutes | create key, set policies, configure workspace |

## Audit trail expectations

With CMK enabled, every decrypt operation is logged in your KMS audit logs. This creates a
complete audit trail of who accessed what data (at the KMS call level). Compare this to
Databricks-managed keys, where encrypt/decrypt operations are not visible to you.

## Cost implications

CMK itself has no additional Databricks charges, but cloud providers charge for KMS API calls:

- **AWS KMS:** $0.03 per 10,000 requests (roughly $0.000003 per request)
- **Azure Key Vault:** $0.03 per 10,000 requests
- **GCP Cloud KMS:** $0.06 per 10,000 requests

For a busy Lakebase instance running thousands of queries per day, expect $0.01-$0.10/month in
KMS charges. For most organizations, negligible compared to infrastructure costs.

## Verification checklist

After your workspace admin sets up CMK, verify:

- [ ] Workspace admin confirms CMK is configured in workspace settings.
- [ ] You can connect to a Lakebase instance and run queries.
- [ ] KMS audit logs show Decrypt operations from Lakebase's service role.
- [ ] You've tested key revocation in a non-production environment (optional, recommended).
- [ ] You understand your key rotation policy (automatic vs. manual).
- [ ] You know how to contact your account team if KMS access breaks.

## Next steps

After understanding CMK, consider:

1. **Implementing CMK in production:** work with your workspace admin and KMS team to roll out
   CMK to all production instances.
2. **Automating key rotation:** set up automatic annual key rotation in your KMS.
3. **Monitoring and alerting:** set up alerts for failed KMS operations in your cloud provider's
   monitoring dashboard.
4. **Compliance documentation:** document your key management process for audits and compliance.

## Related resources

- Databricks documentation: [Customer-Managed Keys for Encryption at Rest](https://docs.databricks.com/en/security/cmk.html) (link to official docs)
- AWS KMS documentation: https://docs.aws.amazon.com/kms/
- Azure Key Vault documentation: https://learn.microsoft.com/en-us/azure/key-vault/
- GCP Cloud KMS documentation: https://cloud.google.com/kms/docs
