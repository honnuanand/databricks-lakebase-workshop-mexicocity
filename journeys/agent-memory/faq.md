# Agent memory, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired (they last about an hour). Re-run the login from
[`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env    # the file you built in 00-setup
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## The agent_memory table doesn't exist

The table is part of the factory schema, which is loaded during setup. If it's missing:

1. Check that you're on the right branch: `echo $LB_BRANCH`.
2. Check the schema loaded: `python lakebase.py --sql "SELECT count(*) FROM factory.machine"`.
3. If factory.machine exists but agent_memory doesn't, run the schema loader from setup:
   ```bash
   python load_factory.py
   ```

## The script failed calling the Foundation Model API

The FM API (Claude on Model Serving) requires:

1. **Endpoint exists**: `databricks serving-endpoints list --profile workshop` should show
   `databricks-claude-opus-4-8`. If not, create one (see setup).
2. **Workspace has permission**: Try a quick test:
   ```bash
   python lakebase.py --fm "Hello, world"  # not a real method; shows the error
   ```
3. **Model endpoint name matches**: The default is `databricks-claude-opus-4-8`. If you
   deployed it differently, pass `--fm-endpoint <name>` to the script.

If the FM API is not available, the script provides a fallback that simulates the agent
responses so you can see the memory flow without a live model call.

## One agent's response didn't appear

The script logs each agent's turn. If you see "no response" or a timeout, check:

1. **FM endpoint is serving**: `databricks serving-endpoints get --profile workshop --name databricks-claude-opus-4-8`.
2. **Network connectivity**: Try a simpler FM call from the Python REPL:
   ```python
   from lakebase import fm_call
   fm_call([{"role": "user", "content": "Hello"}])
   ```
3. **Agent deployment**: If using live agents (not the fallback), verify the endpoint is deployed:
   ```bash
   databricks serving-endpoints describe --name agents_<catalog>-<schema>-<agent> --profile workshop
   ```

## The agents aren't reading each other's memory

Each agent call does a fresh read from the `agent_memory` table at the start. If Agent B doesn't
see Agent A's prior response:

1. Check the table has the rows:
   ```bash
   python lakebase.py --sql "SELECT count(*) FROM factory.agent_memory"
   ```
2. Check the isolation: are you on the same branch for both calls? If you forked the branch
   between agent calls, Agent B would see a copy of Agent A's memory as of the fork point.
3. Check the memory schema: both agents must write to the same `namespace` and `session_id`.
   The script defaults to `('default', 'shift-001')`.

## Why does the table have namespace and session_id columns?

Real agent deployments often run multiple concurrent sessions or need to partition memory by
business unit. The table supports that:

- **namespace**: e.g., "factory-detroit", "factory-shanghai", multiple tenants or business
  units can have separate memory without sharing context.
- **session_id**: e.g., "shift-001", "shift-002", a maintenance shift can have its own
  context. When a shift ends, you can read-only archive that session.

For this journey, both default to sensible values (`"default"`, `"shift-001"`). You could
run multiple concurrent sessions by varying `session_id`.

## Can I use this with agents I deployed myself?

Yes, if your agents accept the memory table pattern:

1. Deploy an agent that reads from `factory.agent_memory` on startup.
2. Have it append user and assistant turns after each response.
3. Point the script at your agent's Model Serving endpoint (the script defaults to
   `databricks-claude-opus-4-8` for a simulated agent, or you can pass a custom endpoint).

The journey script is a minimal example; real agents would add error handling, timeouts, and
retry logic.

## I want to see what the raw memory table looks like

Query it directly:

```bash
python lakebase.py --sql \
  "SELECT id, agent_id, role, content, created_at FROM factory.agent_memory ORDER BY id"
```

Or export it as CSV:

```bash
psql -h <host> -U <user> -d databricks_postgres -c \
  "SELECT id, agent_id, role, content, created_at FROM factory.agent_memory" \
  --csv > agent_memory.csv
```

(You'll need the host and user from your branch's endpoint; `lakebase.py --sql` wraps that.)
