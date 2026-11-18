import copy
import json
from pathlib import Path
import tempfile
import unittest
from save_editor import edit, parse, save, Editor


def fixture():
    return {'schema':1, 'main':{'nickname':'测试','self_desc':'Hello','scoin':10,'hcoin':100,'stamina':10,'friends_point':5}, 'avatar_list':[], 'unknown':{'preserve':[1,2,3]}, 'endless_runtime':{'begin':100,'end':200,'progress':9,'max_progress':10,'progress_time':120,'active':None,'group':7,'claimed_floors':[1,2,3]}}

class Tests(unittest.TestCase):
    def test_allowlist_and_preservation(self):
        before=fixture()
        after, changes=edit(before,{'scoin':'1000'})
        expected=copy.deepcopy(before);expected['main']['scoin']=1000
        self.assertEqual(after,expected)
        self.assertEqual(before,fixture())
        with self.assertRaises(ValueError):edit(before,{'uid':'20'})
    def test_identity_read_only_with_unicode(self):
        a=fixture();a['main']['nickname']='😀'*4;before=copy.deepcopy(a)
        b,_=edit(a,{'nickname':'😀'*4})
        self.assertEqual(b,before)
        with self.assertRaisesRegex(ValueError,'游戏内'):
            edit(a,{'nickname':'😀'*5})
        self.assertEqual(a,before)
    def test_numeric_bounds(self):
        for value in ['-1','1.5','100000001','１２']:
            with self.assertRaises(ValueError):edit(fixture(),{'scoin':value})
    def test_template_scope(self):
        before=fixture();after,_=edit(before,{},31,150)
        expected=copy.deepcopy(before)
        expected['endless_runtime'].update(progress=31,max_progress=31,progress_time=150)
        self.assertEqual(after,expected)
    def test_template_guards(self):
        for now in [99,200]:
            with self.assertRaises(ValueError):edit(fixture(),{},31,now)
        data=fixture();data['endless_runtime']['active']={}
        with self.assertRaises(ValueError):edit(data,{},31,150)
    def test_bad_json(self):
        for raw in [b'{"schema":1,"schema":1}',b'{"main":NaN}',b'[]']:
            with self.assertRaises(ValueError):parse(raw)
    def test_backup_roundtrip_and_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'account.json';original=json.dumps(fixture()).encode();source.write_bytes(original)
            after,_=edit(fixture(),{'scoin':'999'})
            backup=save(source,original,source,after)
            self.assertEqual(backup.read_bytes(),original)
            self.assertEqual(parse(source.read_bytes()),after)
            with self.assertRaises(ValueError):save(source,original,source,fixture())
    def test_save_as_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'account.json';raw=json.dumps(fixture()).encode();source.write_bytes(raw)
            target=Path(d)/'new.json';save(source,raw,target,fixture())
            self.assertEqual(source.read_bytes(),raw)
            with self.assertRaises(ValueError):save(source,raw,target,fixture())

class CostumeTests(unittest.TestCase):
    def account(self):
        a=fixture();a['avatar_list']=[{'avatar_id':101,'dress_list':[99999],'dress_id':99999}, {'avatar_id':102,'dress_list':[]}]
        a['has_got_item_id_list']=[123,99999]
        return a

    def test_default_preserves_partial_ownership(self):
        a=self.account();self.assertEqual(edit(a,{})[0],a)

    def test_unlock_shared_and_preserve_unknown(self):
        from costumes import catalog
        a=self.account();before=copy.deepcopy(a);b,changes=edit(a,{},costumes=True)
        self.assertEqual(a,before);self.assertTrue(changes)
        self.assertEqual(len(b['avatar_list']),2)
        for av in b['avatar_list']:
            expected={r['dress_id'] for r in catalog() if av['avatar_id'] in r['avatar_ids']}
            self.assertTrue(expected<=set(av['dress_list']))
            self.assertTrue(expected<=set(b['has_got_item_id_list']))
        self.assertIn(99999,b['avatar_list'][0]['dress_list'])
        self.assertEqual(b['avatar_list'][0]['dress_id'],99999)
        self.assertEqual(edit(b,{},costumes=True),(b,[]))

    def test_lock_equipped_and_preserve_other_items(self):
        a,_=edit(self.account(),{},costumes=True);a['avatar_list'][0]['dress_id']=50019
        b,changes=edit(a,{},costumes=False)
        self.assertEqual(b['avatar_list'][0]['dress_list'],[99999])
        self.assertEqual(b['avatar_list'][0]['dress_id'],0)
        self.assertEqual(b['has_got_item_id_list'],[123,99999])
        self.assertEqual(b['unknown'],a['unknown']);self.assertTrue(changes)
        self.assertEqual(edit(b,{},costumes=False),(b,[]))

    def test_all46_experience_and_starter_scope(self):
        from save_editor import load_template
        from costumes import catalog
        self.assertEqual(len(catalog()),46)
        a=load_template('满级体验号');b,_=edit(a,{},costumes=True)
        self.assertTrue({r['dress_id'] for r in catalog()}<=set(b['has_got_item_id_list']))
        starter=load_template('新号');b,_=edit(starter,{},costumes=True)
        self.assertEqual(len(b['avatar_list']),len(starter['avatar_list']))
        self.assertEqual(b['main'],starter['main'])

    def test_malformed_is_atomic_and_ignored_when_unchanged(self):
        a=self.account();a['avatar_list'][1]['dress_list']=None;before=copy.deepcopy(a)
        with self.assertRaises(ValueError):edit(a,{},costumes=True)
        self.assertEqual(a,before);self.assertEqual(edit(a,{})[0],a)

    def test_save_roundtrip_and_backup(self):
        a=self.account();b,_=edit(a,{},costumes=True)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'account.json';raw=json.dumps(a).encode();p.write_bytes(raw)
            backup=save(p,raw,p,b)
            self.assertEqual(backup.read_bytes(),raw);self.assertEqual(parse(p.read_bytes()),b)

class ProgressionTests(unittest.TestCase):
    def world(self):
        a=fixture();a['main']['level']=80
        a['openworld_data']={'cycle':3,'finish_story_id_list':list(range(101,112))+list(range(201,208)), 'cur_story_list':[], 'servant_level':3, 'quest_data':{'keep':True}, 'spawn_point':'castle'}
        a['openworld_runtime']={'schema':1,'active':None,'receipts':{'101':{'reward':1}},'cycle_receipts':{'1':{'reward':2}},'area_teams':[]}
        return a
    def test_legacy_cycle_shortcut_rejected_atomically(self):
        before=self.world();snapshot=copy.deepcopy(before)
        with self.assertRaisesRegex(ValueError,'深度编辑'):
            edit(before,{},cycle=4)
        self.assertEqual(before,snapshot)
    def test_legacy_rewind_never_removes_story_receipts(self):
        a=self.world();a['openworld_runtime']['receipts']['301']={'reward':99}
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'深度编辑'):
            edit(a,{},cycle=3)
        self.assertEqual(a,before)
        self.assertEqual(a['openworld_runtime']['receipts']['301'],{'reward':99})
    def test_cycle_guards(self):
        a=self.world();a['openworld_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},cycle=4)
        a=self.world();a['main']['level']=41
        with self.assertRaises(ValueError):edit(a,{},cycle=4)
        with self.assertRaises(ValueError):edit(self.world(),{},cycle=5)
    def test_only_32_option(self):
        with self.assertRaises(ValueError):edit(fixture(),{},32,150)

class FullClearTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main']['level']=80
        a['stage_list']=[{'id':999999,'progress':0,'is_done':False}]
        a['stage_runtime']={'schema':1,'active':None,'settlements':[]}
        a['mission_data']={'mission_list':[{'mission_id':900000,'status':2}], 'daily_duty_point':15}
        return a
    def test_legacy_combined_shortcut_rejected_without_changing_save(self):
        a=self.account();before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'深度编辑'):
            edit(a,{},story=True,extra=True,now=150)
        self.assertEqual(a,before)
        self.assertEqual(a['stage_runtime']['settlements'],[])
    def test_each_legacy_full_clear_shortcut_is_rejected(self):
        for scope in ('story','extra'):
            a=self.account();before=copy.deepcopy(a)
            with self.subTest(scope=scope),self.assertRaisesRegex(ValueError,'深度编辑'):
                edit(a,{},**{scope:True})
            self.assertEqual(a,before)
    def test_active_and_low_level_rejected(self):
        a=self.account();a['stage_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},story=True)
        a=self.account();a['main']['level']=1
        with self.assertRaises(ValueError):edit(a,{},story=True)
    def test_unknown_mission_rejected_not_overwritten(self):
        a=self.account();a['mission_runtime']={'schema':1,'source_policy':'other','claimed_ids':[999],'receipts':[]}
        before=copy.deepcopy(a)
        with self.assertRaises(ValueError):edit(a,{},story=True)
        self.assertEqual(a,before)
    def test_existing_reward_receipts_preserved_when_shortcut_rejected(self):
        from progression import CATALOG
        a=self.account();receipt={'mission_id':10001,'keep':'existing'}
        a['mission_runtime']={'schema':1,'source_policy':CATALOG['mission_policy'],'claimed_ids':[10001],'receipts':[receipt]}
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'深度编辑'):
            edit(a,{},story=True)
        self.assertEqual(a,before)
        self.assertEqual(a['mission_runtime']['receipts'],[receipt])

class RankTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main']['level']=80
        a['endless_runtime'].update(display_temperature=35000,climate_opponents=[{'goal':3}],best_floor33_seconds=50,last_end={'old':1},wars=[1],items={'70001':2})
        a['endless_rewards']=[{'claimed':True}]
        return a
    def test_all_seven_ranks(self):
        for rank in range(1,8):
            a=self.account();b,_=edit(a,{},rank=rank,now=150)
            self.assertEqual(b['endless_runtime']['group'],rank)
            self.assertEqual(b['endless_runtime']['progress'],9)
            self.assertEqual(b['endless_runtime']['claimed_floors'],[1,2,3])
            self.assertEqual(b['endless_rewards'],a['endless_rewards'])
            self.assertEqual(b['endless_runtime']['items'],a['endless_runtime']['items'])
            if rank!=7:
                self.assertNotIn('display_temperature',b['endless_runtime'])
                self.assertNotIn('climate_opponents',b['endless_runtime'])
    def test_same_rank_noop(self):
        a=self.account();b,changes=edit(a,{},rank=7,now=150)
        self.assertEqual(a,b);self.assertFalse(changes)
    def test_rank_and_floor(self):
        b,_=edit(self.account(),{},31,150,rank=6)
        self.assertEqual((b['endless_runtime']['group'],b['endless_runtime']['progress']),(6,31))
    def test_rank_guards(self):
        for rank in (0,8,True):
            with self.assertRaises(ValueError):edit(self.account(),{},rank=rank,now=150)
        with self.assertRaises(ValueError):edit(self.account(),{},rank=6,now=200)
        a=self.account();a['endless_runtime']['active']={}
        with self.assertRaises(ValueError):edit(a,{},rank=6,now=150)

class TemplateTests(unittest.TestCase):
    def load(self,kind):
        from save_editor import load_template
        return load_template(kind)
    def test_identity_and_clean_history(self):
        for kind in ['新号','满级体验号']:
            a=self.load(kind)
            self.assertEqual(a['main']['nickname'],'免费版本禁止倒卖')
            self.assertEqual(a['main']['self_desc'],'开源免费版本，仅供学习与技术交流，禁止倒卖，版权归米哈游所有')
            self.assertEqual(len(a['main']['self_desc'].encode('utf-16-le'))//2,30)
            for key in ['gacha_runtime','local_recharge_runtime','wallet_limit_audit','development_test_adjustments','endless_test_history','endless_climate','sdk_account_name','player_card']:
                self.assertNotIn(key,a)
    def test_starter(self):
        a=self.load('新号')
        self.assertEqual(a['main']['level'],1)
        self.assertEqual(a['main']['stamina'],80)
        self.assertEqual(len(a['avatar_list']),1)
        self.assertEqual(a['avatar_list'][0]['avatar_id'],101)
        self.assertTrue(all(x['level']==1 for x in a['avatar_list']+a['weapon_list']))
        self.assertEqual(a['stigmata_list'],[])
        self.assertFalse(any(x['is_done'] for x in a['stage_list']))
    def test_experience(self):
        a=self.load('满级体验号');m=a['main']
        self.assertEqual((m['level'],m['stamina'],m['scoin'],m['hcoin']),(80,160,100000,1000))
        self.assertEqual(len(a['avatar_list']),26)
        self.assertTrue(all(x['level']==80 and x['star']==5 and x['touch_goodfeel']==60750 for x in a['avatar_list']))
        self.assertTrue(all(x['weapon_unique_id'] and all(x.get('stigmata_unique_id_'+str(i)) for i in (1,2,3)) for x in a['avatar_list']))
        self.assertEqual(len({i for x in a['avatar_list'] for i in x['dress_list']}),46)
        self.assertGreaterEqual(len(a['stage_list']),500)
        self.assertTrue(all(x['is_done'] and len(x['challenge_index_list'])==3 for x in a['stage_list']))
        self.assertEqual(a['stage_runtime']['settlements'],[])
        self.assertNotIn('openworld_data',a)
    def test_loadout_references(self):
        for kind in ['新号','满级体验号']:
            a=self.load(kind);weapons={r['unique_id'] for r in a['weapon_list']};stigs={r['unique_id'] for r in a['stigmata_list']}
            self.assertEqual(len(weapons),len(a['weapon_list']))
            self.assertEqual(len(stigs),len(a['stigmata_list']))
            self.assertFalse(weapons&stigs)
            for av in a['avatar_list']:
                self.assertIn(av['weapon_unique_id'],weapons)
                for k in ('stigmata_unique_id_1','stigmata_unique_id_2','stigmata_unique_id_3'):
                    self.assertIn(av[k],stigs|{0})
    def test_templates_are_independent_and_export_safe(self):
        from save_editor import save_new
        a=self.load('新号');a['main']['nickname']='变化'
        self.assertNotEqual(self.load('新号')['main']['nickname'],'变化')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'account.json';save_new(p,a);raw=p.read_bytes()
            with self.assertRaises(FileExistsError):save_new(p,self.load('满级体验号'))
            self.assertEqual(p.read_bytes(),raw)

class IdentityLockTests(unittest.TestCase):
    def test_template_identity_rejected_resources_allowed(self):
        from save_editor import load_template
        for kind in ['新号','满级体验号']:
            a=load_template(kind)
            for key in ['nickname','self_desc']:
                with self.assertRaisesRegex(ValueError,'游戏内'):edit(a,{key:'修改'})
            b,_=edit(a,{'nickname':a['main']['nickname'],'self_desc':a['main']['self_desc'],'scoin':'123'})
            self.assertEqual(b['main']['scoin'],123)
    def test_game_renamed_identity_preserved(self):
        from save_editor import load_template
        a=load_template('新号');a['main'].update(nickname='游戏改名',self_desc='游戏签名')
        b,_=edit(a,{'nickname':'游戏改名','self_desc':'游戏签名','scoin':'42'})
        self.assertEqual(b['main']['nickname'],'游戏改名')
        self.assertEqual(b['main']['self_desc'],'游戏签名')
    def test_normal_identity_is_read_only(self):
        a=fixture();before=copy.deepcopy(a)
        for key in ('nickname','self_desc'):
            with self.assertRaisesRegex(ValueError,'游戏内'):
                edit(a,{key:'改名'})
        self.assertEqual(a,before)
    def test_save_rejects_identity_change_before_writing(self):
        from save_editor import load_template
        for a in (load_template('新号'), fixture()):
            raw=json.dumps(a,ensure_ascii=False).encode('utf-8')
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'account.json';p.write_bytes(raw)
                a['main']['nickname']='修改'
                with self.assertRaisesRegex(ValueError,'游戏内'):save(p,raw,p,a)
                self.assertEqual(p.read_bytes(),raw)
                self.assertEqual(len(list(Path(d).iterdir())),1)

class CaptainLevelTests(unittest.TestCase):
    def account(self):
        a=fixture();a['main'].update(level=20,exp=123);return a
    def test_level_boundaries_and_scope(self):
        for level in [1,80]:
            a=self.account();b,_=edit(a,{'level':str(level)})
            expected=copy.deepcopy(a);expected['main'].update(level=level,exp=0)
            self.assertEqual(b,expected)
    def test_invalid_levels(self):
        for value in ['0','81','-1','1.5','abc']:
            with self.assertRaises(ValueError):edit(self.account(),{'level':value})
    def test_unchanged_level_preserves_exp(self):
        a=self.account();b,changes=edit(a,{'level':'20'})
        self.assertEqual(a,b);self.assertFalse(changes)
    def test_incompatible_exp_rejected(self):
        a=self.account();del a['main']['exp']
        with self.assertRaises(ValueError):edit(a,{'level':'80'})
    def test_lower_level_rejects_incompatible_avatar_and_preserves_original(self):
        from save_editor import load_template
        a=load_template('新号');a['main']['level']=80;a['avatar_list'][0]['level']=80
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'角色等级上限'):
            edit(a,{'level':'1'})
        self.assertEqual(a,before)

    def test_lower_level_rejects_incompatible_cabin_and_preserves_original(self):
        from save_editor import load_template
        a=load_template('新号');a['main']['level']=80
        a['cabin_list']=[{'type':4,'level':3,'extend_grade':1,'tech_list':[]}]
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'舱室 4'):
            edit(a,{'level':'1'})
        self.assertEqual(a,before)

    def test_basic_and_deep_captain_field_limits_agree(self):
        from save_editor import FIELDS,load_template
        from catalog_loader import load_catalog
        import editor_engine
        a=load_template('新号');bounds=editor_engine.limits(a,load_catalog())
        for key in ('level','scoin','hcoin','stamina','friends_point','equipment_size_limit'):
            with self.subTest(field=key):
                maximum=bounds[key]['max']
                self.assertEqual(FIELDS[key][1],maximum)
                changed,_=edit(a,{key:str(maximum)})
                self.assertEqual(changed['main'][key],maximum)
                with self.assertRaises(ValueError):
                    edit(a,{key:str(maximum+1)})

    def test_legacy_out_of_range_values_survive_unrelated_edits(self):
        from save_editor import load_template
        a=load_template('新号');a['main'].update(stamina=2000,hcoin=0x100000000,equipment_size_limit=0x100000000)
        before=copy.deepcopy(a)
        values={key:str(a['main'][key]) for key in ('stamina','hcoin','equipment_size_limit')}
        values['scoin']='50'
        edited,_=edit(a,values)
        for key in ('stamina','hcoin','equipment_size_limit'):
            self.assertEqual(edited['main'][key],before['main'][key])
        self.assertEqual(edited['main']['scoin'],50)
        self.assertEqual(a,before)
        for key in ('stamina','hcoin','equipment_size_limit'):
            with self.subTest(field=key),self.assertRaises(ValueError):
                edit(a,{key:str(before['main'][key]+1)})
        self.assertEqual(a,before)

    def test_legacy_missing_equipment_capacity_remains_absent(self):
        from save_editor import load_template
        a=load_template('新号');a['main'].pop('equipment_size_limit')
        for change in ({'scoin':'42'},{'level':'20'}):
            with self.subTest(change=change):
                changed,_=edit(a,change)
                self.assertNotIn('equipment_size_limit',changed['main'])
                self.assertNotIn('equipment_size_limit',a['main'])

    def test_template_level_preserves_progression(self):
        from save_editor import load_template
        a=load_template('新号');before=copy.deepcopy(a)
        b,_=edit(a,{'level':'80'})
        self.assertEqual(b['main']['level'],80)
        self.assertEqual(b['stage_list'],before['stage_list'])
        self.assertEqual(b['avatar_list'],before['avatar_list'])
        self.assertEqual(a,before)

if __name__=='__main__':unittest.main()


class InventoryAndAvatarTests(unittest.TestCase):
    def test_equipment_limit_bounds_and_auto_bump(self):
        from save_editor import load_template
        a = load_template('新号')
        a['main']['level'] = 23
        a['main']['equipment_size_limit'] = 100
        # Auto-bumps 100 -> 940 when level=23
        b, changes = edit(a, {'scoin': '10'})
        self.assertEqual(b['main']['equipment_size_limit'], 940)
        self.assertTrue(any('装备仓库上限' in c for c in changes))
        # Reject manual value below tier floor or owned equipment count
        a['weapon_list'] = [{'unique_id': i + 1, 'id': 20001, 'level': 1, 'exp': 0, 'is_protected': False} for i in range(960)]
        with self.assertRaisesRegex(ValueError, '960'):
            edit(a, {'equipment_size_limit': '940'})
        at_max, _ = edit(a, {'equipment_size_limit': str(0xffffffff)})
        self.assertEqual(at_max['main']['equipment_size_limit'], 0xffffffff)
        with self.assertRaisesRegex(ValueError, '4,294,967,295'):
            edit(a, {'equipment_size_limit': str(0x100000000)})
        c, _ = edit(a, {'equipment_size_limit': '1500'})
        self.assertEqual(c['main']['equipment_size_limit'], 1500)

    def test_avatar_edit_requires_captain_level_and_non_first_login(self):
        from save_editor import load_template
        a = load_template('新号')
        a['main']['level'] = 14
        with self.assertRaisesRegex(ValueError, '15'):
            edit(a, {}, avatar_edits={101: {'unlocked': True, 'level': 10, 'star': 3, 'full_equip': False}})
        a['main']['level'] = 20
        a['is_first_login'] = True
        with self.assertRaisesRegex(ValueError, '首次登录'):
            edit(a, {}, avatar_edits={101: {'unlocked': True, 'level': 10, 'star': 3, 'full_equip': False}})

    def test_avatar_unlock_awakened_star_level_and_full_equip(self):
        from save_editor import load_template
        a=load_template('新号');a['main']['level']=25
        with self.assertRaisesRegex(ValueError,'脉冲装·绯红'):
            edit(a,{},avatar_edits={211:{'unlocked':True,'level':20,'star':2,'full_equip':False}})
        with self.assertRaisesRegex(ValueError,'25'):
            edit(a,{},avatar_edits={101:{'unlocked':True,'level':30,'star':2,'full_equip':False}})
        with self.assertRaisesRegex(ValueError,'初始'):
            edit(a,{},avatar_edits={103:{'unlocked':True,'level':20,'star':2,'full_equip':False}})
        before=copy.deepcopy(a)
        with self.assertRaisesRegex(ValueError,'负载 54.*Lv.49'):
            edit(a,{},avatar_edits={
                201:{'unlocked':True,'level':20,'star':3,'full_equip':False},
                211:{'unlocked':True,'level':25,'star':4,'full_equip':True}})
        self.assertEqual(a,before)
        a['main']['level']=49
        b,changes=edit(a,{},avatar_edits={
            201:{'unlocked':True,'level':20,'star':3,'full_equip':False},
            211:{'unlocked':True,'level':49,'star':4,'full_equip':True}})
        by_id={x['avatar_id']:x for x in b['avatar_list']}
        self.assertEqual((by_id[211]['star'],by_id[211]['level']),(4,49))
        self.assertGreater(by_id[211]['weapon_unique_id'],0)
        for key in ('stigmata_unique_id_1','stigmata_unique_id_2','stigmata_unique_id_3'):
            self.assertGreater(by_id[211][key],0)
        weapons={w['unique_id'] for w in b['weapon_list']}
        stigmata={item['unique_id'] for item in b['stigmata_list']}
        self.assertIn(by_id[211]['weapon_unique_id'],weapons)
        self.assertTrue(all(by_id[211][key] in stigmata for key in ('stigmata_unique_id_1','stigmata_unique_id_2','stigmata_unique_id_3')))
        self.assertTrue(all(1 <= uid <= 19999 for uid in weapons))
        self.assertTrue(all(20001 <= uid <= 39999 for uid in stigmata))
        self.assertGreaterEqual(b['main']['equipment_size_limit'],500+48*20)
        self.assertTrue(any('推荐满装' in change for change in changes))
