import unittest
import numpy as np
from operators.native_weights import decode


class PackedWeights(unittest.TestCase):
    def test_implicit_fourth_is_fractional_remainder_and_preserves_stream_alignment(self):
        indices,weights=decode([12,10,4,31],[4,45,43,3,5],2,83)
        np.testing.assert_array_equal(indices,[[4,45,43,3],[5,0,0,0]]);np.testing.assert_allclose(weights[0],np.array([12,10,4,5])/31);np.testing.assert_allclose(weights.sum(1),1,atol=1e-7);self.assertTrue((weights>=0).all())
    def test_invalid_truncated_and_trailing_streams_are_rejected(self):
        for weights,bones in [([12,10,4],[1,2,3]),([32],[1]),([31,31],[1,2]),([31],[99])]:
            with self.assertRaises(ValueError):decode(weights,bones,1,83)


if __name__=='__main__':unittest.main()
