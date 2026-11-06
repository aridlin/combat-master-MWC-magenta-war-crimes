"""Fit distal finger segments to the actual native fingertip surface.

A leaf joint has no child joint to define its direction. Use an explicit authored
end bone where available, otherwise the distal cap of the authored skin. Native
endpoints come from native geometry, preserving its full 3D direction.
Only native-reviewed first-person model paths opt into this fit.
"""
import numpy as np
from UnityPy.helpers.MeshHelper import MeshHandler
from .native_weights import read

REVIEWED_MODELS = frozenset({
    'fishguy', 'tf2_scout', 'tf2_soldier', 'tf2_pyro', 'tf2_demoman',
    'tf2_heavy', 'tf2_engineer', 'tf2_medic', 'tf2_sniper', 'tf2_spy',
})
FINGERS = ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky')


def cap(vertices, indices, weights, bone, joint, axis=None):
    """Find the weighted centroid of a leaf's outermost 15% of skin points."""
    vertices = np.asarray(vertices)
    indices, weights, joint = map(np.asarray, (indices, weights, joint))
    if (vertices.ndim != 2 or vertices.shape[1] != 3
            or not np.isfinite(vertices).all() or joint.shape != (3,)
            or not np.isfinite(joint).all()):
        raise ValueError('Invalid fingertip geometry')
    if (indices.shape != weights.shape or indices.ndim != 2
            or len(indices) != len(vertices) or not np.isfinite(weights).all()
            or np.any(weights < 0)):
        raise ValueError('Invalid fingertip skin field')
    mass = np.where(indices == bone, weights, 0).sum(1)
    delta = vertices - joint
    distance = np.linalg.norm(delta, axis=1)
    take = mass > .5
    if axis is not None:
        take &= (delta @ axis) > 0
    if take.sum() < 3:
        raise ValueError('Insufficient authored/native leaf support')
    selected = take & (distance >= np.quantile(distance[take], .85))
    if selected.sum() < 3:
        raise ValueError('Insufficient distal cap vertices')
    point = np.average(vertices[selected], axis=0, weights=mass[selected])
    if not np.isfinite(point).all() or np.linalg.norm(point - joint) < 1e-6:
        raise ValueError('Degenerate distal cap')
    return point, int(selected.sum())


def tips(base, source_indices, source_weights, source_bind, native, options):
    """Return explicit source/native endpoints in their original mesh frames."""
    from .first_person import native_name
    primary = options['primary_sources']
    source_joints = np.linalg.inv(source_bind)[:, :3, 3]
    native_joints = np.linalg.inv(native['inverse_bind'])[:, :3, 3]
    native_index = {native_name(n): i for i, n in enumerate(native['bone_names'])}
    obj = native['mesh_object'].read()
    handler = MeshHandler(obj)
    handler.process()
    vertices = np.asarray(handler.m_Vertices)
    indices, weights = read(obj, handler)
    source = np.asarray(base.vertices)
    source_indices, source_weights = map(np.asarray, (source_indices, source_weights))

    # Material atlases duplicate triangle corners. Count each authored point
    # once for the source cap, checking its skin field before deduplication.
    if any(finger + 'Finger4_' + side not in primary
           for side in ('L', 'R') for finger in FINGERS):
        _, first, labels = np.unique(np.round(source, 7), axis=0,
                                    return_index=True, return_inverse=True)
        field = np.zeros((len(source), len(source_bind)))
        for slot in range(source_indices.shape[1]):
            np.add.at(field, (np.arange(len(source)), source_indices[:, slot]),
                      source_weights[:, slot])
        if np.max(np.abs(field - field[first[labels]])) > 1e-5:
            raise ValueError('Ambiguous authored skin field at coincident points')
        source, source_indices, source_weights = (source[first],
                                                  source_indices[first],
                                                  source_weights[first])

    result = {}
    for side in ('L', 'R'):
        for finger in FINGERS:
            key = finger + 'Finger3_' + side
            previous = finger + 'Finger2_' + side
            tip = finger + 'Finger4_' + side
            bone = native_index[key]
            joint = native_joints[bone]
            axis = joint - native_joints[native_index[previous]]
            if np.linalg.norm(axis) < 1e-6:
                raise ValueError('Degenerate native finger axis')
            axis /= np.linalg.norm(axis)
            target, support = cap(vertices, indices, weights, bone, joint, axis)
            if not .003 < np.linalg.norm(target - joint) < .06:
                raise ValueError('Unreviewed native fingertip length')
            if tip in primary:
                point, tip_index = source_joints[primary[tip]], primary[tip]
                source_support, method = None, 'explicit authored tip bone'
            else:
                point, source_support = cap(source, source_indices, source_weights,
                                            primary[key], source_joints[primary[key]])
                tip_index, method = -1, 'authored distal mesh cap'
            result[primary[key]] = {
                'source': point.tolist(), 'target': target.tolist(),
                'tip_index': tip_index, 'name': key,
                'native_support_vertices': support,
                'source_support_vertices': source_support,
                'source_method': method,
                'target_method': 'full 3D native distal mesh cap',
            }
    return result
