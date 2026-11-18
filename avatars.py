"""Bounded valkyrie and recommended full-equipment edits for V1.9 offline saves."""
import copy
import json
from pathlib import Path

MIN_CAPTAIN_LEVEL = 15

STAR_LABELS = {1: 'B', 2: 'A', 3: 'S', 4: 'SS', 5: 'SSS'}
LABEL_TO_STAR = {v: k for k, v in STAR_LABELS.items()}

# (avatar_id, name, unlock_star, base_avatar_id, initial_weapon_id)
AVATAR_CATALOG = (
    (101, '领域装·白练', 1, 0, 20001),
    (102, '女武神·游侠', 2, 0, 20001),
    (103, '白骑士·月光', 3, 0, 20001),
    (104, '圣女祈祷', 2, 0, 20001),
    (112, '圣仪装·今样', 2, 101, 20001),
    (201, '脉冲装·绯红', 1, 0, 20041),
    (202, '影舞冲击', 2, 0, 20041),
    (203, '女武神·强袭', 2, 0, 20041),
    (204, '雷电女王的鬼铠', 3, 0, 20041),
    (211, '逆神巫女', 2, 201, 20041),
    (212, '御神装·勿忘', 3, 202, 20041),
    (213, '真炎幸魂', 2, 203, 20041),
    (301, '女武神·战车', 1, 0, 20243),
    (302, '驱动装·山吹', 2, 0, 20081),
    (303, '雪地狙击', 2, 0, 20081),
    (304, '次元边界突破', 3, 0, 20081),
    (311, '银狼的黎明', 2, 302, 20081),
    (312, '异度黑核侵蚀', 3, 303, 20081),
    (401, '女武神·凯旋', 2, 0, 20121),
    (402, '融核装·深红', 2, 0, 20121),
    (403, '战场疾风', 1, 0, 20121),
    (404, '血色玫瑰', 3, 0, 20121),
    (501, '女武神·誓约', 2, 0, 20430),
    (502, '处刑装·紫苑', 3, 0, 20430),
    (503, '樱火轮舞', 2, 0, 20430),
    (504, '神恩颂歌', 3, 0, 20430),
)

AVATAR_META = {
    aid: {
        'avatar_id': aid,
        'name': name,
        'unlock_star': unlock_star,
        'base_avatar_id': base_id,
        'initial_weapon_id': init_w,
    }
    for aid, name, unlock_star, base_id, init_w in AVATAR_CATALOG
}

_EXP_CACHE = None


def _experience_presets():
    """Load only equipment IDs and levels, without account or progress data."""
    global _EXP_CACHE
    if _EXP_CACHE is not None:
        return _EXP_CACHE
    path = Path(__file__).with_name('recommended_loadouts.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = data.get('loadouts')
    if data.get('version') != 1 or not isinstance(rows, dict):
        raise ValueError('推荐装备目录格式错误')
    try:
        _EXP_CACHE = {int(key): value for key, value in rows.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError('推荐装备目录包含无效角色 ID') from exc
    return _EXP_CACHE


def current_avatar_states(account):
    """Return a dict mapping each known avatar_id to its current editable state."""
    by_id = {
        row.get('avatar_id'): row
        for row in account.get('avatar_list', [])
        if isinstance(row, dict) and type(row.get('avatar_id')) is int
    }
    states = {}
    for aid, meta in AVATAR_META.items():
        row = by_id.get(aid)
        unlocked = bool(row and row.get('star', 0) > 0)
        star = row.get('star', 0) if unlocked else meta['unlock_star']
        star = max(meta['unlock_star'], min(5, star))
        level = max(1, min(80, row.get('level', 1))) if unlocked else 1
        states[aid] = {
            'unlocked': unlocked,
            'level': level,
            'star': star,
            'full_equip': False,
        }
    return states


def _catalog_row(catalog, table, key, value):
    rows = catalog.get(table)
    if not isinstance(rows, list):
        raise ValueError('当前版本缺少装备或角色目录：' + table)
    found = [row for row in rows if row.get(key) == value]
    if len(found) != 1:
        raise ValueError(f'当前目录缺少或重复记录：{key}={value}')
    return found[0]


def _recommended_cost(catalog, preset, avatar_id):
    weapon = preset.get('weapon')
    stigmata = preset.get('stigmata')
    if not isinstance(weapon, dict) or not isinstance(stigmata, list) or len(stigmata) != 3 or any(not isinstance(row, dict) for row in stigmata):
        raise ValueError('推荐装备数据不完整')
    avatar = _catalog_row(catalog, 'avatardata', 'avatarID', avatar_id)
    total = 0
    for slot, item in enumerate([weapon] + stigmata):
        table = 'weapondata' if slot == 0 else 'stigmatadata'
        row = _catalog_row(catalog, table, 'ID', item['id'])
        if type(item.get('level')) is not int or type(row.get('maxLv')) is not int or not 1 <= item['level'] <= row['maxLv']:
            raise ValueError('推荐装备等级超出当前版本允许范围')
        if slot == 0 and row.get('baseType') not in avatar.get('weaponBaseTypeList', []):
            raise ValueError('推荐武器不适合该角色')
        if slot and row.get('baseType') != slot:
            raise ValueError('推荐圣痕位置与当前目录不符')
        cost = row.get('cost')
        if type(cost) is not int or cost < 0:
            raise ValueError('推荐装备负载数据无效')
        total += cost
    return total


def _add_recommended(account, catalog, avatar_id, preset):
    # Delegate allocation, locks, levels, experience, slots and cost checks to
    # the same engine used by the detailed editor. Displaced items remain owned.
    import editor_engine
    account = copy.deepcopy(account)
    avatar = next(row for row in account['avatar_list'] if row['avatar_id'] == avatar_id)
    # Remove existing stigmata first so an otherwise legal new loadout is not
    # rejected due to the transient old-plus-new cost.
    for slot in (2, 3, 4):
        if avatar.get(f'stigmata_unique_id_{slot - 1}', 0):
            account = editor_engine.apply(account, catalog, {'op': 'equipment_equip',
                'avatar_id': avatar_id, 'slot': slot, 'unique_id': 0})
            avatar = next(row for row in account['avatar_list'] if row['avatar_id'] == avatar_id)
    for slot, item in enumerate([preset['weapon']] + preset['stigmata'], start=1):
        kind = 'weapon' if slot == 1 else 'stigmata'
        account = editor_engine.apply(account, catalog, {'op': 'equipment_add', 'kind': kind,
            'id': item['id'], 'level': item['level'], 'exp': 0, 'is_protected': True})
        uid = account[kind + '_list'][-1]['unique_id']
        account = editor_engine.apply(account, catalog, {'op': 'equipment_equip',
            'avatar_id': avatar_id, 'slot': slot, 'unique_id': uid})
    return account


def apply_avatar_edits(account, edits):
    """Apply legacy UI requests atomically through the V0.2.0 editor engine."""
    if not edits:
        return []
    if not isinstance(account, dict) or not isinstance(edits, dict):
        raise ValueError('存档或女武神编辑项格式错误。')
    captain_level = account.get('main', {}).get('level', 1)
    if type(captain_level) is not int or captain_level < MIN_CAPTAIN_LEVEL:
        raise ValueError(f'需舰长等级达到 {MIN_CAPTAIN_LEVEL} 级才可调整女武神，避免影响新手与家园引导。')
    if account.get('is_first_login') is True:
        raise ValueError('首次登录引导存档不可直接调整女武神。')
    import editor_engine
    from catalog_loader import load_catalog
    catalog = load_catalog()
    presets = _experience_presets()
    rows = account.get('avatar_list', [])
    if not isinstance(rows, list):
        raise ValueError('角色列表格式不兼容。')
    current = current_avatar_states(account)
    final_unlocked = {aid for aid, cur in current.items() if edits.get(aid, cur).get('unlocked')}
    final_unlocked.update(row['avatar_id'] for row in rows if isinstance(row, dict) and
                          type(row.get('avatar_id')) is int and row['avatar_id'] not in AVATAR_META and row.get('star', 0) > 0)
    if not final_unlocked:
        raise ValueError('至少需保留 1 位已解锁的女武神。')
    for aid in final_unlocked:
        meta = AVATAR_META.get(aid)
        if meta and meta['base_avatar_id'] and meta['base_avatar_id'] not in final_unlocked:
            raise ValueError(f'解锁觉醒女武神「{meta["name"]}」需先解锁基础角色「{AVATAR_META[meta["base_avatar_id"]]["name"]}」。')
    requests = []
    cap = _catalog_row(catalog, 'playerleveldata', 'level', captain_level).get('avatarLevelLimit')
    if type(cap) is not int or cap < 1:
        raise ValueError('当前舰长等级的角色等级上限不可用')
    for aid, cfg in edits.items():
        if aid not in AVATAR_META or not isinstance(cfg, dict):
            raise ValueError(f'不支持的女武神 ID 或配置：{aid}')
        meta, cur = AVATAR_META[aid], current[aid]
        want_unlocked = bool(cfg.get('unlocked'))
        want_level, want_star = cfg.get('level', cur['level']), cfg.get('star', cur['star'])
        want_full = bool(cfg.get('full_equip', False))
        if type(want_level) is not int or not 1 <= want_level <= cap:
            raise ValueError(f'「{meta["name"]}」等级须在 1–{cap} 之间。')
        if type(want_star) is not int or not meta['unlock_star'] <= want_star <= 5:
            raise ValueError(f'「{meta["name"]}」评阶不能低于初始 {STAR_LABELS[meta["unlock_star"]]} 级。')
        if want_full and not want_unlocked:
            raise ValueError(f'「{meta["name"]}」未解锁时不能勾选推荐满装。')
        if want_full:
            preset = presets.get(aid)
            if not preset:
                raise ValueError(f'缺少「{meta["name"]}」的推荐装备模板。')
            cost = _recommended_cost(catalog, preset, aid)
            row = _catalog_row(catalog, 'avatarleveldata', 'level', want_level)
            if type(row.get('cost')) is not int or cost > row['cost']:
                possible = [r['level'] for r in catalog['avatarleveldata'] if type(r.get('level')) is int and
                            type(r.get('cost')) is int and r['cost'] >= cost]
                minimum = f'，需至少达到 Lv.{min(possible)}' if possible else ''
                raise ValueError(f'「{meta["name"]}」推荐满装需要负载 {cost}，当前 Lv.{want_level} 上限为 {row.get("cost")}{minimum}。')
        requests.append((aid, cur, want_unlocked, want_level, want_star, want_full))
    # Unlock original forms first; lock awakened forms first. No hidden team
    # rewrites: engine rejects characters still referenced by saved teams.
    requests.sort(key=lambda v: (0 if not v[2] else 1,
                  -bool(AVATAR_META[v[0]]['base_avatar_id']) if not v[2]
                  else bool(AVATAR_META[v[0]]['base_avatar_id']), v[0]))
    result, changes = copy.deepcopy(account), []
    for aid, cur, unlocked, level, star, full in requests:
        meta = AVATAR_META[aid]
        if not unlocked:
            if cur['unlocked']:
                result = editor_engine.apply(result, catalog, {'op': 'avatar', 'avatar_id': aid, 'star': 0})
                changes.append(f'女武神「{meta["name"]}」：设为未解锁')
            continue
        if not cur['unlocked'] or cur['level'] != level or cur['star'] != star:
            result = editor_engine.apply(result, catalog, {'op': 'avatar', 'avatar_id': aid,
                                                          'star': star, 'level': level})
        if full:
            result = _add_recommended(result, catalog, aid, presets[aid])
        if not cur['unlocked'] or cur['level'] != level or cur['star'] != star or full:
            detail = '、推荐满装' if full else ''
            changes.append(f'女武神「{meta["name"]}」（Lv.{level} / {STAR_LABELS[star]}{detail}）')
    account.clear()
    account.update(result)
    return changes


def enrich_experience_template(account, catalog=None):
    """Return the full-level template with verified outfits and max affection.

    Recommendations are projected IDs and levels only. All items are created
    and equipped through the V0.2.0 engine; no legacy progress is copied.
    """
    import editor_engine
    if catalog is None:
        from catalog_loader import load_catalog
        catalog = load_catalog()
    if not isinstance(account, dict):
        raise ValueError('模板存档格式错误')
    result = copy.deepcopy(account)
    changes = {}
    for aid in AVATAR_META:
        row = next((r for r in result.get('avatar_list', []) if r.get('avatar_id') == aid), None)
        if not row or row.get('star', 0) <= 0:
            raise ValueError(f'满级模板缺少已解锁的女武神 {aid}')
        result = editor_engine.apply(result, catalog, {'op': 'avatar', 'avatar_id': aid,
                                                        'touch_goodfeel': 60750})
        changes[aid] = {'unlocked': True, 'level': row['level'], 'star': row['star'],
                        'full_equip': True}
    apply_avatar_edits(result, changes)
    return result
