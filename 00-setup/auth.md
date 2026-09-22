# 2 · Authenticate

The CLI and the Python SDK act as *you*. This step logs you in to your workspace and creates a
named **profile** the scripts use.

## Log in

Use the workspace host your instructor gave you (or your own). This opens a browser to complete
the login:

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

`--profile workshop` names this login. Every script in the workshop reads a profile name from
the `LB_PROFILE` environment variable, so pick a name and remember it.

## Confirm it worked

```bash
databricks auth profiles
```

```text
Name       Host                                          Valid
workshop   https://<your-workspace>.cloud.databricks.com  YES
```

And confirm the SDK can see you:

```bash
databricks current-user me --profile workshop
```

You should see your user record (your email, id). If you do, auth is good.

## Set your environment

The workshop scripts read a few environment variables. Set these now (you'll add `LB_PROJECT`
and `LB_BRANCH` in the next two steps):

```bash
export LB_PROFILE=workshop
export LB_SCHEMA=factory
```

> **Tip**
> Put these exports in a file you can re-source, for example `workshop.env`, then
> `source workshop.env` in each new terminal. You'll add two more lines to it shortly.

> **Warning**
> The login token expires, usually within an hour. When a CLI command or script fails with a
> "refresh token" or authentication error, that's all it is: re-run the `databricks auth login`
> command above and continue. This is the single most common hiccup in the workshop.

---

Next: [`provision.md`](provision.md) — get a Lakebase project to work in.
