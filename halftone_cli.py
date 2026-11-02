#!/usr/bin/env python3
"""Offline semantic texture pipeline; see --help."""
import argparse
import json
from pathlib import Path
from halftone.assets import scan
from halftone.patterns import generate, previews
from halftone.classify import classify
from halftone.pipeline import apply, verify, restore
from halftone.materials import finalize
from halftone.extend import extend
from halftone.arrays import apply_arrays
from halftone.shared import separate_shared


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='halftone.json')
    p.add_argument('operation', choices=['scan-assets','generate-textures','classify-assets','preview-classification','apply-textures','verify-bundles','restore-backups','finalize-materials','extend-coverage','apply-array-textures','separate-shared-albedos'])
    p.add_argument('--array-mappings',default='config/array-layers.json')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--bundle', action='append', help='Limit staged edits to these bundle-relative paths; repeatable')
    args = p.parse_args()
    config = json.loads(Path(args.config).read_text())
    if args.operation == 'scan-assets':
        scan(config, config['paths']['reports'])
    elif args.operation == 'generate-textures':
        print(json.dumps(generate(config), indent=2))
        print(previews(config))
    elif args.operation in ('classify-assets','preview-classification'):
        report = classify(config)
        print(json.dumps(report['summary'], indent=2))
        if args.operation=='preview-classification':
            for r in report['assets']:
                if r['action']=='replace': print(r['category'],r['bundle'],r['name'],r['id'])
    elif args.operation=='apply-textures':
        print(json.dumps(apply(config,args.dry_run,args.bundle),indent=2))
    elif args.operation=='verify-bundles':
        print(json.dumps(verify(config),indent=2))
    elif args.operation=='restore-backups':
        print(json.dumps(restore(config,args.dry_run),indent=2))
    elif args.operation=='finalize-materials':
        print(json.dumps(finalize(config,args.dry_run),indent=2))
    elif args.operation=='extend-coverage':
        print(json.dumps(classify(config)['summary'] if args.dry_run else extend(config),indent=2))
    elif args.operation=='apply-array-textures':
        print(json.dumps(json.loads(Path(args.array_mappings).read_text()) if args.dry_run else apply_arrays(config,args.array_mappings),indent=2))
    elif args.operation=='separate-shared-albedos':
        print(json.dumps(classify(config)['summary'] if args.dry_run else separate_shared(config),indent=2))


if __name__ == '__main__':
    main()
