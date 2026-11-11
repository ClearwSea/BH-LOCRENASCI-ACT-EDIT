"""Edit ownership of the supported costume catalog without changing avatars."""
import json
from pathlib import Path

CHOICES = {'保持不变': None, '全部解锁': True, '全部锁定': False}


def catalog():
    return json.loads((Path(__file__).parent / 'costume_catalog.json').read_text(encoding='utf-8'))['dresses']


def set_costumes(account, unlocked):
    if type(unlocked) is not bool:
        raise ValueError('服装解锁选项无效。')
    rows = catalog()
    known = {row['dress_id'] for row in rows}
    obtained = account.get('has_got_item_id_list', [])
    if not isinstance(obtained, list) or any(type(x) is not int for x in obtained):
        raise ValueError('已获得物品列表格式不兼容。')
    added = removed = reset = 0
    granted = set()
    for avatar in account['avatar_list']:
        if not isinstance(avatar, dict) or type(avatar.get('avatar_id')) is not int:
            raise ValueError('角色列表格式不兼容。')
        owned = avatar.get('dress_list', [])
        if not isinstance(owned, list) or any(type(x) is not int for x in owned):
            raise ValueError('角色服装列表格式不兼容。')
        if unlocked:
            eligible = [row['dress_id'] for row in rows if avatar['avatar_id'] in row['avatar_ids']]
            granted.update(eligible)
            new = owned + [iid for iid in eligible if iid not in owned]
            added += len(new) - len(owned)
        else:
            new = [iid for iid in owned if iid not in known]
            removed += len(owned) - len(new)
            if avatar.get('dress_id', 0) in known:
                avatar['dress_id'] = 0
                reset += 1
        if new != owned:
            avatar['dress_list'] = new
    new_obtained = (obtained + sorted(granted - set(obtained)) if unlocked
                    else [iid for iid in obtained if iid not in known])
    changed_history = new_obtained != obtained
    if changed_history:
        account['has_got_item_id_list'] = new_obtained
    if not (added or removed or reset or changed_history):
        return None
    if unlocked:
        return f'服装：解锁已有角色的全部支持服装（新增 {added} 条角色持有记录）'
    return f'服装：锁定全部支持服装（移除 {removed} 条持有记录，{reset} 位角色换回默认）'
