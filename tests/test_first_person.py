import unittest
import numpy as np
from operators.first_person import arm_name,native_name,validate_assignments
from operators.autorig import helmet_vertices


class FirstPerson(unittest.TestCase):
    def test_only_anatomical_arm_bones_can_influence_extracted_arms(self):
        self.assertEqual(arm_name('ShoulderPart2_L'),'Shoulder_L')
        self.assertEqual(arm_name('IndexFinger4_R'),'IndexFinger3_R')
        self.assertEqual(native_name('j_mid_2_L'),'MiddleFinger2_L')
        for name in ['Root_M','Chest_M','Head_M','WeaponPivot_R','Hip_L',None]:self.assertIsNone(arm_name(name))
        for name in ['tag_weapon','tag_camera','tag_L_IK_target']:self.assertTrue(native_name(name).startswith('unused_'))

    def test_shared_prefab_cannot_silently_change_an_unselected_operator(self):
        targets=[{'id':'a','renderers':[{'path_id':'12'}]},{'id':'b','renderers':[{'path_id':'12'}]}]
        for assignments in [{'a':'shrek'},{'a':'shrek','b':'fishguy'}]:
            with self.assertRaisesRegex(ValueError,'Shared first-person arms conflict'):validate_assignments(assignments,targets)
        validate_assignments({'a':'shrek','b':'shrek'},targets)
        validate_assignments({},targets)

    def test_head_rotation_does_not_pull_up_connected_chest_collar_vertices(self):
        points=np.array([[0,0,1.2],[.1,0,1.48],[-.1,0,1.48],[0,0,1.5],[.1,0,1.65],[-.1,0,1.65]])
        head=helmet_vertices(points,np.array([[0,1,2],[3,4,5]]))
        np.testing.assert_array_equal(head,[False,False,False,True,True,True])


if __name__=='__main__':unittest.main()
