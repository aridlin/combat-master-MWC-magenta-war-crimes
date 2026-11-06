# Independent Unity weight references

These are MWC-owned diagnostic data, not Combat Master meshes or replacement
models. The triangle has three vertices and eight simple reference transforms.
The project license covers these reference sources and outputs.

`MWCSkinReference.Generate()` ran in a separate Unity 6000.6.5f1 authoring
project. It called `Mesh.SetBoneWeights` with 1, 4 and 8 influences, saved the
binary `ReferenceWeights.asset`, and recorded API readback in
`unity-reference.json`. The JSON additionally includes the serialized packed
words independently extracted from that asset.

The Python writer then changed the distributions to 1, 5 and 7 influences.
`MWCSkinReadback.Run()` imported the resulting asset and recorded actual Unity
API values and CPU pose errors in `python-readback.json`. It compares
`BakeMesh` with independently multiplied bone/bind matrices and restores the
previous quality setting. Unlimited skinning missed by at most 1.1921e-7 m;
the deliberately capped four-weight control missed by 0.012891 m.

To repeat the live oracle, use a disposable authoring project, run `Generate`,
write the Python distributions used by
`test_python_authored_distributions_match_actual_editor_readback` into its
`ReferenceData/PythonWeights-binary.asset`, then run `Run`. Never load these
editor scripts into Combat Master. The checked-in tests compare against the
captured values without launching an Editor or changing a game installation.

Editor 6000.6 reference checks do not prove native-player 6000.3 behavior.
The separate private native controls and their limits are recorded in
[the investigation report](../../../docs/variable-skinning-investigation.md).
