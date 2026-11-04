"""Synthetic RPak/Starpak visual fixtures; no proprietary data."""
import struct,tempfile,unittest
from pathlib import Path
from model_import.respawn_rpak import RPak7
RED=struct.pack('<HHI',0xf800,0,0)

def fixture(root,streamed=False,ambiguous=False):
 page=bytearray(768)
 def put(o,f,*v):struct.pack_into('<'+f,page,o,*v)
 put(0,'Q2I4HI',17,0,280,8 if streamed else 4,8 if streamed else 4,0,1,32 if streamed else 8)
 put(29,'6B',0,0,0,0,1,1 if streamed else 0)
 page[280:290]=b'pilot_col\0';page[330:336]=b'pilot\0'
 put(80,'Q',18);put(88,'2I',0,330);put(216,'4I',0,400,0,408);put(400,'Q',17);page[416:424]=RED
 entries=[(17,0,56,8,b'txtr'),(18,64,208,12,b'matl')]
 if ambiguous:
  page[448:656]=page[64:272];put(464,'Q',19);put(600,'4I',0,688,0,696);put(688,'Q',999);entries.append((19,448,208,12,b'matl'))
 header=bytearray(88);header[:4]=b'RPak';struct.pack_into('<H',header,4,7)
 struct.pack_into('<4H6I',header,56,32,1,1,0,0,len(entries),0,0,0,0)
 index=bytearray()
 for guid,offset,size,version,kind in entries:
  e=bytearray(72);struct.pack_into('<Q',e,0,guid);struct.pack_into('<4I',e,16,0,offset,0,416)
  struct.pack_into('<Q',e,32,4096 if streamed and guid==17 else 2**64-1)
  struct.pack_into('<II4s',e,60,size,version,kind);index.extend(e)
 data=header+b'pc_stream.starpak\0'.ljust(32,b'\0')+struct.pack('<IIQ',0,16,len(page))+struct.pack('<III',0,16,len(page))+index+page
 struct.pack_into('<Q',data,24,len(data));struct.pack_into('<Q',data,40,len(data))
 p=Path(root)/'fixture.rpak';p.write_bytes(data);star=Path(root)/'pc_stream.starpak'
 if streamed:star.write_bytes(b'SRPk\x01\0\0\0'+b'\0'*(4096-8)+RED*4+struct.pack('<QQQ',4096,32,1))
 return p,star,len(data)-len(page)

class RPakVisuals(unittest.TestCase):
 def test_original_embedded_color_and_material_resolution(self):
  with tempfile.TemporaryDirectory() as root:
   p,_,_=fixture(root)
   with RPak7(p) as r:
    im,record=r.texture_image(r.diffuse('pilot'));self.assertEqual(im.size,(4,4));self.assertEqual(im.getpixel((0,0)),(255,0,0,255));self.assertEqual(record['source'],'rpak');self.assertEqual(record['mip_bytes'],8)
   self.assertIsNone(r.data);self.assertTrue(r.file.closed)
 def test_streamed_color_and_directory_range_validation(self):
  with tempfile.TemporaryDirectory() as root:
   p,star,_=fixture(root,streamed=True)
   with RPak7(p) as r:
    texture=r.diffuse('pilot')
    with self.assertRaisesRegex(ValueError,'explicitly'):r.texture_image(texture)
    im,record=r.texture_image(texture,star);self.assertEqual(im.size,(8,8));self.assertEqual(im.getpixel((7,7)),(255,0,0,255));self.assertEqual(record['source'],'starpak')
    raw=bytearray(star.read_bytes());struct.pack_into('<Q',raw,len(raw)-16,1);star.write_bytes(raw)
    with self.assertRaisesRegex(ValueError,'outside'):r.texture_image(texture,star)
 def test_patch_compression_page_extents_and_pointer_rejection(self):
  with tempfile.TemporaryDirectory() as root:
   p,_,page=fixture(root);original=p.read_bytes()
   for offset,fmt,value,error in ((62,'H',1,'patch'),(6,'H',256,'decoded'),(40,'Q',1,'decoded'),(144,'I',999,'extents'),(page+8,'I',5,'pointer'),(208,'I',1,'header size'),(page,'Q',18,'GUID')):
    b=bytearray(original);struct.pack_into('<'+fmt,b,offset,value);p.write_bytes(b)
    with self.assertRaisesRegex(ValueError,error):RPak7(p)
   p.write_bytes(original[:87])
   with self.assertRaisesRegex(ValueError,'bounds'):RPak7(p)
 def test_duplicate_names_keep_variants_and_fail_ambiguity(self):
  with tempfile.TemporaryDirectory() as root:
   p,_,_=fixture(root,ambiguous=True)
   with RPak7(p) as r:
    self.assertEqual(len(r.names[('matl','pilot')]),2)
    with self.assertRaisesRegex(ValueError,'ambiguous'):r.diffuse('pilot')
    with self.assertRaisesRegex(ValueError,'Missing'):r.diffuse('unknown')

if __name__=='__main__':unittest.main()
