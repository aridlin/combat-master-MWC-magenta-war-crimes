// Private serialization oracle only; this triangle is not a replacement model.
using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using Unity.Collections;

public static class MWCSkinReference
{
    [Serializable] public class Result
    {
        public string editorVersion;
        public int[] bonesPerVertex;
        public int[] boneIndices;
        public float[] weights;
        public float unlimitedBakeMaximumError;
        public float fourBoneBakeMaximumError;
        public bool referenceOnly = true;
    }

    public static string Generate()
    {
        const string folder = "Assets/MWC_SkinReference";
        const string asset = folder + "/ReferenceWeights.asset";
        if (AssetDatabase.LoadAssetAtPath<Mesh>(asset) != null)
            throw new InvalidOperationException("Refuse to overwrite an existing reference asset");
        AssetDatabase.CreateFolder("Assets", "MWC_SkinReference");
        var root = new GameObject("MWC private skin reference");
        var oldQuality = QualitySettings.skinWeights;
        try
        {
            var bones = new Transform[8];
            var bind = new Matrix4x4[8];
            for (int i = 0; i < bones.Length; i++)
            {
                bones[i] = new GameObject("ReferenceBone" + i).transform;
                bones[i].SetParent(root.transform, false);
                bones[i].localPosition = new Vector3(0, i * .1f, 0);
                bind[i] = bones[i].worldToLocalMatrix * root.transform.localToWorldMatrix;
            }
            var mesh = new Mesh { name = "MWC_1_4_8_influence_reference" };
            mesh.vertices = new[] { new Vector3(-1,0,0), new Vector3(0,1,0), new Vector3(1,0,0) };
            mesh.triangles = new[] { 0, 1, 2 };
            mesh.bindposes = bind;
            var counts = new NativeArray<byte>(new byte[] { 1, 4, 8 }, Allocator.Temp);
            var weights = new NativeArray<BoneWeight1>(13, Allocator.Temp);
            try
            {
                weights[0] = new BoneWeight1 { boneIndex = 0, weight = 1 };
                for (int i = 0; i < 4; i++)
                    weights[1+i] = new BoneWeight1 { boneIndex = i, weight = (4-i)/10f };
                for (int i = 0; i < 8; i++)
                    weights[5+i] = new BoneWeight1 { boneIndex = i, weight = (8-i)/36f };
                mesh.SetBoneWeights(counts, weights);
            }
            finally { weights.Dispose(); counts.Dispose(); }
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            var renderer = root.AddComponent<SkinnedMeshRenderer>();
            renderer.sharedMesh = mesh; renderer.bones = bones; renderer.rootBone = root.transform;
            renderer.quality = SkinQuality.Auto;
            var actualCounts = mesh.GetBonesPerVertex();
            var actualWeights = mesh.GetAllBoneWeights();
            var result = new Result { editorVersion = Application.unityVersion,
                bonesPerVertex = new int[3], boneIndices = new int[actualWeights.Length], weights = new float[actualWeights.Length] };
            for (int i=0; i<3; i++) result.bonesPerVertex[i]=actualCounts[i];
            for (int i=0; i<actualWeights.Length; i++)
            { result.boneIndices[i]=actualWeights[i].boneIndex; result.weights[i]=actualWeights[i].weight; }
            if (actualCounts.Length != 3 || actualCounts[0]!=1 || actualCounts[1]!=4 || actualCounts[2]!=8)
                throw new InvalidOperationException("Unity did not retain the reference influence counts");
            for (int i=0; i<bones.Length; i++)
                bones[i].localPosition += new Vector3(.03f*i, .01f*i, -.005f*i);
            Func<SkinWeights,float> bakeError = quality =>
            {
                QualitySettings.skinWeights = quality;
                var baked = new Mesh(); renderer.BakeMesh(baked, true);
                var original = mesh.vertices; var posed=baked.vertices; int cursor=0; float maximum=0;
                for (int v=0; v<original.Length; v++)
                {
                    Vector3 expected=Vector3.zero;
                    for (int j=0; j<actualCounts[v]; j++)
                    {
                        var weight=actualWeights[cursor++];
                        expected += (bones[weight.boneIndex].localToWorldMatrix * bind[weight.boneIndex]).MultiplyPoint3x4(original[v]) * weight.weight;
                    }
                    maximum=Math.Max(maximum,Vector3.Distance(expected,posed[v]));
                }
                UnityEngine.Object.DestroyImmediate(baked); return maximum;
            };
            result.unlimitedBakeMaximumError=bakeError(SkinWeights.Unlimited);
            result.fourBoneBakeMaximumError=bakeError(SkinWeights.FourBones);
            if (result.unlimitedBakeMaximumError > .0001f)
                throw new InvalidOperationException("Unlimited CPU bake missed independent weighted matrix result");
            EditorSettings.serializationMode=SerializationMode.ForceText;
            AssetDatabase.CreateAsset(mesh,asset); AssetDatabase.SaveAssets();
            string destination=Path.Combine(Directory.GetParent(Application.dataPath).FullName,"ReferenceData");Directory.CreateDirectory(destination);
            string sourcePath=Path.Combine(Application.dataPath,"MWC_SkinReference/ReferenceWeights.asset");
            File.Copy(sourcePath,Path.Combine(destination,"ReferenceWeights-text.asset"),false);
            EditorSettings.serializationMode=SerializationMode.ForceBinary;
            AssetDatabase.ForceReserializeAssets(new[] { asset }); AssetDatabase.SaveAssets();
            File.Copy(sourcePath,Path.Combine(destination,"ReferenceWeights-binary.asset"),false);
            string json=JsonUtility.ToJson(result,true);File.WriteAllText(Path.Combine(destination,"ReferenceWeights.json"),json);
            return json;
        }
        finally { QualitySettings.skinWeights=oldQuality; UnityEngine.Object.DestroyImmediate(root); }
    }

    public static string Inspect()
    {
        var mesh=AssetDatabase.LoadAssetAtPath<Mesh>("Assets/MWC_SkinReference/ReferenceWeights.asset");
        if(mesh==null)throw new InvalidOperationException("No reference mesh");
        var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();
        return "vertices="+mesh.vertexCount+" counts="+string.Join(",",counts.ToArray())+" weights="+weights.Length;
    }
}
