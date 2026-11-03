"""Checked Unity five-bit packed skin decoder.

UnityPy 1.25.4's fallback subtracts the integer sum from 1 for an implicit fourth
influence. The stored weights are thirty-firsts: the remainder is (31-sum)/31.
Keep this local to the data reader; do not patch or execute game code.
"""
import numpy as np
from UnityPy.helpers.PackedBitVector import unpack_ints
from .skinning import validate_weights


def decode(weights,bones,vertices,bone_count):
    wi=bi=0;out_i=np.zeros((vertices,4),dtype='<u2');out_w=np.zeros((vertices,4),dtype='<f4')
    for vertex in range(vertices):
        total=0
        for slot in range(4):
            if bi>=len(bones):raise ValueError('Truncated packed skin bone indices')
            index=int(bones[bi]);bi+=1
            if not 0<=index<bone_count:raise ValueError('Packed skin index outside native rig')
            out_i[vertex,slot]=index
            if slot==3:weight=31-total
            else:
                if wi>=len(weights):raise ValueError('Truncated packed skin weights')
                weight=int(weights[wi]);wi+=1
            if not 0<=weight<=31 or total+weight>31:raise ValueError('Invalid five-bit packed skin weight')
            out_w[vertex,slot]=weight/31;total+=weight
            if total==31:break
        if total!=31:raise ValueError('Packed skin weights do not sum to 31')
    if wi!=len(weights) or bi!=len(bones):raise ValueError('Packed skin stream contains unexpected trailing values')
    validate_weights(out_i,out_w,vertices,bone_count);return out_i,out_w


def read(mesh,handler):
    compressed=mesh.m_CompressedMesh
    if compressed.m_Weights.m_NumItems:
        return decode(unpack_ints(compressed.m_Weights),unpack_ints(compressed.m_BoneIndices),len(handler.m_Vertices),len(mesh.m_BindPose))
    indices=np.asarray(handler.m_BoneIndices);weights=np.asarray(handler.m_BoneWeights,dtype='<f4');validate_weights(indices,weights,len(handler.m_Vertices),len(mesh.m_BindPose));return indices,weights
