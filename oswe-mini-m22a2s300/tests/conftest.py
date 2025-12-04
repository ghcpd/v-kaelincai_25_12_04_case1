import time
import json
from pathlib import Path

start_time = time.time()


def pytest_sessionfinish(session, exitstatus):
    duration = time.time() - start_time
    results = {
        "total_tests": session.testscollected if hasattr(session, 'testscollected') else 'unknown',
        "exitstatus": exitstatus,
        "duration_seconds": duration
    }
    out = Path(session.config.rootpath) / "results" / "results_post.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
