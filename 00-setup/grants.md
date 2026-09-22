# 4 · Grants

Whether you need to do anything here depends on how you got your project.

## If you provisioned your own project (Path B)

You're the owner. You already have the access to create branches and run SQL, so there is
**nothing to do here.** Continue to [`your-branch.md`](your-branch.md).

## If you're using a shared project (Path A)

You need two things to run the workshop on your own branch:

1. **Permission to create branches** on the project (`CAN_MANAGE` on the project).
2. **A Postgres role** so you can connect to the branches you create.

In a group workshop the instructor grants these for the whole room in one step, so usually
**you don't run anything here** either. Confirm you can branch by continuing to
[`your-branch.md`](your-branch.md); if branch creation fails with a permission error, come back
here and send your instructor the section below.

## For instructors: granting the room

Grant each participant (or a shared workshop group) `CAN_MANAGE` on the project so they can
branch, and make sure their identity can connect to Postgres. The permission that authorizes
branching lives on the **project**, not the instance:

```bash
# CAN_MANAGE on the project (authorizes create_branch)
databricks permissions update database-projects "$LB_PROJECT" \
  --profile "$LB_PROFILE" --json '{
    "access_control_list": [
      {"group_name": "workshop-participants", "permission_level": "CAN_MANAGE"}
    ]
  }'
```

> **Note**
> This is the learner path: each person authenticates as themselves over OAuth, so they connect
> to branches with their own Databricks identity. The heavier grant chain (creating a dedicated
> Postgres **role** for a **service principal**, stamping the `databricks_auth` security label,
> schema grants, and a role on the production branch) is needed when an **application's** service
> principal must connect, not a person. You'll meet that in the [capstone](../journeys/capstone-app/),
> where you put an app on Lakebase. For running the journeys as yourself, project `CAN_MANAGE`
> plus your own identity is enough.

---

Next: [`your-branch.md`](your-branch.md) — create your personal branch.
