import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from catgun.geometry import Mesh,render

class PreviewLighting(unittest.TestCase):
    def test_studio_fill_lights_front_without_modifying_source(self):
        mesh=Mesh();mesh.vertices=[[0,0,0],[1,0,0],[0,0,1]];mesh.normals=[[0,-1,0]]*3;mesh.uv=[[.5,.5]]*3;mesh.faces=[[0,1,2]]
        original=[x.copy() for x in mesh.arrays()];texture=Image.new('RGB',(4,4),(80,100,120))
        with tempfile.TemporaryDirectory() as root:
            files=[Path(root)/name for name in ('default.png','studio.png')]
            for p,mode in zip(files,('default','studio')):render(mesh,p,eye=(.3,-3,.3),target=(.3,0,.3),width=200,height=240,texture=texture,label='Source preview',lighting=mode)
            a,b=[np.asarray(Image.open(p))[40:] for p in files]
            old=np.all(a==[18,23,28],axis=2);self.assertGreater(old.sum(),1000)
            self.assertGreater(b[old].mean(),a[old].mean()*2)
            for x,y in zip(original,mesh.arrays()):np.testing.assert_array_equal(x,y)
            with self.assertRaisesRegex(ValueError,'lighting'):render(mesh,files[0],lighting='unknown')

if __name__=='__main__':unittest.main()
