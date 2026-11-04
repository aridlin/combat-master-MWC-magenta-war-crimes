import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from skybox.bundles import texture_slots,encoded,build
from skybox.pixels import face_directions


def material(names):
    return {'m_Name':'test sky','m_SavedProperties':{'m_TexEnvs':[(name,{}) for name in names]}}


class SkyTextureBindings(unittest.TestCase):
    def test_single_cubemap_and_six_sided_layouts_stay_distinct(self):
        self.assertEqual(texture_slots(material(['_Tex'])),{'_Tex':None})
        layout=texture_slots(material(['_BackTex','_DownTex','_FrontTex','_LeftTex','_RightTex','_UpTex']))
        self.assertEqual(len(layout),6)
        # Axis labels are specified by Unity's 6 Sided skybox inspector.
        for slot,direction in {'_FrontTex':[0,0,1],'_BackTex':[0,0,-1],'_LeftTex':[1,0,0],'_RightTex':[-1,0,0],'_UpTex':[0,1,0],'_DownTex':[0,-1,0]}.items():
            np.testing.assert_array_equal(face_directions(layout[slot],np.array(0.),np.array(0.)),direction)

    def test_missing_duplicate_or_unreviewed_texture_slots_fail(self):
        for slots in ([],['_Tex','_MainTex'],['_Tex','_Tex'],['_FrontTex','_BackTex'],['_LeftTex','_RightTex','_UpTex','_DownTex','_FrontTex','_FrontTex']):
            with self.subTest(slots=slots),self.assertRaisesRegex(ValueError,'Unsupported or ambiguous'):
                texture_slots(material(slots))

    def test_separate_faces_match_the_existing_cubemap_encoding(self):
        for night in (False,True):
            combined=encoded(32,night);stride=32*32*4
            self.assertEqual(len(combined),stride*6)
            for face in range(6):
                self.assertEqual(encoded(32,night,face),combined[face*stride:(face+1)*stride])

    def test_conflicting_backup_fails_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source/src/maps/fake';source.parent.mkdir(parents=True);source.write_bytes(b'declared source')
            backup=root/'backups/src/maps/fake';backup.parent.mkdir(parents=True);backup.write_bytes(b'preserve this original')
            manifest=root/'app.acf';manifest.write_text('"buildid" "123"')
            config={'app_manifest':str(manifest),'expected_build_id':'123','bundle_root':str(root/'source')}
            settings={'output':str(root/'output'),'backups':str(root/'backups'),'sources':{'src/maps/fake':hashlib.sha256(source.read_bytes()).hexdigest()}}
            with patch('skybox.bundles.TARGETS',{'src/maps/fake':['sky']}),self.assertRaisesRegex(ValueError,'backup belongs to another baseline'):
                build(config,settings)
            self.assertEqual(backup.read_bytes(),b'preserve this original')


if __name__=='__main__':unittest.main()
