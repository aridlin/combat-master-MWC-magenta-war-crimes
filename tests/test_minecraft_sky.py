import io,json,tempfile,unittest,zipfile,warnings
from pathlib import Path
import numpy as np
from PIL import Image
from skybox.minecraft import load,colors,MEMBERS
from skybox.pixels import face_directions,faces
from skybox.bundles import source_assets,sky_appearance
from installer.mwc_installer.engine import sky_source_path


def fixture(path,opaque_cloud=False,sun_color=(0,0,0),bad_cloud=False):
    cloud=Image.new('RGBA',(4,8) if bad_cloud else (4,4),(255,255,255,0))
    if opaque_cloud:cloud.putpixel((0,0),(255,255,255,255))
    sun=Image.new('RGB',(4,4),sun_color);moon=Image.new('RGB',(16,8),(200,0,0));moon.paste((0,30,0),(0,0,4,4));raw={}
    for name,image in [('clouds',cloud),('sun',sun),('moon_phases',moon)]:
        stream=io.BytesIO();image.save(stream,format='PNG');raw[name]=stream.getvalue()
    raw['biome']=json.dumps({'effects':{'sky_color':0x123456,'fog_color':0x789abc}}).encode()
    raw['version']=b'{"id":"original-test-art"}'
    with zipfile.ZipFile(path,'w') as z:
        for key,value in raw.items():z.writestr(MEMBERS[key],value)
    return path


class LocalMinecraftSky(unittest.TestCase):
    def test_only_local_art_normalizes_exactly_the_reviewed_sky_appearance(self):
        import copy
        tree={'m_Name':'sky','m_SavedProperties':{'m_Floats':[('_Rotation',199.),('_Exposure',.34),('_SkyExponent',3.)],'m_Colors':[('_Tint',dict(r=1.,g=.99,b=.95,a=.5)),('_Other',dict(r=1.))]}}
        saved=copy.deepcopy(tree)
        self.assertIsNone(sky_appearance(tree,False));self.assertEqual(tree,saved)
        report=sky_appearance(tree,True)
        self.assertEqual(report['exposure'],{'old':.34,'new':1.})
        self.assertEqual(report['tint']['new'],dict.fromkeys(('r','g','b','a'),.5))
        saved['m_SavedProperties']['m_Floats'][1]=('_Exposure',1.)
        saved['m_SavedProperties']['m_Colors'][0]=('_Tint',dict.fromkeys(('r','g','b','a'),.5))
        self.assertEqual(tree,saved)
        for fields in ([],[('_Exposure',1.),('_Exposure',2.)],[('_Exposure',float('nan'))]):
            with self.assertRaises(ValueError):sky_appearance({'m_Name':'bad','m_SavedProperties':{'m_Floats':fields}},True)

    def test_older_frontend_retains_saved_source_and_explicit_blank_clears_it(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root,'minecraft-source.txt').write_text('/owned/client.jar',encoding='utf8')
            self.assertEqual(sky_source_path({},root),'/owned/client.jar')
            self.assertEqual(sky_source_path({'minecraft_source':''},root),'')
            with self.assertRaisesRegex(ValueError,'local jar path'):sky_source_path({'minecraft_source':None},root)

    def test_reads_art_and_palette_without_extracting_the_archive(self):
        with tempfile.TemporaryDirectory() as root:
            path=fixture(Path(root)/'client.jar');assets=load(path)
            self.assertEqual(assets['sky_color'],(18,52,86));self.assertEqual(assets['fog_color'],(120,154,188))
            self.assertEqual(assets['provenance']['version'],'original-test-art')
            self.assertFalse(assets['provenance']['assets_redistributed'])
            self.assertEqual(list(Path(root).iterdir()),[path])
            np.testing.assert_array_equal(colors(np.array([0.,1,0]),False,assets),[18,52,86])

    def test_cloud_alpha_and_black_backed_sun_are_respected(self):
        with tempfile.TemporaryDirectory() as root:
            clear=load(fixture(Path(root)/'clear.jar'));cloudy=load(fixture(Path(root)/'cloud.jar',opaque_cloud=True));red=load(fixture(Path(root)/'red.jar',sun_color=(20,0,0)))
            np.testing.assert_array_equal(colors(np.array([0.,1,0]),False,cloudy),[255,255,255])
            direction=np.array([.45,.72,.35]);base=colors(direction,False,clear).astype(int)
            np.testing.assert_array_equal(colors(direction,False,red).astype(int)-base,[20,0,0])
            np.testing.assert_array_equal(colors(-direction,False,clear),colors(-direction,False,red))

    def test_night_uses_first_authored_moon_phase(self):
        with tempfile.TemporaryDirectory() as root:
            assets=load(fixture(Path(root)/'client.jar'));direction=np.array([.45,.72,.35]);pixel=colors(direction,True,assets)
            self.assertGreater(int(pixel[1]),40);self.assertLess(int(pixel[0]),40)

    def test_same_cube_edge_direction_has_identical_local_art_sampling(self):
        with tempfile.TemporaryDirectory() as root:
            assets=load(fixture(Path(root)/'client.jar',opaque_cloud=True));v=np.linspace(-1,1,23)
            a=face_directions(0,np.ones_like(v),v);b=face_directions(5,-np.ones_like(v),v)
            np.testing.assert_array_equal(colors(a,False,assets),colors(b,False,assets))
            self.assertEqual([im.size for im in faces(32,assets=assets)],[(32,32)]*6)

    def test_duplicate_missing_or_wrong_layout_members_fail(self):
        with tempfile.TemporaryDirectory() as root:
            path=fixture(Path(root)/'bad.jar',bad_cloud=True)
            with self.assertRaisesRegex(ValueError,'layout'):load(path)
            path=fixture(Path(root)/'duplicate.jar')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(path,'a') as z:z.writestr(MEMBERS['version'],b'{"id":"duplicate"}')
            with self.assertRaisesRegex(ValueError,'duplicate'):load(path)
            with zipfile.ZipFile(Path(root)/'empty.jar','w'):pass
            with self.assertRaisesRegex(ValueError,'Missing'):load(Path(root)/'empty.jar')

    def test_changing_source_or_exporting_into_source_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            jar=fixture(Path(root)/'client.jar');settings={'minecraft_source':str(jar),'output':str(Path(root)/'private')};_,provenance=source_assets(settings)
            fixture(jar,sun_color=(20,0,0))
            with self.assertRaisesRegex(ValueError,'manifest'):source_assets(settings,{'sky_source':provenance})
            settings['output']=str(Path(__file__).resolve().parents[1]/'assets/private-should-not-exist')
            with self.assertRaisesRegex(ValueError,'outside'):source_assets(settings)
