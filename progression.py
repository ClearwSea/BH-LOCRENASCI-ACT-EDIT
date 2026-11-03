"""Bounded progression edits for the supported V1.9 offline save format."""
import json
from pathlib import Path
import time

CATALOG = json.loads((Path(__file__).with_name('stage_catalog.json')).read_text(encoding='utf-8'))
CYCLES = {'保持不变': None, '第一轮': 1, '第二轮': 2, '第三轮': 3, '第四轮 PART1': 4}
STORIES = {1:list(range(101,112)),2:list(range(201,208)),3:list(range(301,309)),4:list(range(401,412))}


def unlock(account, kind, now=None):
    if kind not in ('story','extra'):
        raise ValueError('未知关卡类型。')
    title = '剧情' if kind == 'story' else '外传'
    rows = account.get('stage_list')
    runtime = account.get('stage_runtime')
    if not isinstance(rows,list) or not isinstance(runtime,dict) or runtime.get('schema') != 1:
        raise ValueError('关卡存档结构不兼容。')
    if runtime.get('active') is not None:
        raise ValueError('请先结束当前关卡，再导出存档。')
    receipts=runtime.get('settlements')
    if not isinstance(receipts,list) or any(not isinstance(x,dict) or not isinstance(x.get('response',{}),dict) for x in receipts):
        raise ValueError('关卡记录格式不兼容。')
    if any(not isinstance(x,dict) or type(x.get('id')) is not int for x in rows):
        raise ValueError('关卡列表格式不兼容。')
    saved={x['id']:x for x in rows}
    if len(saved)!=len(rows):raise ValueError('存档有重复关卡，无法解锁。')
    selected=CATALOG[kind]
    ids={x['id'] for x in selected}
    if any(i not in ids for x in selected for i in x['pre']):
        raise ValueError('解锁模板缺少前置关卡。')
    min_level=max(x['level'] for x in selected)
    if kind=='extra':min_level=max(min_level,CATALOG['extra_level'])
    if type(account['main'].get('level')) is not int or account['main']['level']<min_level:
        raise ValueError(f'解锁全部{title}关卡需要舰长达到 {min_level} 级。')
    won={r.get('stage_id') for r in receipts if r.get('end_status')==1 and r.get('response',{}).get('retcode')==0 and r.get('response',{}).get('progress')==1}
    count=0
    for config in selected:
        i=config['id'];row=saved.get(i)
        if row is None:
            row={'id':i,'progress':0,'enter_times':0,'reset_times':0,'assist_enter_times':0,'challenge_index_list':[],'stamina_discount':100,'is_done':False}
            rows.append(row)
        old=list(row.get('challenge_index_list',[]))
        if any(type(n) is not int or not 0<=n<config['stars'] for n in old):
            raise ValueError('关卡星级结构与此版本不一致。')
        desired=list(range(config['stars']))
        if row.get('is_done') is not True or row.get('progress')!=1 or sorted(set(old))!=desired or i not in won:count+=1
        row.update(progress=1,is_done=True,challenge_index_list=desired)
        if i not in won:
            receipts.append({'stage_id':i,'end_status':1,'request_digest':f'editor-unlock-{i}',
                'response':{'retcode':0,'stage_id':i,'progress':1},
                'completed_at':int(time.time() if now is None else now),'source':'save_editor_unlock','rewards_granted':False})
    key = 'mission_runtime' if kind == 'story' else 'extra_achievement_runtime'
    task = account.setdefault(key, {'schema':1,'source_policy':CATALOG['mission_policy'],'claimed_ids':[],'receipts':[]} if kind == 'story' else {'claimed_ids':[],'receipts':[]})
    if not isinstance(task,dict) or not isinstance(task.get('claimed_ids'),list) or not isinstance(task.get('receipts'),list):
        raise ValueError('任务记录不兼容。')
    ids = CATALOG['story_missions' if kind == 'story' else 'extra_missions']
    if kind == 'story':
        if task.get('schema')!=1 or task.get('source_policy')!=CATALOG['mission_policy'] or any(i not in ids for i in task['claimed_ids']):
            raise ValueError('主线任务与当前模板不一致。')
        changed_claims=task['claimed_ids']!=ids
        task['claimed_ids']=list(ids)
    else:
        changed_claims=not set(ids)<=set(task['claimed_ids'])
        task['claimed_ids']=list(dict.fromkeys(task['claimed_ids']+ids))
    # Existing reward receipts and unrelated daily/weekly missions are preserved.
    mission_data=account.get('mission_data',{})
    if not isinstance(mission_data,dict):raise ValueError('任务列表格式不兼容。')
    if 'mission_list' in mission_data:
        if not isinstance(mission_data['mission_list'],list) or any(not isinstance(x,dict) for x in mission_data['mission_list']):
            raise ValueError('任务列表格式不兼容。')
        prior=mission_data['mission_list']
        mission_data['mission_list']=[x for x in prior if x.get('mission_id') not in ids]
        changed_claims=changed_claims or prior!=mission_data['mission_list']
    return f'{title}关卡全部通关：共 {len(selected)} 关，相关任务设为已领取（不补发奖励）' if count or changed_claims else None


def set_cycle(account, cycle):
    if cycle not in STORIES:raise ValueError('请选择第一轮至第四轮 PART1。')
    world=account.get('openworld_data');runtime=account.get('openworld_runtime')
    if not isinstance(world,dict) or not isinstance(runtime,dict) or runtime.get('schema')!=1:
        raise ValueError('请先在游戏中进入一次樱色轮回，再导出存档。')
    if runtime.get('active') is not None:
        raise ValueError('请先离开樱色轮回地图，再导出存档。')
    level={1:16,2:30,3:35,4:42}[cycle]
    if type(account['main'].get('level')) is not int or account['main']['level']<level:
        raise ValueError(f'该轮回需要舰长达到 {level} 级。')
    finished=world.get('finish_story_id_list');current=world.get('cur_story_list');receipts=runtime.get('receipts')
    if not isinstance(finished,list) or any(type(i) is not int for i in finished) or not isinstance(current,list) or not isinstance(receipts,dict):
        raise ValueError('轮回剧情记录格式不兼容。')
    known={i for v in STORIES.values() for i in v}
    # Unknown side-story state cannot safely be rewound with this bounded template.
    if any(i not in known for i in finished) or any(not isinstance(x,dict) or x.get('story_id') not in known for x in current):
        raise ValueError('存档包含模板范围外的轮回剧情，暂不支持修改。')
    before=[i for c,ids in STORIES.items() if c<cycle for i in ids]
    replay={i for c,ids in STORIES.items() if c>=cycle for i in ids}
    rewinding=bool(set(finished)&replay or any(str(i) in receipts for i in replay))
    world.update(cycle=cycle,finish_story_id_list=before,cur_story_list=[])
    # Existing receipt causes reward handler to return before completing replayed story.
    for i in replay:receipts.pop(str(i),None)
    # Story teams and position can otherwise refer to the later castle map.
    world.pop('spawn_point',None)
    runtime['area_teams']=[]
    # Preserve inventory, servant, commission state and already claimed cycle rewards.
    label=next(k for k,v in CYCLES.items() if v==cycle)
    text=f'樱色轮回：从{label}开头继续'
    if rewinding:text+='（重玩剧情可再次获得剧情奖励，已有物品不会扣除）'
    return text


RANKS = {'保持不变':None, '嚎叫深渊':1, '废土深渊':2, '禁忌深渊':3, '原罪深渊':4, '苦痛深渊':5, '红莲深渊':6, '无限深渊':7}


def set_rank(account, rank, now=None):
    if type(rank) is not int or rank not in range(1,8):
        raise ValueError('请选择七个段位之一。')
    state=account.get('endless_runtime')
    now=int(time.time() if now is None else now)
    if not isinstance(state,dict) or any(type(state.get(k)) is not int for k in ('begin','end','group')):
        raise ValueError('请先在游戏中进入深渊，再导出存档。')
    if not state['begin']<=now<state['end']:
        raise ValueError('请先在游戏中刷新本期深渊，再导出存档。')
    if 'active' not in state or state['active'] is not None:
        raise ValueError('请先结束深渊战斗，再导出存档。')
    if type(account['main'].get('level')) is not int or account['main']['level']<25:
        raise ValueError('深渊需要舰长达到25级。')
    if not 1<=state['group']<=7:raise ValueError('原段位不在支持范围内。')
    if state['group']==rank:return None
    state['group']=rank
    # The actual server state() rebinds the target tier's temperature/opponents
    # when display_temperature is absent. Do not ship NumPy or recreate its RNG.
    for key in ('display_temperature','climate_opponents','best_floor33_seconds'):
        state.pop(key,None)
    state['last_end']=None
    # Prior interactions refer to the old group's simulated members.
    for key,value in [('wars',[]),('bot_penalties',{}),('bombs',[])]:
        if key in state:state[key]=value
    return '深渊段位：'+next(k for k,v in RANKS.items() if v==rank)
