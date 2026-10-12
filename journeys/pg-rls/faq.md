# Row-level security, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env
```

## "table bank.account does not exist"

The factory schema was not loaded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step.

## Row-level security is enabled but queries still return all rows

Check that the session variable is set. If the script doesn't set `app.current_operator_plant`, the [row-level security](../../docs/glossary.md) policy reads NULL (or a default), and rows aren't filtered. The script must set the variable before running the query:

```sql
SET app.current_operator_plant = 'BR-NYC';
SELECT * FROM bank.account;
```

## Can I use RLS with JOINS?

Yes. The RLS policy applies to the table it's defined on. If you join account and work_order, both tables must have compatible policies, or the policy on one table applies:

```sql
SELECT m.account_id, w.trade_id
  FROM bank.account m
  JOIN bank.trade w ON m.branch_id = w.branch_id
 WHERE m.branch_id = current_setting('app.current_operator_plant');
```

The filter on machine propagates (machine.branch_id restricted) but work_order rows are unfiltered unless work_order also has an RLS policy on branch_id.

## What if I want column-level masking, not just row-level?

RLS is row-level. For column-level masking (hiding a sensitive field from certain roles), you need a different approach:

```sql
CREATE VIEW machine_for_operators AS
SELECT account_id, branch_id, status,
       CASE WHEN current_user = 'admin' THEN health_pct ELSE NULL END as health_pct
  FROM bank.account;
```

Then grant SELECT on the view to operators, and revoke SELECT on the underlying table. This works but is less flexible than RLS. For stronger masking, use a view + RLS together.

## Row-level security bypassed, superuser sees all rows. Is this a security hole?

No, it's by design. Superusers (and Postgres roles with BYPASSRLS) can see all rows and bypass row-level security. In Lakebase, the branch owner is a superuser-equivalent. For application users, grant normal privileges (no BYPASSRLS) and assign them a role with an RLS policy. Those users cannot bypass row-level security.

## Can I test row-level security without creating multiple roles?

Yes, use `SET ROLE` to switch identities within the same connection (if you're a superuser):

```sql
SET ROLE operator_detroit;
SELECT * FROM bank.account;  -- sees only Detroit rows

SET ROLE operator_chicago;
SELECT * FROM bank.account;  -- sees only Chicago rows

RESET ROLE;
```

This is how the script tests row-level security without creating separate connections. (With separate connections, you'd need to authenticate as each role, which is more complex.)

## How do I update the row-level security policy?

Drop and recreate:

```sql
DROP POLICY machine_operator_isolation ON bank.account;
CREATE POLICY machine_operator_isolation ON bank.account
  FOR SELECT
  USING (branch_id = current_setting('app.current_operator_plant'));
```

Or modify the policy directly (Postgres 13+):

```sql
ALTER POLICY machine_operator_isolation ON bank.account
  USING (branch_id = current_setting('app.current_operator_plant'));
```

## Can RLS prevent INSERT/UPDATE/DELETE, not just SELECT?

Yes. You can have separate policies for each operation:

```sql
CREATE POLICY machine_select ON bank.account FOR SELECT
  USING (branch_id = current_setting('app.current_operator_plant'));

CREATE POLICY machine_update ON bank.account FOR UPDATE
  USING (branch_id = current_setting('app.current_operator_plant'))
  WITH CHECK (branch_id = current_setting('app.current_operator_plant'));

CREATE POLICY machine_delete ON bank.account FOR DELETE
  USING (branch_id = current_setting('app.current_operator_plant'));
```

The `WITH CHECK` clause on UPDATE and INSERT ensures the new row also satisfies the policy.

## Does RLS work with views?

Yes, but with caveats. The RLS policy applies to the underlying table, not the view. If the view does complex joins, make sure the RLS policy is correctly inherited by all joined tables. Test with EXPLAIN to verify.
