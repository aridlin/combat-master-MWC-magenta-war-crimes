"""Conservative reference-backed semantic classification, with explicit conflicts."""
import collections
import re
from pathlib import Path
from .assets import load_scan, dump

DATA_SLOTS = {'Normal':'normal', 'Normal_Map':'normal', '_BumpMap':'normal',
              'Metallic':'metallic_smoothness', '_MetallicGlossMap':'metallic_smoothness',
              '_Met_AO_smooth':'packed_metallic_ao_smoothness', '_SpecGlossMap':'specular_smoothness',
              '_OcclusionMap':'ambient_occlusion', '_FlapMask':'alpha_or_cloth_mask',
              '_Mask':'mask', 'Reticle':'ui_reticle', 'Camo':'unverified_overlay'}


def rule_categories(rules, text):
    return {r['category'] for r in rules if re.search(r['regex'], text)}


def classify(config):
    scans = load_scan(config['paths']['reports'])
    textures, materials, users = {}, {}, collections.defaultdict(list)
    for bundle in scans:
        for t in bundle['textures']:
            textures[t['id']] = {**t, 'bundle': bundle['bundle'], 'source': bundle['source']}
        for m in bundle['materials']:
            materials[m['id']] = {**m, 'bundle': bundle['bundle']}
        for renderer in bundle['renderers']:
            for material in renderer['materials']:
                users[material].append({**renderer, 'bundle': bundle['bundle']})
    usage = collections.defaultdict(list)
    known_weapons = {m['name'] for m in materials.values() if m['bundle'].startswith('src/weapons/')}
    known_characters = {m['name'] for m in materials.values() if m['bundle'] in ('src/thrid_person','src/first_person')}
    for mid, material in materials.items():
        renderers = users.get(mid, [])
        explicit = config['material_overrides'].get(mid, 'automatic')
        # Scene renderer names can describe a whole building/atlas. Do not let
        # a nearby tree or concrete child classify every surface on that object.
        context = material['name']
        categories = rule_categories(config['material_rules'], context)
        # Character equipment stays character-colored, including goggles/glass.
        if material['bundle'] == 'src/thrid_person' and any(r['type']=='SkinnedMeshRenderer' for r in renderers):
            categories = {'characters'}
        elif categories == {'characters', 'glass'}:
            categories = {'characters'}
        elif material['bundle'].startswith('src/weapons/'):
            categories = {'characters'} if 'characters' in categories else {'weapons'}
        elif material['bundle'] == 'src/first_person':
            categories = {'characters'}
        elif material['bundle'].startswith('src/maps/'):
            # A statue/female-shaped prop is not a player model.
            categories.discard('characters')
        elif material['bundle'].startswith('src/blueprints/'):
            name = material['name']
            if any(name == known or name.startswith(known+'_') for known in known_weapons):
                categories = {'weapons'}
        if config.get('coverage_mode')=='all_surface_albedo' and len(categories)>1:
            n=material['name'].lower()
            if 'leaf' in n or 'leaves' in n or 'grass' in n:
                categories={'vegetation'}
            elif 'gravel' in n:
                categories={'dirt'}
            elif 'wood' in n and 'wood' in categories:
                categories={'wood'}
            elif 'metal' in n and 'glass' in n:
                categories={'glass'} if 'trans' in n else {'sheet_metal'}
            if any(name == known or name.startswith(known+'_') for known in known_characters):
                categories = {'characters'} if categories != {'weapons'} else {'characters','weapons'}
            if re.search(config.get('weapon_name_regex', r'(?!)'), name):
                # A weapon decorated with an operator theme remains a weapon:
                # ButterflyKnife_Frogman and BenelliM2_*_Angel are orange.
                categories = {'weapons'}
        if explicit != 'automatic':
            categories = {explicit} if explicit else set()
        # In full-surface mode the shipped shader's own weapon flag is
        # stronger evidence than decorative skin names. Unknown props get
        # a documented neutral fallback rather than retaining their albedo.
        fallback = False
        if config.get('coverage_mode')=='all_surface_albedo' and explicit=='automatic':
            if material['bundle'] in ('src/thrid_person','src/first_person'):
                categories={'characters'}
            elif re.search(r'(?i)(?:watch|garmin|parashut|parachut|zipline|paramotor|helmet|glove|sleeve|handacc|dog.?tag)',material['name']):
                categories={'characters'}
            elif not material['bundle'].startswith('src/maps/') and material.get('floats',{}).get('_IsWeapon')==1 and (material['bundle'].startswith(('src/weapons/','src/blueprints/')) or re.search(config.get('weapon_name_regex',r'(?!)'),material['name'])):
                categories={'weapons'}
            elif not categories:
                categories={config['fallback_category']}
                fallback=True
        color_aliases={p['texture'] for p in material['properties'] if p['slot'] in config['color_slots']}
        for prop in material['properties']:
            if prop['texture']:
                usage[prop['texture']].append({'material_id': mid, 'material': material['name'],
                    'material_bundle': material['bundle'], 'slot': prop['slot'],
                    'scale': prop['scale'], 'offset': prop['offset'],
                    'categories': sorted(categories), 'renderers': [r['name'] for r in renderers],
                    'fallback': fallback,
                    'is_color': prop['slot'] in config['color_slots'] or (prop['slot']=='_Tex' and prop['texture'] in color_aliases),
                    'renderer_types': sorted({r['type'] for r in renderers})})
    records = []
    if config.get('coverage_mode')=='all_surface_albedo':
        for refs in usage.values():
            known=set().union(*(set(r['categories']) for r in refs if r['is_color'] and not r['fallback']))
            if len(known)==1:
                for ref in refs:
                    if ref['is_color'] and ref['fallback']:
                        ref['categories']=sorted(known)
                        ref['inferred_from_shared_albedo']=True
                        ref['fallback']=False
    excluded = config['excluded_name_regex']
    for tid, t in textures.items():
        refs = usage.get(tid, [])
        colors = [r for r in refs if r['is_color']]
        noncolors = [r for r in refs if not r['is_color']]
        categories = set().union(*(set(r['categories']) for r in colors)) if colors else set()
        reasons = []
        override = config['asset_overrides'].get(tid, 'automatic')
        if override != 'automatic':
            if override:
                # Explicit mapping resolves unknowns, never known cross-category use.
                categories.add(override)
            else:
                reasons.append('explicit_skip')
        if not categories:
            filename_hints = rule_categories(config['filename_rules'], t['name'])
            if len(filename_hints) == 1 and colors:
                categories = filename_hints
        if not colors:
            reasons.append('no_supported_albedo_reference')
        if noncolors:
            reasons.append('also_used_as_noncolor_or_unknown_slot')
        if len(categories) > 1 or any(len(r['categories'])>1 for r in colors):
            reasons.append('mixed_category_conflict')
        if len(categories) == 0:
            reasons.append('unclassified')
        if any(not r['categories'] for r in colors) and override == 'automatic':
            reasons.append('shared_with_unclassified_material')
        if re.search(excluded, t['name']+' '+' '.join(r['material'] for r in refs)):
            reasons.append('excluded_ui_decal_effect_or_ambiguous_name')
        if config.get('coverage_mode')!='all_surface_albedo' and t['bundle'].startswith('src/maps/') and re.search(r'(?i)(atlas|streetprops|_props_|trim|cardboard|boxes|_set\d)',t['name']):
            reasons.append('possible_mixed_category_atlas')
        if any(any(rt in ('ParticleSystemRenderer','TrailRenderer','LineRenderer') for rt in r['renderer_types']) for r in colors):
            reasons.append('effect_renderer')
        full=config.get('coverage_mode')=='all_surface_albedo'
        if t['format'] not in ((3,4,10,12,25,28,29) if full else (10,12,28,29)):
            reasons.append('unsupported_texture_format')
        if not full and (t['width'] < 32 or t['height'] < 32):
            reasons.append('too_small_for_pattern')
        if (t['width'] % 4 or t['height'] % 4) and not (full and t['format'] in (3,4,25)):
            reasons.append('non_block_aligned_dimensions')
        if t['color_space'] != 1 and not (full and colors and not noncolors):
            reasons.append('not_srgb_color_texture')
        category = next(iter(categories)) if len(categories) == 1 else None
        if category and not config['categories'].get(category, {}).get('enabled', False):
            reasons.append('category_disabled')
        data_kinds = sorted({('albedo' if r['is_color'] else DATA_SLOTS.get(r['slot'],'unknown_shader_data')) for r in refs})
        records.append({**t, 'category': category, 'candidates': sorted(categories), 'data_kinds':data_kinds or ['unreferenced_or_external'],
                        'uses_neutral_fallback':any(r['fallback'] for r in colors),
                        'action': 'replace' if not reasons else 'preserve',
                        'reasons': sorted(set(reasons)), 'references': refs})
    summary = {'textures': len(records), 'eligible': sum(r['action']=='replace' for r in records),
               'categories': dict(collections.Counter(r['category'] for r in records if r['action']=='replace')),
               'preserve_reasons': dict(collections.Counter(x for r in records for x in r['reasons'])),
               'bundles_scanned': len(scans), 'parse_errors': sum(len(b['errors']) for b in scans)}
    report = {'summary': summary, 'assets': records,
              'limitations': ['References in scripts/custom shader properties cannot be inferred reliably.',
                 'Semantic names are evidence, not proof; ambiguous assets remain unchanged.',
                 'UVs and material scales are preserved, so world-space dot scale is approximate.']}
    dump(Path(config['paths']['reports'])/'classification.json', report)
    return report
