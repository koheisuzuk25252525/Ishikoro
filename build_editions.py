# つかいかた: python3 build_editions.py "あいことば" "https://xxxx.booth.pm/items/123"
import sys, subprocess, json, re
src = open('/home/claude/web/ishikoro.html').read()
pw = sys.argv[1] if len(sys.argv) > 1 else ""
shop = sys.argv[2] if len(sys.argv) > 2 else ""
m = re.search(r'const hashPass = str => \{.*?toString\(36\); \};', src, re.S)
js = m.group(0) + f'\nconsole.log(hashPass({json.dumps(pw)}.trim().normalize("NFKC")))'
h = subprocess.run(['node', '-e', js], capture_output=True, text=True).stdout.strip() if pw else ""
def ed(s, edition, passh):
    s = s.replace('<title>いしころ戦記</title>', '<title>いしころ戦記 ' + ('体験版' if edition == 'trial' else '製品版') + '</title>', 1)
    s = s.replace('const EDITION = "family";', f'const EDITION = "{edition}";', 1)
    s = s.replace('const PASS_HASH = "";', f'const PASS_HASH = "{passh}";', 1)
    s = s.replace('const SHOP_URL = "";', f'const SHOP_URL = {json.dumps(shop)};', 1)
    return s
open('/home/claude/web/dist/ishikoro_trial.html', 'w').write(ed(src, "trial", ""))
open('/home/claude/web/dist/ishikoro_full.html', 'w').write(ed(src, "full", h))
print("hash", h)
