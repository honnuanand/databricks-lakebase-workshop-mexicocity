# Row-level security, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, roles created

```text
role already exists: bu_retailbank      (or: created role: bu_retailbank)
role already exists: bu_globalmarkets   (or: created role: bu_globalmarkets)
granted schema/table SELECT and membership to all business unit roles
```

One role per business unit in the seed (RetailBank, GlobalMarkets). Roles are created silently; no
error means they exist. Each gets SELECT on `bank.account` and `bank.branch` (the policy reads
`bank.branch`), plus membership so you can `SET ROLE` into it.

## Step 2, row-level security policy enabled

```text
RLS enabled on bank.account
Policy created: account_bu_isolation
```

The policy is enabled and FORCEd (so even the table owner is filtered). Queries now apply the
filter automatically.

## Step 3, query with row-level security

```text
  as bu_retailbank (business unit RetailBank): 6 accounts, the SAME query:
    ('ACCT-100234', 'BR-NYC', 'good_standing')
    ('ACCT-100235', 'BR-NYC', 'good_standing')
    ('ACCT-100240', 'BR-NYC', 'watch')
    ('ACCT-100241', 'BR-NYC', 'good_standing')
    ('ACCT-200310', 'BR-SFO', 'good_standing')
    ('ACCT-200311', 'BR-SFO', 'frozen')

  as bu_globalmarkets (business unit GlobalMarkets): 2 accounts, the SAME query:
    ('ACCT-300420', 'BR-LON', 'good_standing')
    ('ACCT-300421', 'BR-LON', 'watch')
```

Same query (`SELECT account_id, branch_id, status FROM bank.account ORDER BY account_id`), but
different rows. The RetailBank role sees only RetailBank's branches (NYC, SFO); the GlobalMarkets
role sees only its branch (LON). The RLS policy is filtering automatically, driven by
`SET app.current_bu = '<business unit>'`.

## Step 4, query plan shows policy

```text
Seq Scan on account  (cost=0.00..15.00 rows=133 width=32)
  Filter: (health_pct > '50'::numeric)
```

The plan shows a `Filter` on the table scan. When the current business unit is set and the policy
is active, Postgres also folds the policy's `branch_id IN (...)` subquery into the plan; the filter
is added automatically, not by anything in your query.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| [RLS](../../docs/glossary.md) policy overhead | < 1 ms | negligible on queries; filtering is fast |
| Rows returned (same query, different role) | 6 vs 2 | row-level security works; isolation is enforced |
| Roles created | 2 (one per business unit) | each business unit has a role |
| Queries that see all rows | 0 (unless RLS is disabled) | no escape hatch; enforcement is universal (FORCE) |

> **From the field**
> [Row-level security](../../docs/glossary.md) is a trust boundary. It doesn't prevent a superuser from reading all rows (superusers bypass RLS unless the table is FORCEd), but it prevents ordinary application users from seeing rows outside their scope. In Lakebase, the app's Service Principal typically has full access (runs as a trusted identity), but end users see only their rows. Use it for multi-tenant SaaS, federated operations, and any scenario where business units or customers must not see each other's data.
