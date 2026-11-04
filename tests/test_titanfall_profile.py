import unittest
from operators.profiles import profile


def hierarchy():
    names=['def_c_hip','def_c_spineA','def_c_spineB','def_c_spineC','def_c_neckA','def_c_head']
    parents=[-1,0,1,2,3,4]
    for side in ('l','r'):
        for bone in ('clav','shoulder','elbow','wrist','thigh','knee','ankle','ball'):
            names.append(f'def_{side}_{bone}');parents.append(0)
        wrist=names.index(f'def_{side}_wrist')
        for finger in ('Index','Mid','Thumb','Ring','Pinky'):
            parent=wrist
            for letter in 'ABC':
                names.append(f'def_{side}_fin{finger}{letter}');parents.append(parent);parent=len(names)-1
    names+=['def_cape_1','def_cape_2','def_l_elbowB']
    parents += [0,len(names)-3,names.index('def_l_shoulder')]
    return {'bone_names':names,'bone_parents':parents}


class TitanfallProfile(unittest.TestCase):
    def test_explicit_primary_and_helper_inheritance(self):
        meta=hierarchy();p=profile('titanfall2_native',meta);names=meta['bone_names']
        self.assertEqual(p['source_targets'][names.index('def_r_finMidB')],'MiddleFinger2_R')
        self.assertEqual(p['source_targets'][names.index('def_cape_2')],'Root_M')
        self.assertEqual(p['source_targets'][names.index('def_l_elbowB')],'Elbow_L')
        self.assertEqual(p['primary_sources']['Shoulder_L'],names.index('def_l_shoulder'))
        self.assertEqual(p['source_basis'],[[-1,0,0],[0,0,-1],[0,1,0]])

    def test_bad_hierarchy_and_missing_required_anchor(self):
        meta=hierarchy();meta['bone_names'][5]='unknown_head'
        with self.assertRaisesRegex(ValueError,'anchors'):profile('titanfall2_native',meta)
        meta=hierarchy();meta['bone_parents'][-1]=len(meta['bone_names'])
        with self.assertRaisesRegex(ValueError,'anchors'):profile('titanfall2_native',meta)
        meta=hierarchy();meta['bone_parents'][-2]=len(meta['bone_names'])-2
        with self.assertRaisesRegex(ValueError,'Cyclic'):profile('titanfall2_native',meta)
        meta=hierarchy();meta['bone_names'][-1]=meta['bone_names'][0]
        with self.assertRaisesRegex(ValueError,'skeleton'):profile('titanfall2_native',meta)


if __name__=='__main__':unittest.main()
