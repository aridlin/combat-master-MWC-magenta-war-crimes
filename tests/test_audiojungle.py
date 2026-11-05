import hashlib,io,json,tempfile,unittest,wave
from pathlib import Path
from unittest.mock import patch
import audiojungle as a
from installer.mwc_installer.engine import validate_audio_selection,compose


def wav():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b'\0\1'*441)
    return stream.getvalue()


class LocalAudiojungle(unittest.TestCase):
    def test_local_wav_records_actual_source_hash_without_running_scripts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=wav();(root/'sample.wav').write_bytes(data)
            (root/'autorun.py').write_text("raise RuntimeError('must never run')")
            spec={'clips':[{'source':'sample.wav'}]};_,cache=a.prepare(root,spec)
            self.assertEqual(cache['sample.wav'][0],data)
            self.assertEqual(cache['sample.wav'][1]['source_sha256'],hashlib.sha256(data).hexdigest())
            self.assertAlmostEqual(cache['sample.wav'][1]['source_seconds'],.01)

    def test_mp3_is_decoded_without_a_playback_or_script_api(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'sample.mp3').write_bytes(b'local compressed sample')
            with patch.object(a,'decode_mp3',return_value=wav()) as decode:
                data,meta=a.read_local(root,'sample.mp3')
            decode.assert_called_once_with(b'local compressed sample')
            self.assertEqual(data,wav());self.assertIn('decoded_wav_sha256',meta)

    def test_missing_escaped_symlink_and_executable_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/'pack';root.mkdir();(base/'outside.wav').write_bytes(wav())
            (root/'link.wav').symlink_to(base/'outside.wav')
            for name in ('missing.wav','../outside.wav','/outside.wav','link.wav','evil.py','sound\\bad.wav'):
                with self.subTest(name=name),self.assertRaises(ValueError):a.read_local(root,name)
            with self.assertRaisesRegex(ValueError,'extracted'):a.prepare(base/'source.7z')
            with self.assertRaisesRegex(ValueError,'Choose'):a.prepare('')

    def test_incomplete_selection_fails_without_creating_any_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'good.wav').write_bytes(wav())
            with self.assertRaises(ValueError):a.prepare(root,{'clips':[{'source':'good.wav'},{'source':'missing.mp3'}]})
            self.assertEqual([p.name for p in root.iterdir()],['good.wav'])

    def test_slot_conflict_is_explicit_and_detected_before_source_access(self):
        with patch.object(a,'prepare') as prepare:
            with self.assertRaisesRegex(ValueError,'same four Minigun'):
                validate_audio_selection({'tf2_medigun_audio','audiojungle_medigun'},'missing')
            prepare.assert_not_called()
            validate_audio_selection({'cat_audio','tf2_medigun_audio'},'')
            prepare.assert_not_called()
            validate_audio_selection({'cat_audio','audiojungle_medigun'},'local')
            prepare.assert_called_once_with('local')

    def test_compose_rejects_conflicts_before_allocating_a_build(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'uncreated-state'
            with self.assertRaisesRegex(ValueError,'same four Minigun'):
                compose({},state,{}, {'tf2_medigun_audio','audiojungle_medigun'},'')
            self.assertFalse(state.exists())

    def test_map_owns_the_same_four_reviewed_slots_as_vanilla_medigun_audio(self):
        other=json.loads((a.ROOT/'config/tf2-audio-map.json').read_text())
        spec=json.loads((a.ROOT/'config/audiojungle-map.json').read_text())
        self.assertEqual(spec['build_id'],other['build_id'])
        self.assertEqual([(r['id'],r['name']) for r in spec['clips']],[(r['id'],r['name']) for r in other['clips']])
        self.assertEqual(len(spec['clips']),4)


if __name__=='__main__':unittest.main()
