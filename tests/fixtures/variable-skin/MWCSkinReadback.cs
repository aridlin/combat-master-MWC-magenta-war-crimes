// Runs only in the private authoring Editor, never in Combat Master.
using System;
using System.IO;
using UnityEngine;
using UnityEditor;

public static class MWCSkinReadback
{
    public static string Run()
    {
        const string asset="Assets/MWC_SkinReference/PythonWeights.asset";
        string folder=Path.Combine(Directory.GetParent(Application.dataPath).FullName,"ReferenceData");
        if(File.Exists(Path.Combine(Application.dataPath,"MWC_SkinReference/PythonWeights.asset")))
            throw new InvalidOperationException("Refuse to overwrite an existing imported reference");
        File.Copy(Path.Combine(folder,"PythonWeights-binary.asset"),Path.Combine(Application.dataPath,"MWC_SkinReference/PythonWeights.asset"),false);
        AssetDatabase.ImportAsset(asset,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);
        var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(asset);
        if(mesh==null)throw new InvalidOperationException("Unity did not load the Python-authored reference");
        var counts=mesh.GetBonesPerVertex();var weights=mesh.GetAllBoneWeights();
        if(counts.Length!=3||counts[0]!=1||counts[1]!=5||counts[2]!=7)
            throw new InvalidOperationException("Unity lost a variable-weight row");
        var result=new MWCSkinReference.Result { editorVersion=Application.unityVersion,
            bonesPerVertex=new int[3],boneIndices=new int[weights.Length],weights=new float[weights.Length] };
        for(int v=0;v<3;v++)result.bonesPerVertex[v]=counts[v];
        for(int i=0;i<weights.Length;i++){result.boneIndices[i]=weights[i].boneIndex;result.weights[i]=weights[i].weight;}
        var root=new GameObject("MWC Python skin readback");var oldQuality=QualitySettings.skinWeights;
        try
        {
            var bones=new Transform[mesh.bindposeCount];var bind=mesh.bindposes;
            for(int i=0;i<bones.Length;i++)
            {
                bones[i]=new GameObject("ReferenceBone"+i).transform;bones[i].SetParent(root.transform,false);
                var rest=bind[i].inverse;bones[i].localPosition=rest.GetColumn(3);bones[i].localRotation=rest.rotation;bones[i].localScale=rest.lossyScale;
                bones[i].localPosition+=new Vector3(.03f*i,.01f*i,-.005f*i);
            }
            var renderer=root.AddComponent<SkinnedMeshRenderer>();renderer.sharedMesh=mesh;renderer.bones=bones;renderer.rootBone=root.transform;renderer.quality=SkinQuality.Auto;
            Func<SkinWeights,float> error=quality=>
            {
                QualitySettings.skinWeights=quality;var baked=new Mesh();renderer.BakeMesh(baked,true);
                var original=mesh.vertices;var posed=baked.vertices;int cursor=0;float maximum=0;
                for(int v=0;v<original.Length;v++)
                {
                    Vector3 expected=Vector3.zero;
                    for(int j=0;j<counts[v];j++){var w=weights[cursor++];expected+=(bones[w.boneIndex].localToWorldMatrix*bind[w.boneIndex]).MultiplyPoint3x4(original[v])*w.weight;}
                    maximum=Math.Max(maximum,Vector3.Distance(expected,posed[v]));
                }
                UnityEngine.Object.DestroyImmediate(baked);return maximum;
            };
            result.unlimitedBakeMaximumError=error(SkinWeights.Unlimited);result.fourBoneBakeMaximumError=error(SkinWeights.FourBones);
            if(result.unlimitedBakeMaximumError>.0001f)throw new InvalidOperationException("Python variable skin differs from independent matrix bake");
            string json=JsonUtility.ToJson(result,true);File.WriteAllText(Path.Combine(folder,"PythonWeights-readback.json"),json);return json;
        }
        finally{QualitySettings.skinWeights=oldQuality;UnityEngine.Object.DestroyImmediate(root);}
    }
}
