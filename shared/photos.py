"""Fetch openly licensed reference photos from Wikimedia Commons and write credits.json.

Usage from an episode:  python ../../../shared/photos.py <assets_dir> name=File_title.jpg ...
Images are saved as <assets_dir>/<name>.jpg (1280 px wide thumbs, not committed); credits.json lists file, source URL, licence and author for each one so the end card and description can credit them.
--original also saves the full-size original as <name>_original.<ext> and makes <name>.jpg from it with Lanczos
(no second download); credits.json then names the original and carries a ready attribution line.
--any keeps files whatever their licence (still recorded in credits.json); --enwiki looks files up on English
Wikipedia, which also hosts non-free press and archive photos.
"""
import json, os, re, subprocess, sys, time, urllib.parse

API = 'https://commons.wikimedia.org/w/api.php?'
UA = 'pixel-explainer-bot/1.0 (educational; https://github.com/YunRah2103/claude-code-videos)'
OPEN = ('CC0', 'Public domain', 'CC BY', 'CC BY-SA')   # licence prefixes we accept


def _get(url, binary=False, tries=9):
    for k in range(tries):                                # Commons rate-limits bursts: back off and retry
        time.sleep(4 * k + 2)
        out = subprocess.run(['curl', '-sS', '-L', '-m', '60', '-A', UA, url], capture_output=True).stdout
        if out and (binary and not out.startswith(b'<') or out.startswith(b'{')):
            return out if binary else json.loads(out)
    print(f'failed: {url}')


def _plain(html): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()


def fetch(out_dir, items, width=1280, any_licence=False, api=API, original=False):
    os.makedirs(out_dir, exist_ok=True)
    credits = []
    for name, title in items:
        q = dict(action='query', titles='File:' + title, prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth=width, format='json')
        r = _get(api + urllib.parse.urlencode(q))
        if not r: continue                                # rate-limited for good: leave it out of the credits
        info = next(iter(r['query']['pages'].values()))['imageinfo'][0]
        meta = info['extmetadata']
        lic = meta.get('LicenseShortName', {}).get('value', '')
        if not any_licence and not lic.startswith(OPEN):
            print(f'skip {title}: licence {lic!r}'); continue
        path = os.path.join(out_dir, name + '.jpg')
        url = info['url'].split('?')[0]
        orig = os.path.join(out_dir, name + '_original' + os.path.splitext(url)[1].lower())
        saved = 'original'
        if original and not os.path.isfile(orig):
            data = _get(url, binary=True, tries=3)
            for tw in (1280, 960):                        # originals throttled (HTTP 429): Commons asks for standard thumb sizes
                if data or info['width'] <= tw: break
                saved = f'{tw}px Commons rendering'
                data = _get(url.replace('/commons/', '/commons/thumb/') + f'/{tw}px-' + url.rsplit('/', 1)[1], binary=True, tries=3)
            if not data: continue
            open(orig, 'wb').write(data)
            json.dump(saved, open(orig + '.saved', 'w'))
        elif original and os.path.isfile(orig + '.saved'):
            saved = json.load(open(orig + '.saved'))
        if original and not os.path.isfile(path):
            from PIL import Image
            im = Image.open(orig).convert('RGB')
            if im.width > width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            im.save(path, quality=95)
        if not os.path.isfile(path):
            data = _get(info.get('thumburl') or info['url'], binary=True)
            if not data and width > 640:                  # originals under `width` are served unscaled and throttle harder
                return fetch(out_dir, items, 640, any_licence, api)
            if not data: continue
            open(path, 'wb').write(data)
        credits.append(dict(file=name + '.jpg', title=title, source=info['descriptionurl'], licence=lic,
                            licence_url=meta.get('LicenseUrl', {}).get('value', ''), author=_plain(meta.get('Artist', {}).get('value'))))
        if original:
            credits[-1].update(original=os.path.basename(orig), original_url=url, saved_as=saved,
                               attribution=f'{credits[-1]["author"]}, {lic}, via Wikimedia Commons')
        print(f'{name}: {lic} / {credits[-1]["author"]}')
    json.dump(credits, open(os.path.join(out_dir, 'credits.json'), 'w'), indent=1, ensure_ascii=False)
    return credits


if __name__ == '__main__':
    flags = [a for a in sys.argv[2:] if a.startswith('--')]
    api = 'https://en.wikipedia.org/w/api.php?' if '--enwiki' in flags else API
    fetch(sys.argv[1], [a.split('=', 1) for a in sys.argv[2:] if not a.startswith('--')], any_licence='--any' in flags, api=api, original='--original' in flags)
