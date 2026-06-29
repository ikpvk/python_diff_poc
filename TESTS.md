# Tests

Run with:

```bash
python test_compare_dirs.py
```

## Test Scenarios

### `_strip_noise(s, noise)` — unit tests

| Test | Input | Noise | Expected | Notes |
|------|-------|-------|----------|-------|
| exact match | `"xyz"` | `"xyz"` | `""` | String equals noise word |
| no match | `"hello"` | `"xyz"` | `"hello"` | Unrelated string unchanged |
| prefix | `"xyz-foo"` | `"xyz"` | `"foo"` | `word-` at start |
| suffix | `"foo-xyz"` | `"xyz"` | `"foo"` | `-word` at end |
| infix middle | `"foo-xyz-bar"` | `"xyz"` | `"foo-bar"` | `-word-` in middle, collapes to one dash |
| infix at end | `"foo-xyz-"` | `"xyz"` | `"foo"` | `-word-` at end, removed entirely |
| infix at start | `"-xyz-foo"` | `"xyz"` | `"foo"` | `-word-` at start |
| prefix + suffix | `"xyz-foo-xyz"` | `"xyz"` | `"foo"` | Both forms |
| trailing infix bug | `"name-dev-"` | `"dev"` | `"name"` | Regression: infix at end retains trailing dash |
| noise inside word | `"developer"` | `"dev"` | `"developer"` | No dash delimiters, not stripped |
| empty noise | `"hello"` | `""` | `"hello"` | No-op |
| None noise | `"hello"` | `None` | `"hello"` | No-op |
| non-string input | `42` | `"xyz"` | `42` | Passed through unchanged |

### `_noise_deep_eq(a, b, noise)` — unit tests

| Test | a | b | Noise | Expected | Notes |
|------|---|---|-------|----------|-------|
| strings equal | `"hello-xyz"` | `"hello"` | `"xyz"` | `True` | Values differ by noise only |
| strings different | `"hello-xyz"` | `"world"` | `"xyz"` | `False` | Genuine value difference |
| dicts noise keys | `{"xyz-a": 1}` | `{"a": 1}` | `"xyz"` | `True` | Keys differ by noise only |
| dicts noise key + value diff | `{"xyz-a": 1}` | `{"a": 2}` | `"xyz"` | `False` | Keys match, values differ |
| dicts extra noise key | `{"a": 1, "xyz-b": 2}` | `{"a": 1}` | `"xyz"` | `False` | Extra key in a |
| lists noise items | `["a-xyz", "b"]` | `["a", "b"]` | `"xyz"` | `True` | List items differ by noise |
| nested dicts | `{"a": {"xyz-b": 1}}` | `{"a": {"b": 1}}` | `"xyz"` | `True` | Deeply nested noise |
| nested lists in dict | `{"items": ["a-xyz"]}` | `{"items": ["a"]}` | `"xyz"` | `True` | Nested list items |
| type mismatch | `1` | `"1"` | `"xyz"` | `False` | Different types |
| no noise | `"hello"` | `"hello"` | `None` | `True` | Falls through to `==` |
| trailing infix | `{"name-dev-": "alice-dev"}` | `{"name": "alice"}` | `"dev"` | `True` | Regression: key and value both use trailing infix |

### `json_tree_diff(a, b, noise=None)` — unit tests

| Test | Scenario | Noise | Expected |
|------|----------|-------|----------|
| no diff | identical objects | None | `[]` |
| type mismatch | `int` vs `str` | None | 1 line with `→` |
| added key | key only in b | None | line with `+` |
| removed key | key only in a | None | line with `-` |
| changed value | value differs | None | line with `→` |
| noise matches keys | `name-dev-` ↔ `name` | `"dev"` | `[]` |
| noise matches values | `"hello-dev"` ↔ `"hello"` | `"dev"` | `[]` |
| noise matches list | `["a-dev"]` ↔ `["a"]` | `"dev"` | `[]` |
| trailing infix | `key-dev-` ↔ `key` | `"dev"` | `[]` |
| real diff persists | `real: 100 → 200` | `"xyz"` | line with `real` |
| no noise arg | `{"a": 1} → {"a": 2}` | None | 1 line |
| nested noise | `timeout-dev` ↔ `timeout` | `"dev"` | `[]` |
| nested real diff | `enabled: false → true` | `"dev"` | line with `enabled` |

### `compare_dirs(dir1, dir2, noise=None)` — integration tests

| Test | Scenario | Noise | Expected |
|------|----------|-------|----------|
| identical dirs | same file and content | None | `"fully matched"` |
| file only in a | one extra file | None | `"mismatches found"` + `"Only in"` |
| noise dir name | `xyz-f.json` ↔ `f.json` | `"xyz"` | `"fully matched"` |
| noise subdir | `xyz-sub/f.json` ↔ `sub/f.json` | `"xyz"` | `"fully matched"` |
| trailing infix | `name-dev-` ↔ `name` + `alice-dev` ↔ `alice` | `"dev"` | `"fully matched"` |
| real diff persists | `real: 100 → 200` | `"xyz"` | `"mismatches found"` + `"real"` |
| no noise arg | `{"a": 1} → {"a": 2}` | None | `"mismatches found"` |
| list noise | `["a-xyz"]` ↔ `["a"]` | `"xyz"` | `"fully matched"` |

### `walk_all(root)` — unit tests

| Test | Scenario | Expected |
|------|----------|----------|
| yields files and dirs | walk a populated tree | all entries present |
| skips .git | walk tree with .git | `.git` entries excluded |
