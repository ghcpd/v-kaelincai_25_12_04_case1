import re
import json
from pathlib import Path

def parse_text(path: Path) -> dict:
    raw = path.read_bytes()
    # PowerShell redirection can create UTF-16 files; detect many null bytes and switch
    if raw.count(b"\x00") > len(raw) // 10:
        text = raw.decode('utf-16', errors='replace')
    else:
        text = raw.decode('utf-8', errors='replace')
    # find pattern like '5 passed in 0.13s' or '2 failed in 0.11s'
    m = re.search(r"(\d+) passed", text)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", text)
    failed = int(m.group(1)) if m else 0
    m = re.search(r"in ([0-9.]+)s", text)
    time_s = float(m.group(1)) if m else 0.0
    return {"passed": passed, "failed": failed, "duration_s": time_s, "raw": text}

if __name__ == '__main__':
    base = Path(__file__).resolve().parents[1] / 'results'
    pre = parse_text(base / 'results_pre.txt')
    post = parse_text(base / 'results_post.txt')
    agg = {
        'pre': pre,
        'post': post,
    }
    (base / 'aggregated_metrics.json').write_text(json.dumps(agg, indent=2), encoding='utf-8')
    print('Wrote', base / 'aggregated_metrics.json')
