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
path resolution within the selected native prefab. The reviewed packed Euler
curves use XYZ order (`Rz @ Ry @ Rx` for column vectors). This differs from
the ZXY order of the usual `Quaternion.Euler` API; that API's convention must
not be substituted for the clip format. Missing or ambiguous hashes,
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
The initial implementation also separated hands on the **unmodified original
native glove control**. That discrepancy was subsequently traced to its wrong
Euler order and corrected as described below. A fresh bounded native range comparison
subsequently confirmed palm stretching in that direct-remap candidate, so it
remains rejected; correcting the diagnostic does not overturn that native
rejection. The earlier 928 numerical fits did not establish visual
quality. A separate nearest-native-hand-weight experiment also remains private
and unaccepted. Installed models and their original animation assets are
unchanged.

## Native Avatar comparison and Euler correction

The original first-person clips were loaded as data through Unity's standard
AssetBundle API into a private Editor project. An owned transform-only hierarchy
and built-in Animator/AnimationClipPlayable evaluated the original
`Hands_SkinnedAvatar`. No game MonoBehaviour, animation event, game controller,
network code or runtime IK was executed. Importing standalone cooked clips
through AssetDatabase and calling `SampleAnimation` produced zero motion and
were explicitly excluded from the comparison.

Six clips were sampled at 0, 0.5 and 1 seconds: AK12 idle, ADS and reload;
Kar98k idle and reload; and Dual1911 ADS. The corrected public sampler matched
the Editor across 36 renderer poses and 2,880 bone matrices. Maximum bone
position error was 0.000000762 m; maximum matrix-element error was
0.000001794. The former ZXY conversion did not match mixed-axis rotations.
An independent, entirely owned mixed-axis `quaternion.EulerXYZ` reference is
included in the regression test; no game clips or pose matrices are published.
[Counts, hashes and limitations](native-clip-euler-verification.json) accompany
the comparison.

![Original gloves under the corrected isolated ADS clip](screenshots/native-glove-corrected-offline-ads-nov6.png)

Both corrected idle and ADS control renders have connected native wrists in
the inspected view. Fishguy's current authored arms still show a sharp wrist
transition under the same isolated poses. These renders use geometric normals
and a studio camera; they are offline diagnostic renders, **not native game
screenshots**. This establishes a useful isolated-clip control, not full
animation, grip, skinning-quality, camera or runtime-layer acceptance.

The authoring Editor was 6000.6.5f1; the game is 6000.3.19f1. The first private
Editor later crashed with code 139; the second produced the extended corpus
and subsequently terminated with code 143. Neither run establishes long-session
Editor stability. These terminal results do not alter the recorded numerical
comparison or justify installing a rejected wrist candidate. The production
model fitter, installer and installed game were unchanged by this correction.

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
