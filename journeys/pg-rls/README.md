# Row-level security

> ## What you'll learn
>
> **Key takeaways**
>
> - Row-level security (RLS) is a policy on the database table itself. Every query automatically filters rows based on the policy, the same query returns different data for different users.
> - The policy is enforced at the database layer, so even a forgotten filter in the app can't leak data. A user asking for "show me all machines" gets only their plant's machines, always.
> - The numbers that matter: RLS overhead is negligible (< 1 millisecond per query on thousands of rows). Multi-tenant isolation is database-native, no app logic needed.
>
> **You'll be able to:** set up RLS so multiple plants/operators share the machine table, but each sees only their own rows. The same query, different results, enforced by Postgres itself.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

Three plants, Detroit, Chicago, Toronto, each operated by a different team. They share a central database for reporting and scheduling. But Detroit's operators must not see Chicago's machine health data, and vice versa. The traditional approach: add a filter to every query. But filters get forgotten, copy-pasted wrong, bypassed.

Row-level security flips it: the database itself enforces the boundary. A query that says "SELECT * FROM machine" automatically returns only the requester's plant's machines. No app logic, no forgotten filter, no escape hatch.

## Why RLS matters

Multi-tenancy is the norm now. Every SaaS has multiple customers sharing infrastructure. RLS lets you build true database-level tenancy: the database physically refuses to return rows outside a user's tenant, regardless of query. This is stronger than any app-layer access control, it's a database-enforced guarantee.

## The wow moment

You set up an RLS policy on the machine table scoped by plant. Then you connect as two different operators (different Postgres roles), run the same query, and get different results. The query is identical; the policy changes the result set. You prove it works by switching between roles and running EXPLAIN to confirm the policy is being applied.

## What you'll do

1. Create Postgres roles for each plant operator (or app) and assign them to users.
2. Create an RLS policy on the machine table: restrict to rows where plant_id matches current_user_id.
3. Enable RLS on the machine table.
4. Connect as different operators and run the same query, verify the results differ.
5. Optionally, add column-level masking or encryption for sensitive fields.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the factory schema loaded. You need to be able to create roles and policies (typically available to the branch owner).

## Wrapping up

Row-level security transforms how you think about access control. Instead of trusting queries to filter correctly, you trust the database to enforce boundaries. The next journey explores a different kind of database guarantee: [No double-booking](../pg-booking/), using exclusion constraints to prevent overlapping reservations at the database layer.
