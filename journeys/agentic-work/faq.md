# The agent does the work, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the script.

## "Missing required env var LB_PROJECT / LB_BRANCH"

Re-source your environment:

```bash
source workshop.env
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## The operation row already exists (from a prior run)

The script is idempotent: it checks the agent's memory before assigning. If you see "already
assigned" on the first run, it means a prior run left data behind. Clean up:

```bash
python lakebase.py --sql "DELETE FROM factory.operation WHERE wo_id='WO-1001'"
python lakebase.py --sql "DELETE FROM factory.agent_memory WHERE namespace='default' AND content LIKE '%WO-1001%'"
```

Then re-run the script.

## The agent didn't call any tools

If you see "no tool calls" in the output, the agent prompt may have been misinterpreted. Check:

1. **Fallback simulation**: The script falls back to simulating tool calls if the FM API
   is unavailable. Check if the FM endpoint is running:
   ```bash
   databricks serving-endpoints list --profile workshop | grep claude
   ```
2. **Model response parsing**: The script expects Claude to return a `<tool_name>` and
   `<tool_input>` block. If Claude's response format changed, the parser might not recognize it.
   Look for "parse failed" in the output.

## The tool call succeeded but the row didn't insert

If you see "tool call: assign_work_order OK" but the operation table is still empty, check:

1. **Are you querying the right table?** Run:
   ```bash
   python lakebase.py --sql "SELECT count(*) FROM factory.operation"
   ```
   If the count changed, the insert worked but maybe with a different wo_id or machine_id.

2. **Check the agent's SQL**: The script runs:
   ```sql
   INSERT INTO factory.operation (op_id, wo_id, machine_id, seq, status)
   VALUES ('OP-' || gen_random_uuid()::text, 'WO-1001', 'M-204', 1, 'pending')
   ```
   If that failed (e.g., foreign key violation), the operation table would be unchanged. Look
   for an error in the script's debug output.

3. **Branch isolation**: If you're on a different branch than when the agent ran, you'd see
   different data. Confirm your branch: `echo $LB_BRANCH`.

## The second release didn't refuse; it assigned again

If you called the script twice and both times saw "assigned", the memory table might not be
keeping the agent's log. Check:

```bash
python lakebase.py --sql \
  "SELECT agent_id, content FROM factory.agent_memory WHERE namespace='default'"
```

You should see rows from both calls. If not, the agent's memory table is on a different
schema or branch. Confirm `$LB_SCHEMA` (default: `factory`).

## I want to use a different work order or machine

The script hardcodes `WO-1001` and `M-204`. To use different values, edit the script or pass
them as arguments (not currently supported; you'd need to modify the script):

1. Open `agentic_work.py`.
2. Change these lines:
   ```python
   WO_ID = "WO-1001"
   MACHINE_ID = "M-204"
   ```
3. Re-run.

Or manually run the tool calls:

```bash
python lakebase.py --sql \
  "SELECT machine_id, status FROM factory.machine WHERE status='healthy' LIMIT 5"

python lakebase.py --sql \
  "INSERT INTO factory.operation (op_id, wo_id, machine_id, seq, status) \
   VALUES (gen_random_uuid()::text, 'WO-XXXX', 'M-YYYY', 1, 'pending')"
```

## Can I test this with my own agent?

Yes, if your agent supports a tool-calling pattern:

1. Deploy an agent that accepts a `release_work_order` tool.
2. Have it accept `wo_id` and `machine_id` as arguments.
3. Have it call a `get_free_machines` tool to read the machine table.
4. Point the script at your Model Serving endpoint (edit `FM_ENDPOINT` in the script or pass
   `--fm-endpoint <name>`).

The journey script is a minimal example; production agents would add error handling, retries,
and transaction isolation.

## Why does the operation table have an auto-generated ID (op_id)?

The `operation` table tracks routing steps of a work order. Each operation is one step. WO-1001
might have operations on M-204 (press), M-205 (another press), and M-311 (CNC). The op_id
is unique per operation. A single work order can have multiple operation rows. The script
generates one operation per release.
