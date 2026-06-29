import json
import sys
from pathlib import Path


def _strip_noise(s, noise):
    if not isinstance(s, str) or not noise:
        return s
    if s == noise:
        return ""
    if s.startswith(noise + "-"):
        s = s[len(noise) + 1:]
    infix = "-" + noise + "-"
    if infix in s:
        i = s.find(infix)
        s = s[:i] + s[i + len(infix) - 1:]  # collapse to single dash
    if s.endswith("-" + noise):
        s = s[:-(len(noise) + 1)]
    return s


def _noise_deep_eq(a, b, noise):
    if type(a) != type(b):
        return False
    if isinstance(a, str):
        return _strip_noise(a, noise) == _strip_noise(b, noise)
    if isinstance(a, dict):
        a_norm = {}
        for k in a:
            nk = _strip_noise(k, noise)
            if nk not in a_norm:
                a_norm[nk] = k
        b_norm = {}
        for k in b:
            nk = _strip_noise(k, noise)
            if nk not in b_norm:
                b_norm[nk] = k
        if set(a_norm) != set(b_norm):
            return False
        return all(_noise_deep_eq(a[a_norm[nk]], b[b_norm[nk]], noise) for nk in a_norm)
    if isinstance(a, list):
        return len(a) == len(b) and all(
            _noise_deep_eq(x, y, noise) for x, y in zip(a, b)
        )
    return a == b


def json_tree_diff(a, b, noise=None):
    lines = []

    def _diff(a, b, prefix=""):
        if type(a) != type(b):
            lines.append(f"{prefix}{repr(a)} → {repr(b)}")
            return

        if isinstance(a, dict):
            a_norm = {}
            for k in a:
                nk = _strip_noise(k, noise)
                if nk not in a_norm:
                    a_norm[nk] = k
            b_norm = {}
            for k in b:
                nk = _strip_noise(k, noise)
                if nk not in b_norm:
                    b_norm[nk] = k

            entries = []
            for nk in sorted(set(list(a_norm.keys()) + list(b_norm.keys()))):
                ak = a_norm.get(nk)
                bk = b_norm.get(nk)
                if ak is None:
                    entries.append(("+", nk, b[bk], None))
                elif bk is None:
                    entries.append(("-", nk, a[ak], None))
                else:
                    v1, v2 = a[ak], b[bk]
                    if v1 != v2 and not _noise_deep_eq(v1, v2, noise):
                        entries.append(("~", nk, v1, v2))

            for i, (kind, key, v1, v2) in enumerate(entries):
                is_last = i == len(entries) - 1
                conn = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if kind == "+":
                    lines.append(f"{prefix}{conn}+ {key}: {json.dumps(v1)}")
                elif kind == "-":
                    lines.append(f"{prefix}{conn}- {key}: {json.dumps(v1)}")
                elif kind == "~":
                    if isinstance(v1, (dict, list)):
                        lines.append(f"{prefix}{conn}{key}")
                        _diff(v1, v2, next_prefix)
                    else:
                        lines.append(f"{prefix}{conn}{key}: {json.dumps(v1)} → {json.dumps(v2)}")

        elif isinstance(a, list):
            entries = []
            max_len = max(len(a), len(b))
            for i in range(max_len):
                if i >= len(a):
                    entries.append(("+", i, b[i], None))
                elif i >= len(b):
                    entries.append(("-", i, a[i], None))
                elif a[i] != b[i]:
                    v1, v2 = a[i], b[i]
                    if _noise_deep_eq(v1, v2, noise):
                        continue
                    entries.append(("~", i, v1, v2))

            for j, (kind, idx, v1, v2) in enumerate(entries):
                is_last = j == len(entries) - 1
                conn = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if kind == "+":
                    lines.append(f"{prefix}{conn}+ [{idx}]: {json.dumps(v1)}")
                elif kind == "-":
                    lines.append(f"{prefix}{conn}- [{idx}]: {json.dumps(v1)}")
                elif kind == "~":
                    if isinstance(v1, (dict, list)):
                        lines.append(f"{prefix}{conn}[{idx}]")
                        _diff(v1, v2, next_prefix)
                    else:
                        lines.append(f"{prefix}{conn}[{idx}]: {json.dumps(v1)} → {json.dumps(v2)}")

    _diff(a, b, "")
    return lines


def walk_all(root):
    root = Path(root)
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if ".git" in rel.parts:
            continue
        yield rel if p.is_file() else rel / ""  # dirs get trailing /


def _norm_path(p, noise):
    return Path(*[_strip_noise(part, noise) for part in p.parts])


def compare_dirs(dir1, dir2, noise=None):
    p1, p2 = Path(dir1), Path(dir2)
    entries1 = list(walk_all(dir1))
    entries2 = list(walk_all(dir2))

    if noise:
        map1 = {_norm_path(e, noise): e for e in entries1}
        map2 = {_norm_path(e, noise): e for e in entries2}
        nk1, nk2 = set(map1), set(map2)
        only_in_a = sorted(map1[nk] for nk in sorted(nk1 - nk2))
        only_in_b = sorted(map2[nk] for nk in sorted(nk2 - nk1))
        common_keys = sorted(nk1 & nk2)
    else:
        s1, s2 = set(entries1), set(entries2)
        only_in_a = sorted(s1 - s2)
        only_in_b = sorted(s2 - s1)
        common_keys = sorted(s1 & s2)
        map1 = {e: e for e in entries1}
        map2 = {e: e for e in entries2}

    out = []
    mismatch_found = bool(only_in_a or only_in_b)

    if only_in_a:
        out.append(f"--- Only in {dir1} ---\n")
        for f in only_in_a:
            out.append(f"  + {f}\n")
        out.append("\n")

    if only_in_b:
        out.append(f"--- Only in {dir2} ---\n")
        for f in only_in_b:
            out.append(f"  + {f}\n")
        out.append("\n")

    for nk in common_keys:
        orig_a, orig_b = map1[nk], map2[nk]
        if not str(orig_a).endswith(".json") or not str(orig_b).endswith(".json"):
            continue
        a = json.loads((p1 / orig_a).read_text())
        b = json.loads((p2 / orig_b).read_text())
        lines = json_tree_diff(a, b, noise)
        if lines:
            mismatch_found = True
            out.append(f"{nk}\n")
            for line in lines:
                out.append(f"{line}\n")
            out.append("\n")

    print("mismatches found" if mismatch_found else "fully matched")
    sys.stdout.write("".join(out))


if __name__ == "__main__":
    args = sys.argv[1:]
    noise = None
    if len(args) >= 4 and args[0] == "--ignore":
        noise = args[1]
        dirs = args[2:4]
    elif len(args) == 2:
        dirs = args
    else:
        print("Usage: python compare_dirs.py [--ignore <word>] <dir_a> <dir_b>")
        sys.exit(1)
    compare_dirs(dirs[0], dirs[1], noise)
