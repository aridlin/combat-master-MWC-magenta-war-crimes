# Keeping large build artifacts on another disk

The staging CLI normally confines output to its current workspace. A workspace
can explicitly register directory links to another disk in `.mwc-storage.json`:

```json
{
  "version": 1,
  "workspace": "/home/me/mwc",
  "mounts": [
    {"alias": "experiments", "target": "/mnt/archive/mwc/experiments"}
  ]
}
```

The alias must be a relative path inside that workspace and an existing symbolic
link to the declared absolute target. Both the workspace alias (for example
`experiments/new-review`) and its resolved registered target are accepted, so
subsequent pipeline steps can reuse validated paths. Nested links escaping the
registered target remain rejected. Steam bundle paths remain forbidden.

Copy and hash-verify originals and generated data before replacing a directory
with a link. Keep the archive mounted for installer originals, rollback history
and archived reviews. Source code, tools and reports can stay on the fast disk.
