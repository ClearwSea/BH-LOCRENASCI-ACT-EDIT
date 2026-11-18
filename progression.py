"""Bounded progression edits for the supported V1.9 offline save format."""
import json
from pathlib import Path
import time

CATALOG = json.loads((Path(__file__).with_name('stage_catalog.json')).read_text(encoding='utf-8'))
CYCLES = {'保持不变': None, '第一轮': 1, '第二轮': 2, '第三轮': 3, '第四轮 PART1': 4}
STORIES = {1:list(range(101,112)),2:list(range(201,208)),3:list(range(301,309)),4:list(range(401,412))}


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
