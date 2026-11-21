"""Write CREDITS.txt for an episode from its Commons file pages (author + licence parsed from the HTML, one polite
request every 6 s). Usage: python credits.py EPISODE_DIR 'local.jpg=Commons file name' ..."""
import html, re, subprocess, sys, time, urllib.parse
UA = "YubCarVideos/1.0 (educational video pipeline)"
out = ["Photos and logos: Wikimedia Commons (downloaded via Special:FilePath). Used under the licences below.", ""]
def clean(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()
for arg in sys.argv[2:]:
    local, name = arg.split("=", 1)
    url = "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(name.replace(" ", "_"))
    page = subprocess.run(["curl", "-sSL", "-A", UA, url], capture_output=True, text=True).stdout
    aut = re.search(r'>\s*Author\s*</td>\s*<td[^>]*>(.*?)</td>', page, re.S)
    lic = sorted(set('CC ' + m[0].upper() + ' ' + m[1] for m in re.findall(r'creativecommons\.org/licenses/([a-z-]+)/([0-9.]+)', page)))
    if re.search(r'GNU Free Documentation License', page): lic.append('GFDL')
    pd = "Public domain" if not lic and re.search(r"public domain|PD-textlogo|PD-shape", page, re.I) else ""
    out += [f"{local}: \"{name}\"", f"  Author: {clean(aut.group(1)) if aut else 'see file page'}",
            f"  Licence: {', '.join(lic) or pd or 'see file page'}", f"  Source: {url}", ""]
    time.sleep(6)
open(sys.argv[1] + "/CREDITS.txt", "w").write("\n".join(out))
print("\n".join(out))
