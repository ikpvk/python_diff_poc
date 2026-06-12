import json
import sys
from pathlib import Path


def json_tree_diff(a, b):
    lines = []

    def _diff(a, b, prefix=""):
        if type(a) != type(b):
            lines.append(f"{prefix}{repr(a)} → {repr(b)}")
            return

        if isinstance(a, dict):
            entries = []
            for key in sorted(set(list(a.keys()) + list(b.keys()))):
                if key not in a:
                    entries.append(("+", key, b[key], None))
                elif key not in b:
                    entries.append(("-", key, a[key], None))
                elif a[key] != b[key]:
                    entries.append(("~", key, a[key], b[key]))

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
                    entries.append(("~", i, a[i], b[i]))

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
        yield rel if p.is_file() else rel / ""  # dirs get trailing /


def compare_dirs(dir1, dir2):
    p1, p2 = Path(dir1), Path(dir2)
    entries1 = set(walk_all(dir1))
    entries2 = set(walk_all(dir2))
    json_files1 = {f.relative_to(p1) for f in p1.rglob("*.json")}
    json_files2 = {f.relative_to(p2) for f in p2.rglob("*.json")}

    only_in_a = sorted(entries1 - entries2)
    only_in_b = sorted(entries2 - entries1)
    common = sorted(set(json_files1) & set(json_files2))

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

    for f in common:
        a = json.loads((p1 / f).read_text())
        b = json.loads((p2 / f).read_text())
        lines = json_tree_diff(a, b)
        if lines:
            mismatch_found = True
            out.append(f"{f}\n")
            for line in lines:
                out.append(f"{line}\n")
            out.append("\n")

    print("mismatches found" if mismatch_found else "fully matched")
    sys.stdout.write("".join(out))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_dirs.py <dir_a> <dir_b>")
        sys.exit(1)
    compare_dirs(sys.argv[1], sys.argv[2])
