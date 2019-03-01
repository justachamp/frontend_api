def set_value_at_keypath(obj, keypath, val):
    parts = keypath.split('.')
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = val
    return True
