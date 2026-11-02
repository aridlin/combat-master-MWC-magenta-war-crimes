# Restore the current visual stack

Each layer stores exact source bundles, hashes and a build manifest. Keep these
local files: they are not included in Git. Deployment closes the identified
game executable and refuses unknown installed hashes.

Restore in this order, using the configurations and output directories from
the installed builds:

```sh
.venv/bin/python cat_audio.py restore
.venv/bin/python sight_customization.py restore
.venv/bin/python catgun_cli.py restore --config catgun.local.json
.venv/bin/python helicopter_windows.py restore
.venv/bin/python crate_colors.py restore
.venv/bin/python deploy_halftone.py restore
```

If installed with the default catgun.json instead, omit the cat --config option.
The first two affect weapon bundles; the helicopter and blue-crate layers share
src/src, so the helicopter layer must be removed first. The last command then
restores the preinstall state saved by the halftone deployer.

A lower-layer restoration may intentionally refuse while an upper layer is
installed. Remove the upper layer first, rather than editing hashes or forcing
replacement. Steam file verification is the independent way to restore original
Steam-delivered assets; these tools do not override integrity checks.
