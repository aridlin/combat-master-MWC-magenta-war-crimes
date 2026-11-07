import hashlib,io,json,os,struct,tempfile,unittest,wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import audio_preview as preview
import tf2_audio
from installer.mwc_installer import engine


def wav(samples,rate=44100):
    stream=io.BytesIO()
    with wave.open(stream,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate);output.writeframes(np.asarray(samples,dtype='<i2').tobytes())
    return stream.getvalue()


def owned_slot(name='owned clip',frames=441,rate=44100):
    template=bytearray(96+frames*2);template[:4]=b'FSB5';struct.pack_into('<4I',template,4,1,1,36,0);struct.pack_into('<I',template,24,2)
    struct.pack_into('<Q',template,60,(frames<<34)|{22050:10,44100:16}[rate])
    template[96:]=np.full(frames,3000,dtype='<i2').tobytes()
    clip=SimpleNamespace(m_Resource=SimpleNamespace(m_Source='owned',m_Offset=0,m_Size=len(template)),m_CompressionFormat=0,m_Channels=1,m_Frequency=rate,m_Length=frames/rate)
    obj=SimpleNamespace(path_id=1,type=SimpleNamespace(name='AudioClip'),peek_name=lambda:name,read=lambda:clip,assets_file=None)
    row={'id':'1','name':name,'source':'owned.wav','offset_seconds':0.}
    return obj,row,bytes(template)


class AudioPreviews(unittest.TestCase):
    def test_shared_slot_processing_validates_native_shape_before_reading_source(self):
        obj,row,template=owned_slot();reader=lambda name:(wav(np.full(441,5000)),{'source_sha256':'owned'})
        with patch.object(tf2_audio,'get_resource_data',return_value=template):
            clip,raw,pcm,analysis,_=tf2_audio.processed_slot(obj,row,reader,{})
            self.assertEqual(len(pcm),882);self.assertEqual(raw,template);self.assertEqual(analysis['frames'],441)
            obj.read().m_Length=.5
            with patch('builtins.open',side_effect=AssertionError('source should not be opened')):
                with self.assertRaisesRegex(ValueError,'frame count'):tf2_audio.processed_slot(obj,row,reader,{})
        with self.assertRaisesRegex(ValueError,'slot changed'):tf2_audio.processed_slot(obj,{**row,'name':'different'},reader,{})

    def test_combined_preview_has_separate_clips_and_explicit_silence(self):
        first=np.array([0,1000,-1000,0],dtype='<i2').tobytes();second=np.array([2000,0],dtype='<i2').tobytes()
        pcm,timeline=preview.audition_pcm([(first,44100),(second,22050)])
        result=np.frombuffer(pcm,dtype='<i2');gap=round(44100*.3)
        np.testing.assert_array_equal(result[:4],[0,1000,-1000,0]);self.assertTrue(np.all(result[4:4+gap]==0))
        self.assertEqual(timeline,[{'clip_index':0,'start_frame':0,'frames':4},{'clip_index':1,'start_frame':4+gap,'frames':4}])
        self.assertEqual(len(result),8+gap)

    def test_owned_export_preserves_source_bytes_and_original_rate_WAV_PCM(self):
        obj,row,template=owned_slot();spec={'build_id':'owned','clips':[row]};reader=lambda name:(wav(np.full(441,5000)),{'source_sha256':'owned'})
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=root/'originals'/'audio';bundle.parent.mkdir();bundle.write_bytes(b'owned immutable bundle');output=root/'preview';previous=Path.cwd()
            try:
                os.chdir(root)
                with patch.object(preview,'source_reader',return_value=(spec,reader)),patch.object(preview,'build_id',return_value='owned'),patch.object(preview.UnityPy,'load',return_value=SimpleNamespace(objects=[obj])),patch.object(tf2_audio,'get_resource_data',return_value=template):
                    result=preview.export({'bundle_root':str(bundle.parent)},bundle,output,'tf2_medigun_audio')
                with wave.open(str(output/'01.wav')) as audio:
                    pcm=audio.readframes(audio.getnframes());self.assertEqual(audio.getframerate(),44100)
                self.assertEqual(hashlib.sha256(pcm).hexdigest(),result['clips'][0]['pcm_sha256'])
                self.assertFalse(result['game_or_installer_selection_changed']);self.assertEqual(bundle.read_bytes(),b'owned immutable bundle')
                self.assertFalse((root/'state.json').exists())
            finally:os.chdir(previous)

    def test_request_uses_verified_backup_without_install_recovery_or_process_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);game=root/'game';bundle_root=game/'Bundles';bundle_root.mkdir(parents=True)
            state=root/'state';backup=state/'originals/root/audio';backup.parent.mkdir(parents=True);backup.write_bytes(b'owned original')
            saved={'bundle_root':str(bundle_root),'originals':{'root/audio':hashlib.sha256(backup.read_bytes()).hexdigest()},'selected':['cat_audio'],'operator_assignments':{'operator_30':'shrek'}}
            state_file=state/'state.json';state_file.write_text(json.dumps(saved));before=state_file.read_bytes()
            captured=[]
            def export(config,bundle,output,pack,**kwargs):
                self.assertEqual(bundle,backup);output.mkdir(parents=True);(output/'preview.wav').write_bytes(wav([0,1000,0]));report={'pack':pack,'private_audio_preview':True};(output/'manifest.json').write_text(json.dumps(report));captured.append(output);return report
            request={'action':'preview_audiojungle','game':str(game),'state':str(state),'audiojungle_source':'owned pack','offline_authorized':False,'selected':['tf2_medigun_audio','audiojungle_medigun']}
            with patch.object(engine,'inspect_game',return_value={'bundle_root':str(bundle_root)}),patch.object(preview,'export',side_effect=export),patch.object(engine,'game_running',side_effect=AssertionError('read-only preview must not stop a running game')),patch.object(engine,'recover',side_effect=AssertionError('no recovery')),patch.object(engine,'snapshot',side_effect=AssertionError('no snapshot')),patch.object(engine,'transaction',side_effect=AssertionError('no install')):
                for _ in range(2):preview.request_preview(request)
                unlink=Path.unlink
                def locked_wave(path,*args,**kwargs):
                    if path==captured[0]/'preview.wav':raise PermissionError('Owned Windows player lock control')
                    return unlink(path,*args,**kwargs)
                with patch.object(Path,'unlink',locked_wave):preview.request_preview(request)
                self.assertTrue((captured[0]/'manifest.json').exists())
                preview.request_preview(request) # The player released it; cleanup can retry.
            self.assertEqual(state_file.read_bytes(),before);self.assertEqual(backup.read_bytes(),b'owned original')
            self.assertEqual(len(list((state/'audio-previews/audiojungle_medigun').iterdir())),2)
            self.assertFalse(captured[0].exists());self.assertEqual((state/'audio-preview.txt').read_text(),str(captured[-1]/'preview.wav'))

    def test_changed_backup_and_cache_escape_fail_without_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);game=root/'game';bundle_root=game/'Bundles';bundle_root.mkdir(parents=True);state=root/'state';state.mkdir()
            config={'bundle_root':str(bundle_root)};request={'action':'preview_tf2_audio','game':str(game),'state':str(state)}
            saved={'bundle_root':str(bundle_root),'originals':{'root/audio':'changed'}};(state/'state.json').write_text(json.dumps(saved))
            backup=state/'originals/root/audio';backup.parent.mkdir(parents=True);backup.write_bytes(b'owned')
            with patch.object(engine,'inspect_game',return_value=config),patch.object(preview,'export') as export:
                with self.assertRaisesRegex(ValueError,'backup changed'):preview.request_preview(request)
                export.assert_not_called()
                (state/'state.json').unlink();(state/'audio-previews').symlink_to(root/'outside')
                with self.assertRaisesRegex(ValueError,'outside the state'):preview.request_preview(request)
                export.assert_not_called()

    def test_preview_output_cannot_be_inside_source_or_game(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);game=root/'game';game.mkdir()
            with patch.object(engine,'inspect_game',return_value={'bundle_root':str(game/'Bundles')}):
                with self.assertRaisesRegex(ValueError,'outside the game'):preview.request_preview({'action':'preview_tf2_audio','state':str(game/'previews'),'game':str(game)})
            source=root/'originals/audio';source.parent.mkdir();source.write_bytes(b'owned source')
            previous=Path.cwd()
            try:
                os.chdir(root)
                with patch.object(preview,'source_reader',return_value=({'build_id':'owned','clips':[]},None)),patch.object(preview,'build_id',return_value='owned'),patch.object(preview.UnityPy,'load') as load:
                    with self.assertRaisesRegex(ValueError,'outside the Steam'):preview.export({'bundle_root':str(game/'Bundles')},source,source.parent/'forbidden','tf2_medigun_audio')
                    load.assert_not_called()
                self.assertFalse((source.parent/'forbidden').exists());self.assertEqual(source.read_bytes(),b'owned source')
            finally:os.chdir(previous)


if __name__=='__main__':unittest.main()
