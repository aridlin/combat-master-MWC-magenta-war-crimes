# Offline review of shipped first-person clips

`operators.clip_review` samples the original game's generic transform curves
without launching the game or running any animation event, controller, script,
IK solver or network code. It is a diagnostic for authored model adaptation.
It does not change any installed asset or first-person animation.

Run from a private project workspace using its Python environment and verified
original backup bundle:

```sh
PYTHONPATH=public-repo .venv/bin/python -m operators.clip_review \
  --bundle /path/to/verified-original/src/first_person \
  --operator operator_0 --clip AK12_Arms_Idle --frame 0 \
  --output experiments/private-ak-idle-pose
```

The output must be fresh, outside the public source/package tree, and inside
the review workspace or an explicitly registered workspace-storage alias.
`pose.npz` contains renderer-local bone pose matrices and original inverse-bind
matrices; `review.json` records the original bundle hash, clip, frame, resolved
binding counts and limitations. These exports contain private native game data;
do not redistribute them or add them to an installer/repository.

The reader supports the reviewed nonlegacy, uncompressed generic clip layout:
streamed cubic channels, dense samples at their exact sample frames, constant
channels, transform position/quaternion/Euler/scale bindings, and unique CRC32
path resolution within the selected native prefab. Euler conversion uses
Unity's documented Z-X-Y rotation order. Missing or ambiguous hashes,
unsupported/discrete/object bindings, malformed channel lengths and
intermediate dense-frame times fail explicitly. Original renderer hashes are
checked against the project's reviewed first-person target index.

Seven known Animator root channels are consumed and reported, not applied as
runtime root motion. Event counts are reported without invoking any event.
Actual runtime animation blending, procedural viewmodel placement, IK, camera
FOV and material/lighting behavior remain outside this sampler. An offline
render of sampled geometry is not an in-game screenshot or animation acceptance.

The original first-person bundle contains 1,520 clips. An initial-frame sweep
sampled 1,490 on the Ranger hierarchy and explicitly rejected 30 unresolved or
unsupported cases. This checks only one frame per clip, not full animations.
The initial AK12 idle
inspection resolved all 237 transform bindings on the native Ranger hierarchy;
seven separate Animator root channels were reported. CPU comparisons using
idle, ADS and a reload frame showed palm/finger stretching in the private
hand-control-to-wrist-driver remap. The candidate was kept out of production.
A later review also found hand separation on the **unmodified original native
glove control** in these offline samples. Consequently, these images cannot
settle whether the driver mapping is correct at runtime. The exact cause of
the control discrepancy is unresolved; native animation layers, procedural
transforms and IK are not reproduced. A fresh bounded native range comparison
subsequently confirmed palm stretching in that direct-remap candidate, so it
remains rejected. That native result does not make the offline sampler a
validated deformation predictor. The earlier 928 numerical fits did not establish visual
quality. A separate nearest-native-hand-weight experiment also remains private
and unaccepted. Installed models and their original animation assets are
unchanged.

The existing `operators.native_weights.read` decoder must be used when reading
compressed native glove skin. The project's checked five-bit reader already
handles the implicit fourth influence; the UnityPy fallback in the inspected
version can produce negative fourth weights. No third-party package or game
binary is patched for this diagnostic.

Format and convention references:

- [AssetStudio's original AnimationClip layout](https://github.com/Perfare/AssetStudio/blob/master/AssetStudio/Classes/AnimationClip.cs)
- [AssetStudio's generic binding and path resolution](https://github.com/Perfare/AssetStudio/blob/master/AssetStudioUtility/ModelConverter.cs)
- [Unity 6 Quaternion.Euler](https://docs.unity.com/en-us/engine/6000.3/script-reference/unityengine/quaternion/euler)
- [AssetStudio's five-bit skin format](https://github.com/Perfare/AssetStudio/blob/master/AssetStudio/Classes/Mesh.cs)

The sampler is an independent, scoped data reader. It does not bundle native
clips, skeletons, meshes or any external tooling.
