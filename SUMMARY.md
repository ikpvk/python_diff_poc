# python_diff_poc

Compare two directories containing `.json` files and detect differences in a tree-structure format.

## Usage

```bash
python compare_dirs.py [--ignore <word>] <dir_a> <dir_b>
```

## Requirements

- Recursively walk both directories
- Detect files/directories present in one but not the other
- For `.json` files present in both, compare contents deeply (dicts + lists)
- Show differences in a tree-structure format using box-drawing characters:
  - `+ key: value` — new key (only in `dir_b`)
  - `- key: value` — removed key (only in `dir_a`)
  - `key: old → new` — changed value
  - `├──`/`└──`/`│` for tree hierarchy
  - Dirs get trailing `/` in "Only in" sections
- Print `"fully matched"` at top if no differences; `"mismatches found"` otherwise
- Ignore `.git` directories and their contents (files and subdirs inside `.git` are skipped)
- Optional `--ignore <word>` flag: directories, filenames, JSON keys, and string values that differ only by the word (as `word`, `word-`, `-word`, `-word-`) are treated as equal
- Zero external dependencies (stdlib only: `json`, `pathlib`, `sys`)

## Implementation

| Function | Purpose |
|---|---|---|
| `_strip_noise(s, noise)` | Strips the noise word from a string (exact, prefix `word-`, suffix `-word`, infix `-word-`) |
| `_noise_deep_eq(a, b, noise)` | Recursive deep equality check that accounts for noise in keys and string values |
| `_norm_path(p, noise)` | Normalizes each path component via `_strip_noise` |
| `json_tree_diff(a, b, noise=None)` | Recursively compares two JSON objects, returns tree-structure diff lines |
| `_diff(a, b, prefix)` | Inner recursive walker; handles dicts, lists, type mismatches, scalar changes |
| `walk_all(root)` | Generator yielding all entries (files + dirs) relative to root |
| `compare_dirs(dir1, dir2, noise=None)` | Orchestrator: collects entries, detects missing files/dirs, runs JSON diff, prints header + output |

## Sample Output

```
mismatches found
--- Only in dir_a ---
  + file3.json
  + sub/file7.json
  + tem_dir_1/
  + tem_dir_1/nested/

--- Only in dir_b ---
  + file4.json

file1.json
├── age: 30 → 31
├── + location: "remote"
├── role: "developer" → "senior developer"
└── skills
    └── + [3]: "kubernetes"
```
