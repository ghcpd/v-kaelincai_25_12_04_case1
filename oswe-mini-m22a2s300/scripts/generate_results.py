#!/usr/bin/env python3
import subprocess, json, sys, time
start=time.time()
res = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
end=time.time()
report={
    "returncode": res.returncode,
    "stdout": res.stdout,
    "stderr": res.stderr,
    "duration_s": end-start
}
with open("results/run_report.json","w",encoding="utf-8") as f:
    json.dump(report,f,indent=2)
print("Wrote results/run_report.json")
