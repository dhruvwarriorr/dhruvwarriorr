"""Live numbers for the README: Codeforces, LeetCode, CodeChef and GitHub.

Each source is fetched on every run and cached in data/stats.json, so a flaky API
never breaks the build: the last good value is reused instead.
"""
import json
import os
import re
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data', 'stats.json')
USER = 'dhruvwarriorr'


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0 (readme-renderer)', **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def gh_token():
    tok = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if tok:
        return tok
    try:
        return subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def fetch_codeforces():
    info = json.loads(http(f'https://codeforces.com/api/user.info?handles={USER}'))['result'][0]
    return dict(rating=info.get('rating', 0), rank=info.get('rank', 'unrated'))


def fetch_leetcode():
    q = 'query{userContestRanking(username:"%s"){rating badge{name}}}' % USER
    rank = json.loads(http('https://leetcode.com/graphql', json.dumps({'query': q}).encode(),
                           {'Content-Type': 'application/json', 'Referer': 'https://leetcode.com'}))['data']['userContestRanking']
    return dict(rating=round(rank['rating']), badge=(rank.get('badge') or {}).get('name') or 'Guardian')


def fetch_codechef():
    page = http(f'https://www.codechef.com/users/{USER}')
    rating = int(re.search(r'rating-number">\s*(\d+)', page).group(1))
    stars = re.search(r'rating-star">(.*?)</div>', page, re.S).group(1)
    return dict(rating=rating, stars=stars.count('&#9733;') or stars.count('★'))


def fetch_github():
    tok = gh_token()
    if not tok:
        raise RuntimeError('no GitHub token')
    q = '''query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{totalContributions}}
      repositories(ownerAffiliations:OWNER,privacy:PUBLIC,first:100){nodes{name stargazerCount isFork}}}}'''
    u = json.loads(http('https://api.github.com/graphql', json.dumps({'query': q, 'variables': {'u': USER}}).encode(),
                        {'Authorization': f'bearer {tok}', 'Content-Type': 'application/json'}))['data']['user']
    return dict(total=u['contributionsCollection']['contributionCalendar']['totalContributions'],
                repo_stars={r['name']: r['stargazerCount'] for r in u['repositories']['nodes'] if not r['isFork']})


def load_data():
    cache = {}
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            cache = json.load(f)
    for key, fn in [('codeforces', fetch_codeforces), ('leetcode', fetch_leetcode),
                    ('codechef', fetch_codechef), ('github', fetch_github)]:
        try:
            cache[key] = fn()
            print(f'✓ {key}')
        except Exception as e:
            if key not in cache:
                raise
            print(f'! {key}: {e} (using cached value)')
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, 'w') as f:
        json.dump(cache, f, indent=1)
        f.write('\n')
    return cache
