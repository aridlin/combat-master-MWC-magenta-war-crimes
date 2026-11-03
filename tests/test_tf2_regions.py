import unittest
from operators.profiles import tf2_mapping


class TF2AnatomicalRegions(unittest.TestCase):
    def test_bandolier_sections_share_one_chest_frame(self):
        regions,_=tf2_mapping(['bip_pelvis','bip_spine_3','bip_head','bip_collar_R','prp_bullet_side','prp_bullet_shoulder'],[-1,0,1,1,0,3])
        self.assertEqual(regions[4], 'Chest_M');self.assertEqual(regions[5], 'Chest_M')
    def test_wrist_cloth_cigarette_and_coat_tails_follow_distinct_regions(self):
        names=['bip_pelvis','bip_spine_2','bip_spine_3','bip_head','bip_lowerArm_L','bip_hand_L','prp_wristInner_L','prp_wristOuter_L','prp_cig','prp_coat_front_0_L','prp_helmet','prp_coatCollar_L']
        parents=[-1,0,1,2,2,4,4,4,3,0,3,2]
        regions,primary=tf2_mapping(names,parents)
        self.assertEqual([regions[i] for i in (6,7,8,9,10,11)],['Elbow_L','Elbow_L','Head_M','Root_M','Head_M','Chest_M'])
        self.assertEqual(regions[1],regions[2])
        self.assertEqual(primary['Chest_M'],2)
        self.assertEqual(primary['Elbow_L'],4)
    def test_unknown_weighted_root_is_not_guessed_as_chest_or_pelvis(self):
        regions,_=tf2_mapping(['bip_pelvis','bip_head','unknown_root'],[-1,0,-1])
        self.assertIsNone(regions[2])  # adapt rejects it if actually weighted
    def test_invalid_ancestry_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'parent chain'):
            tf2_mapping(['bip_pelvis','bip_head','prp_a','prp_b'],[-1,0,3,2])


if __name__=='__main__':unittest.main()
