# Row-level security, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, roles created

```text
CREATE ROLE operator_detroit;
CREATE ROLE operator_chicago;
CREATE ROLE operator_toronto;
GRANT ...
```

Roles are created silently. No error means they exist.

## Step 2, row-level security policy enabled

```text
ALTER TABLE bank.account ENABLE ROW LEVEL SECURITY;
CREATE POLICY machine_operator_isolation ON bank.account ...
```

The policy is created. Queries now apply the filter automatically.

## Step 3, query with row-level security

```text
=== Connected as operator_detroit ===
account_id  branch_id  status  health_pct
ACCT-100240       BR-NYC  healthy  91.00
M-301       BR-NYC  derated   89.75

=== Connected as operator_chicago ===
account_id  branch_id  status  health_pct
M-401       PL-CHICAGO  healthy  95.50
M-405       PL-CHICAGO  down     45.25
```

Same query (`SELECT * FROM account`), but different rows. Detroit operator sees only Detroit machines; Chicago operator sees only Chicago machines. The RLS policy is filtering automatically.

## Step 4, query plan shows policy

```text
Seq Scan on machine  (cost=0.00..23.50 rows=2 width=100)
  Filter: (branch_id = 'BR-NYC'::text)
```

The plan includes `Filter: (branch_id = <value>)`, showing the RLS policy is applied. The filter is added automatically by Postgres.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| [RLS](../../docs/glossary.md) policy overhead | < 1 ms | negligible on queries; filtering is fast |
| Rows returned (same query, different role) | different | row-level security works; isolation is enforced |
| Roles created | 3 (one per plant) | each operator has a role |
| Queries that see all rows | 0 (unless RLS is disabled) | no escape hatch; enforcement is universal |

> **From the field**
> [Row-level security](../../docs/glossary.md) is a trust boundary. It doesn't prevent a superuser from reading all rows (superusers bypass RLS), but it prevents ordinary application users from seeing rows outside their scope. In Lakebase, the app's Service Principal typically has full access (runs as a trusted identity), but end users see only their rows. Use it for multi-tenant SaaS, federated operations, and any scenario where users must not see each other's data.
