"""Probe the Mini for whether it could host the automation browser.

Read-only. Answers three questions that decide the idea:
  1. Is Chrome even installed there?
  2. Is there a logged-in GUI (Aqua) session for it to run in? A headless ssh
     session cannot host a normal Chrome, and the extension needs a real one.
  3. Does the Mini's IP get bot-challenged? docs/TRAPS.md records that Amazon
     challenges the LRD network but not the laptop -- but that was measured with
     curl, and driven Chrome later worked on the laptop where curl failed. So
     the Mini's standing verdict is untested for the browser path.
"""
import getpass
import os
import subprocess


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


print("== host ==")
print("user      :", getpass.getuser())
print("hostname  :", run("hostname"))
print("macOS     :", run("sw_vers -productVersion"))
print("uptime    :", run("uptime"))

print("\n== browsers installed ==")
for app in ("Google Chrome", "Chromium", "Brave Browser", "Microsoft Edge", "Safari"):
    p = f"/Applications/{app}.app"
    print(f"  {app:18s} {'YES' if os.path.exists(p) else 'no'}")

print("\n== GUI session (needed to run a real browser) ==")
print("console user :", run("stat -f '%Su' /dev/console"))
print("who          :", run("who") or "(nobody)")
print("loginwindow  :", run("pgrep -l loginwindow") or "(none)")
print("Aqua session :", run("launchctl managername") or "(unknown)")

print("\n== is this IP bot-challenged? ==")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
for name, url in [
    ("amazon /dp", "https://www.amazon.com/dp/B09YHWKKTR"),
    ("amazon CDN", "https://m.media-amazon.com/images/I/51XR3NHux4L._AC_SL1500_.jpg"),
    ("mcmaster", "https://www.mcmaster.com/"),
]:
    out = run(f'curl -sS -o /dev/null -L --max-time 25 -A "{UA}" '
              f'-w "%{{http_code}} %{{size_download}} %{{content_type}}" "{url}"')
    print(f"  {name:12s} {out}")
