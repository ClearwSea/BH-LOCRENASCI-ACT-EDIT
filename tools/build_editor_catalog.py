"""Derive the standalone editor catalog from an independently built runtime.

This is a development tool, not a requirement for running the editor. It reads
the verified portable runtime and native library supplied as explicit inputs;
its temporary server account is created in a fresh, automatically removed
directory. It writes only fields needed by the editor, never a game save.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


FIELDS = {
    'avatardata': ('avatarID', 'fullName', 'unlockStar', 'avatarFragmentID',
                   'initialWeapon', 'weaponBaseTypeList', 'skillList', 'baseAvatarID'),
    'avatarsubskilldata': ('avatarSubSkillId', 'skillId', 'maxLv', 'name'),
    'avatarexdata': ('avatarIDList', 'commonSubSkillList'),
    'dressdata': ('dressID', 'dressType', 'avatarIDList', 'name'),
    'weapondata': ('ID', 'maxLv', 'expType', 'baseType', 'cost', 'evoID', 'evoMaterial', 'displayTitle'),
    'stigmatadata': ('ID', 'maxLv', 'expType', 'baseType', 'cost', 'evoID', 'evoMaterial', 'displayTitle', 'setID'),
    'materialdata': ('ID', 'quantityLimit', 'ItemType', 'displayTitle', 'characterExpProvide', 'gearExpProvideBase'),
    'equipmentleveldata': ('level', 'Type1'),
    'avatarleveldata': ('level', 'cost'),
    'playerleveldata': ('level', 'avatarLevelLimit', 'stamina'),
    'avatarfragmentdata': ('ID', 'quantityLimit'),
    'cabinleveldata': ('cabinType', 'level', 'playerLevelNeed'),
    'cabinextendgradedata': ('cabinType', 'extendGrade', 'cabinLevelMax'),
    'cabintechtreedata': ('Cabin', 'X', 'Y', 'AbilityType', 'UnlockLevel', 'Argument1',
                           'UnlockAvatarID', 'UnlockAvatarLevel', 'Title'),
}
STAGE_FIELDS = ('id', 'kind', 'difficulty', 'chapterId', 'editor_chapter_id',
                'editor_min_level', 'unlockPlayerLevel', 'unlockStarNum',
                'maxProgress', 'preLevelID', 'display_name')
TEXT_FIELDS = {'fullName', 'name', 'displayTitle', 'Title'}


def selected(row, names):
    return {name: row[name] for name in names if name in row}


def generate(runtime, native):
    runtime, native = runtime.resolve(), native.resolve()
    os.environ['BH3_PACKAGED_NATIVE_LIBRARY'] = str(native)
    sys.path.insert(0, str(runtime))
    import server19_portable as portable
    import server19_editor_progress as progress
    import server19_editor_material_presets as presets
    import server19_gacha as gacha
    import server19_stage as stage
    with tempfile.TemporaryDirectory(prefix='bh3-editor-catalog-') as temp:
        _, verified = portable.configure(Path(temp))
        source = progress.catalog_from_configured_runtime()
        tables = {name: stage._table(name) for name in FIELDS}
        result = {}
        for name, fields in FIELDS.items():
            rows = tables[name]
            if name in ('cabinleveldata', 'cabinextendgradedata'):
                rows = [row for row in rows if row.get('cabinType') in (3, 4, 5)]
            if name == 'cabintechtreedata':
                rows = [row for row in rows if row.get('Cabin') in (3, 4, 5)]
            result[name] = [selected(row, fields) for row in rows]
        result['stages'] = []
        for row in source['stages']:
            item = selected(row, STAGE_FIELDS)
            # Only the number of challenges is needed to validate star indices.
            item['challengeList'] = [0] * len(row['challengeList'])
            result['stages'].append(item)
        sakura = source['sakura']
        result['sakura'] = {'stories': [selected(row, ('Cycle', 'StoryID'))
                                        for row in sakura['stories']]}
        for key in ('cycle', 'second_cycle', 'third_cycle', 'fourth_cycle'):
            result['sakura'][key] = selected(sakura[key], ('level',))
        result['abyss_floors'] = source['abyss_floors']
        result['material_presets'] = presets.build(tables, gacha.CHANNELS)
        referenced = {value for rows in result.values() if isinstance(rows, list)
                      for row in rows if isinstance(row, dict)
                      for key, value in row.items()
                      if key in TEXT_FIELDS and isinstance(value, str)}
        result['textmap'] = [selected(row, ('ID', 'Text')) for row in stage._table('textmap')
                             if row.get('ID') in referenced]
        manifest = runtime / 'portable-manifest.json'
        return {'format_version': 1,
                'source': {'release': 'BH2017-LOCRENASCI v0.2.0',
                           'runtime_manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                           'verified_runtime_files': verified,
                           'description': 'Editor fields derived from the locally built v0.2.0 runtime'},
                'catalog': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--native', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    document = generate(args.runtime, args.native)
    args.output.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')) + '\n', encoding='utf-8')
    print('Wrote', args.output, 'with', len(document['catalog']['stages']), 'stages')


if __name__ == '__main__':
    main()
