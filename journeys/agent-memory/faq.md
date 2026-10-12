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

The table is part of the bank schema, which is loaded during setup. If it's missing:

1. Check that you're on the right branch: `echo $LB_BRANCH`.
2. Check the schema loaded: `python lakebase.py --sql "SELECT count(*) FROM bank.account"`.
3. If bank.account exists but agent_memory doesn't, run the schema loader from setup:
   ```bash
   python load_bank.py
   ```

## The script failed calling the Foundation Model API

The FM API (Claude on Model Serving) requires:

1. **Endpoint exists**: `databricks serving-endpoints list --profile workshop` should show
   `databricks-claude-opus-4-8`. If not, create one (see setup).
2. **Workspace has permission**: the script authenticates as the app/user service principal and
   calls the endpoint directly. A 403 usually means the SP lacks access to the model endpoint.
3. **Model endpoint name matches**: the default is `databricks-claude-opus-4-8`. If you deployed
   it differently, set `FM_ENDPOINT=<name>` in your environment before running the script.

If the FM API is not available, the script provides a fallback that simulates the agent
responses so you can see the memory flow without a live model call. You'll see a
`(FM API unavailable: ...; using fallback simulation)` line, and the story still runs.

## One agent's response didn't appear

The script logs each agent's turn. If you see "no response" or a timeout, check:

1. **FM endpoint is serving**: `databricks serving-endpoints get --profile workshop --name databricks-claude-opus-4-8`.
2. **Network connectivity**: try a simpler FM call from the Python REPL:
   ```python
   from agent_memory import _fm_call
   print(_fm_call([{"role": "user", "content": "Hello"}]))
   ```
3. **Agent deployment**: if using live agents (not the fallback), verify the endpoint is deployed:
   ```bash
   databricks serving-endpoints get --name <your-agent-endpoint> --profile workshop
   ```

## The agents aren't reading each other's memory

Each agent call does a fresh read from the `agent_memory` table at the start. If the ops
assistant doesn't see the fraud advisor's prior response:

1. Check the table has the rows:
   ```bash
   python lakebase.py --sql "SELECT count(*) FROM bank.agent_memory"
   ```
2. Check the isolation: are you on the same branch for both calls? If you forked the branch
   between agent calls, the second agent would see a copy of the first agent's memory as of
   the fork point.
3. Check the memory scope: both agents must write to the same `namespace` and `session_id`.
   The script defaults to `('default', 'sess-01')`.

## Why does the table have namespace and session_id columns?

Real agent deployments often run multiple concurrent sessions or need to partition memory by
line of business. The table supports that:

- **namespace**: e.g., "retail-bank", "global-markets", multiple business units can keep
  separate memory without sharing context.
- **session_id**: e.g., "sess-01", "sess-02", a single investigation or alert queue can have
  its own context. When a case closes, you can read-only archive that session.

For this journey, both default to sensible values (`"default"`, `"sess-01"`). You could run
multiple concurrent investigations by varying `session_id`.

## Can I use this with agents I deployed myself?

Yes, if your agents accept the memory table pattern:

1. Deploy an agent that reads from `bank.agent_memory` on startup.
2. Have it append user and assistant turns after each response.
3. Point the script at your agent's Model Serving endpoint by setting `FM_ENDPOINT=<name>`
   (the script defaults to `databricks-claude-opus-4-8` for a simulated agent).

The journey script is a minimal example; real agents would add error handling, timeouts, and
retry logic.

## I want to see what the raw memory table looks like

Query it directly:

```bash
python lakebase.py --sql \
  "SELECT id, agent_id, role, content, created_at FROM bank.agent_memory ORDER BY id"
```

Or export it as CSV through the helper:

```bash
python lakebase.py --sql \
  "SELECT id, agent_id, role, content, created_at FROM bank.agent_memory ORDER BY id" > agent_memory.txt
```

The `lakebase.py --sql` wrapper handles the host, user, and OAuth credential for your branch,
so you don't have to assemble a raw `psql` connection string.
