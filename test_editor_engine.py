import copy
import unittest

import editor_engine as editor


def fixture():
    account = {'main': {'level': 10}, 'unknown': {'kept': True},
               'avatar_list': [
                   {'avatar_id': 101, 'star': 1, 'level': 1, 'weapon_unique_id': 1,
                    'skill_list': [{'skill_id': 11, 'sub_skill_list': [{'sub_skill_id': 111, 'level': 4, 'is_mask': False}]}]},
                   {'avatar_id': 102, 'star': 1, 'level': 1, 'weapon_unique_id': 2,
                    'skill_list': [{'skill_id': 12, 'sub_skill_list': [{'sub_skill_id': 121, 'level': 4, 'is_mask': False}]}]}],
               'weapon_list': [{'unique_id': 1, 'id': 501, 'level': 1, 'exp': 0, 'is_protected': False},
                               {'unique_id': 2, 'id': 501, 'level': 1, 'exp': 0, 'is_protected': False}],
               'stigmata_list': [{'unique_id': 20001, 'id': 601, 'level': 1, 'exp': 0, 'is_protected': False}],
               'material_list': [{'id': 701, 'num': 30}]}
    tables = {'avatardata': [
                  {'avatarID': 101, 'unlockStar': 1, 'avatarFragmentID': 801, 'skillList': [11], 'initialWeapon': 501, 'weaponBaseTypeList': [1]},
                  {'avatarID': 102, 'unlockStar': 1, 'avatarFragmentID': 802, 'skillList': [12], 'initialWeapon': 501, 'weaponBaseTypeList': [1]}],
              'avatarexdata': [{'avatarIDList': [101, 102], 'commonSubSkillList': [{'Skill1': '101-11-111', 'Skill2': '102-12-121'}]}],
              'avatarsubskilldata': [{'avatarSubSkillId': 111, 'skillId': 11, 'maxLv': 5}, {'avatarSubSkillId': 121, 'skillId': 12, 'maxLv': 5}],
              'dressdata': [{'dressID': 901, 'dressType': 1, 'avatarIDList': [101, 102]}],
              'weapondata': [{'ID': 501, 'maxLv': 10, 'expType': 1, 'baseType': 1, 'cost': 1}],
              'stigmatadata': [{'ID': 601, 'maxLv': 10, 'expType': 1, 'baseType': 1, 'cost': 1}],
              'equipmentleveldata': [{'level': i, 'Type1': [0, 100]} for i in range(1, 11)],
              'avatarleveldata': [{'level': i, 'cost': 10} for i in range(1, 11)],
              'playerleveldata': [{'level': 10, 'avatarLevelLimit': 10}],
              'avatarfragmentdata': [{'ID': 801, 'quantityLimit': 99}, {'ID': 802, 'quantityLimit': 99}],
              'materialdata': [{'ID': 701, 'quantityLimit': 100}]}
    return account, tables


class InventoryEditorTest(unittest.TestCase):
    def setUp(self):
        self.account, self.tables = fixture()

    def test_shared_skill_downgrade_is_atomic(self):
        before = copy.deepcopy(self.account)
        changed = editor.apply(self.account, self.tables, {'type': 'skill', 'avatar_id': 101, 'skill_id': 11, 'sub_skill_id': 111, 'level': 2})
        self.assertEqual(self.account, before)
        self.assertEqual([a['skill_list'][0]['sub_skill_list'][0]['level'] for a in changed['avatar_list']], [2, 2])
        self.assertEqual(changed['unknown'], {'kept': True})

    def test_ranges_and_worn_weapon_deletion(self):
        changed = editor.apply(self.account, self.tables, {'type': 'equipment_add', 'kind': 'weapon', 'id': 501})
        self.assertEqual(changed['weapon_list'][-1]['unique_id'], 3)
        with self.assertRaises(ValueError):
            editor.apply(changed, self.tables, {'type': 'equipment_delete', 'unique_id': 1})
        changed = editor.apply(changed, self.tables, {'type': 'equipment_delete', 'unique_id': 1, 'replacement_uid': 3})
        self.assertEqual(changed['avatar_list'][0]['weapon_unique_id'], 3)

    def test_costume_ownership_and_fallback(self):
        account = editor.apply(self.account, self.tables, {'type': 'costume_all', 'owned': True})
        account = editor.apply(account, self.tables, {'type': 'costume', 'avatar_id': 101, 'equip': 901})
        account = editor.apply(account, self.tables, {'type': 'costume', 'dress_id': 901, 'owned': False})
        self.assertEqual(account['avatar_list'][0]['dress_id'], 0)
        self.assertNotIn(901, account['has_got_item_id_list'])
        self.assertTrue(all(901 not in a['dress_list'] for a in account['avatar_list']))

    def test_weapon_exchange_keeps_both_characters_armed(self):
        changed = editor.apply(self.account, self.tables, {'op': 'equipment_exchange',
                                                          'avatar_id_1': 101, 'avatar_id_2': 102})
        self.assertEqual([a['weapon_unique_id'] for a in changed['avatar_list']], [2, 1])

    def test_material_cap_and_batch_does_not_reduce(self):
        changed = editor.apply(self.account, self.tables, {'type': 'materials_batch', 'items': [{'id': 701, 'num': 20}]})
        self.assertEqual(changed['material_list'][0]['num'], 30)
        with self.assertRaises(ValueError):
            editor.apply(self.account, self.tables, {'type': 'material', 'id': 701, 'num': 101})

    def test_locked_battle_items_and_awakened_dependency(self):
        self.account['exboss_runtime'] = {'bosses': {'1': {'avatars': [101], 'weapons': [1], 'stigmata': []}}}
        with self.assertRaises(ValueError):
            editor.apply(self.account, self.tables, {'type': 'avatar', 'avatar_id': 101, 'star': 0})
        with self.assertRaises(ValueError):
            editor.apply(self.account, self.tables, {'type': 'equipment_delete', 'unique_id': 1})
        del self.account['exboss_runtime']
        with self.assertRaises(ValueError):
            editor.apply(self.account, self.tables, {'type': 'avatar', 'avatar_id': 101, 'star': 0})


def stage_row(identity, pre=(), stars=0):
    return {'id': identity, 'chapterId': 1, 'editor_chapter_id': 1, 'difficulty': 1,
            'unlockPlayerLevel': 1, 'unlockStarNum': stars, 'maxProgress': 1,
            'preLevelID': list(pre), 'challengeList': [{}, {}, {}], 'kind': 'story'}


class ProgressAndCaptainTest(unittest.TestCase):
    def test_progress_uses_editor_stars_without_false_settlement(self):
        source = {'main': {'level': 80}, 'stage_list': [],
                  'stage_runtime': {'schema': 1, 'active': None, 'settlements': []},
                  'mission_runtime': {'claimed_ids': [987]}, 'unknown': {'keep': True}}
        before = copy.deepcopy(source)
        catalog = {'stages': [stage_row(1), stage_row(2, [1]), stage_row(3, [2], 4)]}
        result = editor.apply(source, catalog, {'op': 'story_unlock', 'stage_id': 3})
        self.assertEqual(source, before)
        self.assertEqual(result['stage_runtime']['settlements'], [])
        self.assertEqual(result['mission_runtime'], before['mission_runtime'])
        self.assertEqual(sum(map(len, result['stage_editor_stars'].values())), 4)
        self.assertEqual(result['unknown'], before['unknown'])

    def test_sakura_requires_real_reward_receipts(self):
        source = {'main': {'level': 80}, 'openworld_data': {'cycle': 1,
                    'finish_story_id_list': [101, 102], 'cur_story_list': []},
                  'openworld_runtime': {'schema': 1, 'active': None, 'receipts': {'101': {}}}}
        catalog = {'sakura': {'cycle': {'level': 16}, 'stories': [
                  {'Cycle': 1, 'StoryID': 101}, {'Cycle': 1, 'StoryID': 102}]}}
        before = copy.deepcopy(source)
        with self.assertRaisesRegex(ValueError, '缺少领奖记录'):
            editor.apply(source, catalog, {'op': 'sakura_set_part', 'cycle': 1, 'story_id': 102})
        self.assertEqual(source, before)
        source['openworld_runtime']['receipts']['102'] = {'reward': {'scoin': 1}}
        result = editor.apply(source, catalog, {'op': 'sakura_set_part', 'cycle': 1, 'story_id': 102})
        self.assertEqual(result['openworld_runtime']['receipts'], source['openworld_runtime']['receipts'])

    def test_captain_skill_limit_includes_hub_bonus(self):
        source = {'main': {'level': 1, 'skill_point': 20, 'skill_point_limit': 65,
                           'equipment_size_limit': 500},
                  'cabin_list': [{'type': 4, 'level': 2, 'tech_list': [{'pos_x': 1, 'pos_y': 2}]}]}
        catalog = {'playerleveldata': [{'level': 1}, {'level': 80}],
                   'cabintechtreedata': [{'Cabin': 4, 'X': 1, 'Y': 2, 'AbilityType': 11,
                                           'UnlockLevel': 2, 'Argument1': 15}]}
        self.assertEqual(editor.limits(source, catalog)['skill_point_limit']['min'], 65)
        with self.assertRaisesRegex(ValueError, '技能点上限'):
            editor.apply(source, catalog, {'op': 'captain', 'skill_point_limit': 64})
        result = editor.apply(source, catalog, {'op': 'captain', 'skill_point_limit': 80, 'skill_point': 70})
        self.assertEqual((result['main']['skill_point_limit'], result['main']['skill_point']), (80, 70))
        self.assertEqual(result['skill_point_runtime']['interval'], 7200)
        self.assertEqual(source['main']['skill_point_limit'], 65)

    def test_locked_equipment_error_is_clear(self):
        account, catalog = fixture()
        account['exboss_runtime'] = {'bosses': {'1': {'avatars': [101], 'weapons': [1]}}}
        with self.assertRaisesRegex(ValueError, '记忆战场锁定'):
            editor.apply(account, catalog, {'op': 'equipment_delete', 'unique_id': 1})

    def test_template_creation_has_explicit_uid_and_no_external_io(self):
        catalog = {'playerleveldata': [{'level': 1, 'stamina': 80}],
                   'avatardata': [{'avatarID': 101, 'unlockStar': 1, 'initialWeapon': 501}]}
        original = {'uid': 42, 'opaque': {'preserve': True}}
        result = editor.apply(original, catalog, {'op': 'template', 'kind': 'starter_first_login'})
        self.assertEqual((result['uid'], result['is_first_login']), (42, True))
        self.assertEqual(original, {'uid': 42, 'opaque': {'preserve': True}})


class RealCatalogIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from catalog_loader import load_catalog
        cls.catalog = load_catalog()
        cls.full = editor.apply({'uid': 123456789}, cls.catalog,
                                {'op': 'template', 'kind': 'full_level'})

    def test_full_template_and_real_catalog_edits(self):
        self.assertGreaterEqual(len(self.full['avatar_list']), 26)
        self.assertGreaterEqual(len(self.full['stage_list']), 500)
        before = copy.deepcopy(self.full)
        account = editor.apply(self.full, self.catalog, {'op': 'captain', 'scoin': 12345})
        material = next(row for row in self.catalog['materialdata']
                        if type(row.get('quantityLimit')) is int and row['quantityLimit'] > 10 and
                        all(av.get('avatarFragmentID') != row['ID'] for av in self.catalog['avatardata']))
        account = editor.apply(account, self.catalog, {'op': 'material', 'id': material['ID'], 'num': 10})
        weapon_id = self.catalog['weapondata'][0]['ID']
        account = editor.apply(account, self.catalog, {'op': 'equipment_add', 'kind': 'weapon', 'id': weapon_id})
        uid = account['weapon_list'][-1]['unique_id']
        account = editor.apply(account, self.catalog, {'op': 'equipment_edit', 'unique_id': uid, 'is_protected': True})
        self.assertTrue(account['weapon_list'][-1]['is_protected'])
        account = editor.apply(account, self.catalog, {'op': 'equipment_delete', 'unique_id': uid})
        self.assertFalse(any(item['unique_id'] == uid for item in account['weapon_list']))
        self.assertEqual(account['main']['scoin'], 12345)
        self.assertEqual(self.full, before)

    def test_sakura_skip_and_abyss_keep_real_receipts(self):
        import time
        stories = sorted(row['StoryID'] for row in self.catalog['sakura']['stories'] if row['Cycle'] == 1)
        self.assertGreaterEqual(len(stories), 2)
        source = copy.deepcopy(self.full)
        source['openworld_data'] = {'cycle': 1, 'finish_story_id_list': [], 'cur_story_list': []}
        source['openworld_runtime'] = {'schema': 1, 'active': None, 'receipts': {}, 'cycle_receipts': {}}
        target = editor.apply(source, self.catalog, {'op': 'sakura_set_part', 'cycle': 1, 'story_id': stories[1]})
        self.assertIn(stories[0], target['openworld_editor_skipped'])
        self.assertEqual(target['openworld_runtime']['receipts'], {})
        now = int(time.time())
        source['endless_runtime'] = {'begin': now-100, 'end': now+100, 'group': 1,
                'progress': 1, 'max_progress': 3, 'progress_time': now, 'active': None,
                'claimed_floors': [1, 2]}
        target = editor.apply(source, self.catalog, {'op': 'abyss_set', 'group': 2, 'floor': 4})
        self.assertEqual(target['endless_runtime']['progress'], 3)
        self.assertEqual(target['endless_runtime']['claimed_floors'], [1, 2])


class LegacyAvatarIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from catalog_loader import load_catalog
        cls.catalog=load_catalog()
        cls.full=editor.apply({'uid':123456},cls.catalog,{'op':'template','kind':'full_level'})

    def test_locked_character_and_saved_team_remain_unchanged(self):
        from avatars import apply_avatar_edits
        for field in ('exboss_runtime','avatar_team_list'):
            account=copy.deepcopy(self.full)
            if field=='exboss_runtime':
                account[field]={'bosses':{'1':{'avatars':[102], 'weapons':[]}}}
                change={'unlocked':True,'level':79,'star':5,'full_equip':False}
                error='记忆战场锁定'
            else:
                account[field]=[{'avatar_id_list':[102]}]
                change={'unlocked':False,'level':80,'star':5,'full_equip':False}
                error='编队'
            before=copy.deepcopy(account)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,error):
                apply_avatar_edits(account,{102:change})
            self.assertEqual(account,before)

    def test_legacy_avatar_change_preserves_shared_skills(self):
        from avatars import apply_avatar_edits
        account=editor.apply(self.full,self.catalog,{'op':'skill','avatar_id':201,'skill_id':51,'sub_skill_id':501,'level':1})
        def skill_level(a,aid,skill_id,sub_id):
            avatar=next(x for x in a['avatar_list'] if x['avatar_id']==aid)
            skill=next(x for x in avatar['skill_list'] if x['skill_id']==skill_id)
            return next(x['level'] for x in skill['sub_skill_list'] if x['sub_skill_id']==sub_id)
        self.assertEqual(skill_level(account,201,51,501),1)
        self.assertEqual(skill_level(account,211,171,1701),1)
        apply_avatar_edits(account,{201:{'unlocked':True,'level':79,'star':5,'full_equip':False}})
        self.assertEqual(skill_level(account,201,51,501),1)
        self.assertEqual(skill_level(account,211,171,1701),1)

    def test_out_of_range_legacy_uid_is_not_rewritten(self):
        from avatars import apply_avatar_edits
        account=copy.deepcopy(self.full)
        old_uid=account['weapon_list'][0]['unique_id']
        account['weapon_list'][0]['unique_id']=20000
        for row in account['avatar_list']:
            if row.get('weapon_unique_id')==old_uid:
                row['weapon_unique_id']=20000
        before=copy.deepcopy(account)
        with self.assertRaisesRegex(ValueError,'装备编号'):
            apply_avatar_edits(account,{102:{'unlocked':True,'level':79,'star':5,'full_equip':False}})
        self.assertEqual(account,before)

    def test_full_template_recommendations_have_legal_unique_ids(self):
        from avatars import enrich_experience_template
        before=copy.deepcopy(self.full)
        result=enrich_experience_template(self.full,self.catalog)
        self.assertEqual(self.full,before)
        self.assertTrue(all(row['touch_goodfeel']==60750 for row in result['avatar_list']))
        self.assertTrue(all(row['weapon_unique_id'] and all(row.get('stigmata_unique_id_'+str(i)) for i in (1,2,3)) for row in result['avatar_list']))
        weapons=[row['unique_id'] for row in result['weapon_list']]
        stigmata=[row['unique_id'] for row in result['stigmata_list']]
        self.assertEqual(len(set(weapons)),len(weapons))
        self.assertEqual(len(set(stigmata)),len(stigmata))
        self.assertTrue(all(1<=uid<=19999 for uid in weapons))
        self.assertTrue(all(20001<=uid<=39999 for uid in stigmata))
        self.assertEqual(result['stage_runtime']['settlements'],[])


if __name__ == '__main__':
    unittest.main()
