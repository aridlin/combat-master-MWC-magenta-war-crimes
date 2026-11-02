"""Shared local asset hashes; no game paths or account data."""
import hashlib


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def inventory(env):
    """Original backing bytes; use ObjectReader.data for pending edits."""
    return {(obj.assets_file.name,obj.path_id):{
        'type':obj.type.name,'sha256':hashlib.sha256(obj.get_raw_data()).hexdigest()}
        for obj in env.objects}
