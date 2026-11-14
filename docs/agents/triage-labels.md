# Triage Labels

The installed `mattpocock-skills` workflows speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's GitHub issue tracker (applied via `gh issue edit` per [`issue-tracker.md`](issue-tracker.md)).

| Label in `mattpocock-skills` | Label in our tracker | Meaning                                  |
| ---------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`               | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`                 | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                    | `wontfix`            | Will not be actioned                     |

When an Antigravity (AGY) CLI skill mentions a role (e.g., "apply the AFK-ready triage label"), apply the corresponding label string from this table with `gh issue edit <number> --add-label "<label>"`.

Edit the "Label in our tracker" column if this repository adopts custom GitHub label names.
