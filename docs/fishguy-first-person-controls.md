# Fishguy first-person controls

The native wrist crease remains unresolved. No experimental geometry or skin
candidate from this investigation is enabled in production or installed. Ranger
remains the armored Grapple pilot; Fishguy remains an optional assignment.

Fresh native stationary range controls narrowed the next investigation. The
[capture hashes and exit results](fishguy-native-control-verification.json) are
recorded separately:

| Private control | Observed result |
|---|---|
| Unmodified native first-person bundle | Original glove and forearm render cleanly |
| Native mesh and weights through the custom mesh writer | Clean native arm; the writer alone does not reproduce the Fishguy crease |
| Fishguy with only LOD0 enabled | Wrist crease remains |
| Fishguy with only LOD1 enabled | Arms are absent in this tested scene; hiding the other LOD does not solve the visible LOD0 problem |
| Direct hand-controller → wrist-twist weight remap | Palm stretching confirmed in the native runtime; rejected |
| Post-radius harmonic transition | Fold remains; rejected |
| Uniform joint fitting and smaller hands | Fold remains; rejected |
| Native triangle-surface weight transfer | Palm improves, forearm crease remains; rejected |
| Harmonic weight-field smoothing | Crease remains; rejected |

These are bounded 1280×720 native Linux/Vulkan observations in a private guest
profile, with no network, host audio, player movement or weapon input. The original, writer-roundtrip and two LOD controls exited the game with code 0 and retained the host profile
hashes. Gamescope teardown separately returned 139; these runs do not establish
long-session stability, performance or animation acceptance.

The offline clip sampler also separates hands on an unmodified native glove
control. Its images therefore cannot establish correct runtime deformation.
See [the sampler limits](native-clip-review.md). Native observations narrow the
problem toward imported geometry/retargeting/skin fitting, but do not identify a
single proven cause. Full movement, ADS, reloads and helicopter views remain
unaccepted.
