"""One collector run, start to finish: collect, then recalculate and rebuild only what changed.

  collect.py            call the publishers that are due
  analyze.py            signals, forecasts, backtests      (only when a monthly series changed)
  verify_calcs.py       independent recompute; a mismatch stops the run before anything is published
  analyze_agency.py     spot prices, trade, federal demand (when agency data or monthly data changed)
  verify_agency.py
  build.py              pages and data/status.json

Exit code 0 with "publish=true" in GITHUB_OUTPUT means there is something new to publish.
"""
import json
import os
import subprocess
import sys

from paths import DATA, HERE


def step(script, *args):
    print(f"\n=== {script} {' '.join(args)}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / script), *args])
    if r.returncode:
        sys.exit(f"{script} failed (exit {r.returncode}); nothing was published")


def main():
    step("collect.py", *[a for a in sys.argv[1:] if a == "--all"])
    ch = json.loads((DATA / "changed.json").read_text())
    (DATA / "changed.json").unlink()
    if os.environ.get("MW_ONLY"):          # testing one publisher: keep the downloaded data, skip the rest
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
                fh.write("publish=true\n")
        return
    first = not (DATA / "analytics.json").exists()
    if ch["monthly"] or first or "--rebuild" in sys.argv:
        step("analyze.py")
        step("verify_calcs.py")
    if ch["monthly"] or ch["agency"] or first or not (DATA / "agency_analytics.json").exists() or "--rebuild" in sys.argv:
        step("analyze_agency.py")
        step("verify_agency.py")
    publish = ch["called"] or "--rebuild" in sys.argv
    if publish:
        step("build.py")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"publish={'true' if publish else 'false'}\n")
    print(f"\nrun finished: {len(ch['monthly'])} monthly series changed, agency changed {ch['agency']}, publish {publish}")


if __name__ == "__main__":
    main()
