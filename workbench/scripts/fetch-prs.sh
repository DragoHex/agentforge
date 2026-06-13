#!/usr/bin/env bash
# fetch-prs.sh
# Fetches active PRs for the current user in avi-dev and avi-test repos.
#
# Primary : gh pr list --author @me  (needs repo-scoped token)
# Fallback: git ls-remote over SSH   (works with fine-grained PATs missing org access)
#
# Output  : data/prs.json  { generated, avi_dev: [...], avi_test: [...] }

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/load-config.sh" "${PROJECT_ID:-}"

DATA_DIR="$WORKBENCH_DATA_DIR"
OUT_FILE="$DATA_DIR/prs.json"
TMPD=$(mktemp -d /tmp/wb_prs_XXXXXX)
trap 'rm -rf "$TMPD"' EXIT

mkdir -p "$DATA_DIR"
echo "Fetching active PRs..."

# ── Collect worktree directories ──────────────────────────────────────────────
dev_dirs_json="[]"
test_dirs_json="[]"

py_collect=$(python3 - "$WORKSPACE" "$AVI_DEV_REMOTE" "$AVI_TEST_REMOTE" <<'PYEOF'
import json, os, subprocess, sys
workspace     = sys.argv[1]
dev_remote    = sys.argv[2]
test_remote   = sys.argv[3]

dev_dirs = []; test_dirs = []
try:
    entries = sorted(os.listdir(workspace))
except FileNotFoundError:
    entries = []
for name in entries:
    d = os.path.join(workspace, name)
    git_d = os.path.join(d, '.git')
    if not (os.path.isdir(git_d) or os.path.isfile(git_d)):
        continue
    r = subprocess.run(['git','-C',d,'remote','get-url','origin'],
                       capture_output=True, text=True).stdout.strip()
    if r == dev_remote:
        dev_dirs.append(d)
    test_d = os.path.join(d, 'test')
    test_git = os.path.join(test_d, '.git')
    if os.path.isdir(test_git) or os.path.isfile(test_git):
        tr = subprocess.run(['git','-C',test_d,'remote','get-url','origin'],
                            capture_output=True, text=True).stdout.strip()
        if tr == test_remote:
            test_dirs.append(test_d)
print(json.dumps(dev_dirs))
print(json.dumps(test_dirs))
PYEOF
)
dev_dirs_json=$(echo  "$py_collect" | head -1)
test_dirs_json=$(echo "$py_collect" | tail -1)
echo "  avi-dev worktrees : $(echo "$dev_dirs_json"  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
echo "  avi-test locations: $(echo "$test_dirs_json" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"

# ── Try gh pr list ────────────────────────────────────────────────────────────
gh_prs() {
    local dir="$1"
    [[ -z "$dir" || ! -d "$dir" ]] && echo "[]" && return
    (cd "$dir" && GH_HOST="$GH_HOST" gh pr list \
        --author "@me" --state open --limit 50 \
        --json number,title,url,createdAt,updatedAt,body,reviewRequests,latestReviews,headRefName,baseRefName \
        2>/dev/null) || echo "[]"
}

first_dev=$(echo  "$dev_dirs_json"  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0] if d else "")')
first_test=$(echo "$test_dirs_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0] if d else "")')

DEV_GH=$(gh_prs  "$first_dev")
TEST_GH=$(gh_prs "$first_test")

DEV_CNT=$(echo  "$DEV_GH"  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)
TEST_CNT=$(echo "$TEST_GH" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)
echo "  gh: avi-dev=${DEV_CNT} PR(s), avi-test=${TEST_CNT} PR(s)"

# Write gh JSON to temp files for Python
echo "$DEV_GH"  > "$TMPD/dev_gh.json"
echo "$TEST_GH" > "$TMPD/test_gh.json"
echo "$dev_dirs_json"  > "$TMPD/dev_dirs.json"
echo "$test_dirs_json" > "$TMPD/test_dirs.json"

# ── Python: enrich gh data OR run git ls-remote fallback ─────────────────────
python3 - "$OUT_FILE" "$GH_HOST" "$DEV_CNT" "$TEST_CNT" "$TMPD" "$DSR_HOST" "$GH_ORG" "$GH_REPO_DEV" "$GH_REPO_TEST" <<'PYEOF'
import json, os, re, subprocess, sys, threading
from datetime import datetime, timezone

out_file    = sys.argv[1]
gh_host     = sys.argv[2]
dev_cnt     = int(sys.argv[3])
test_cnt    = int(sys.argv[4])
tmpd        = sys.argv[5]
dsr_host    = sys.argv[6]
gh_org      = sys.argv[7]
gh_repo_dev = sys.argv[8]
gh_repo_test= sys.argv[9]

dev_gh_prs  = json.load(open(f'{tmpd}/dev_gh.json'))
test_gh_prs = json.load(open(f'{tmpd}/test_gh.json'))
dev_dirs    = json.load(open(f'{tmpd}/dev_dirs.json'))
test_dirs   = json.load(open(f'{tmpd}/test_dirs.json'))

GH_TOKEN = ''
hosts_yml = os.path.expanduser('~/.config/gh/hosts.yml')
if os.path.exists(hosts_yml):
    for line in open(hosts_yml):
        if 'oauth_token' in line:
            GH_TOKEN = line.split(':',1)[1].strip()
            break

JIRA_RE    = re.compile(r'AV-\d+', re.I)          # no trailing \b: _ is \w so \bAV-123\b misses AV-123_foo
from urllib.parse import urlparse as _urlparse
_dsr_netloc = _urlparse(dsr_host).netloc or dsr_host
URL_RE     = re.compile(rf'https?://{re.escape(_dsr_netloc)}[^\s\)>\]"\']*', re.I)
ID_RE      = re.compile(r'/(?:requests?|runs?)/(\d+)', re.I)
BASE_BR_RE = re.compile(r'^(eng|main|master|\d+\.\d+|develop)', re.I)

def run(cmd, cwd=None, timeout=30):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return r.stdout.strip()

def dsr_kind(url): return 'dfr' if re.search(r'/dfr', url, re.I) else 'dsr'

# Fetch DSR runs once
dsr_runs = []
try:
    # 90 days / 100 entries to cover older PRs (DSR refs in PR descriptions
    # can be weeks or months old by the time we fetch the PR)
    raw = run(['dsr','list','--count','100','--duration','90'], timeout=30)
    dsr_runs = json.loads(raw) if raw else []
except Exception:
    pass

def dsr_for_branch(branch):
    jids = set(JIRA_RE.findall(branch))
    matched = []
    for r in dsr_runs:
        b = r.get('Branch','')
        # Exact match, or either branch name is a prefix/substring of the other,
        # or Jira ID from the local branch appears in the DSR branch name.
        if (b == branch or
                b in branch or              # DSR branch is a prefix of local branch
                branch in b or              # local branch is a prefix of DSR branch
                any(j in b for j in jids)): # Jira ID match (e.g. AV-260765)
            matched.append(r)
    # Sort by Request_ID descending → most recent first, then split DSR/DFR
    matched.sort(key=lambda r: r.get('Request_ID', 0), reverse=True)
    dsr_e, dfr_e = [], []
    for r in matched[:10]:
        rid = r.get('Request_ID')
        e = {'id': rid,
             'url': f'{dsr_host}/requests/{rid}' if rid else '',
             'status': r.get('Status',''), 'branch': r.get('Branch','')}
        (dfr_e if r.get('Request_Type','DSR').upper()=='DFR' else dsr_e).append(e)
    return dsr_e, dfr_e

def enrich_gh(pr, repo):
    body = pr.get('body') or ''; title = pr.get('title',''); branch = pr.get('headRefName','')
    urls = list(dict.fromkeys(URL_RE.findall(body)))
    dsr_e, dfr_e = [], []
    for url in urls:
        e = {'url': url}
        m = ID_RE.search(url)
        if m: e['id'] = int(m.group(1))
        (dfr_e if dsr_kind(url)=='dfr' else dsr_e).append(e)
    if not dsr_e and not dfr_e:
        dsr_e, dfr_e = dsr_for_branch(branch)
    jira_ids = list(dict.fromkeys(i.upper() for i in JIRA_RE.findall(f'{title} {branch} {body[:600]}') ))[:10]
    requested = {(r.get('login') or r.get('name') or '').strip()
                 for r in pr.get('reviewRequests',[])} - {''}
    latest_map = {(rv.get('author') or {}).get('login',''): rv
                  for rv in pr.get('latestReviews',[])
                  if (rv.get('author') or {}).get('login')}
    reviewers = [{'login': lg,
                  'state': latest_map[lg].get('state','REVIEW_REQUESTED')
                           if lg in latest_map else 'REVIEW_REQUESTED'}
                 for lg in sorted(requested | set(latest_map))]
    return {'number': pr.get('number'), 'title': title, 'url': pr.get('url',''),
            'repo': repo, 'branch': branch, 'base': pr.get('baseRefName',''),
            'created_at': pr.get('createdAt',''), 'updated_at': pr.get('updatedAt',''),
            'jira_ids': jira_ids, 'reviewers': reviewers, 'dsr': dsr_e, 'dfr': dfr_e}

def git_find_prs(repo_name, dirs):
    if not dirs: return []
    ref_dir = dirs[0]
    print(f'  [{repo_name}] Building PR map via git ls-remote…', flush=True)

    heads_lines = []; merge_lines = []
    def fetch_heads():
        heads_lines[:] = run(['git','-C',ref_dir,'ls-remote','origin','refs/pull/*/head'],
                              timeout=120).splitlines()
    def fetch_merges():
        merge_lines[:] = run(['git','-C',ref_dir,'ls-remote','origin','refs/pull/*/merge'],
                              timeout=120).splitlines()
    t1 = threading.Thread(target=fetch_heads)
    t2 = threading.Thread(target=fetch_merges)
    t1.start(); t2.start(); t1.join(); t2.join()

    sha_to_pr = {}
    for line in heads_lines:
        p = line.split('\t')
        if len(p) == 2:
            sha_to_pr[p[0]] = p[1].split('/')[2]

    open_prs = set()
    for line in merge_lines:
        p = line.split('\t')
        if len(p) == 2:
            open_prs.add(p[1].split('/')[2])

    print(f'  [{repo_name}] {len(sha_to_pr)} heads, {len(open_prs)} open (merge ref).', flush=True)

    branch_to_dir = {}
    for d in dirs:
        b = run(['git','-C',d,'branch','--show-current'])
        if b and not BASE_BR_RE.match(b):
            branch_to_dir[b] = d

    results = []; seen = set()
    for branch, wt in branch_to_dir.items():
        remote_sha = run(['git','-C',wt,'ls-remote','origin',f'refs/heads/{branch}']).split('\t')[0]
        local_sha  = run(['git','-C',wt,'rev-parse','HEAD'])
        search_sha = remote_sha or local_sha
        if not search_sha: continue

        pr_num = sha_to_pr.get(search_sha)
        if not pr_num or pr_num in seen: continue

        # Open heuristics (no REST API available):
        #  1) merge ref exists → definitely open (GitHub creates it when no conflict)
        #  2) remote branch still exists → likely open (not yet merged/deleted)
        #  3) exact local-SHA match → PR head = current local commit; branch likely open
        #     with merge conflict (no merge ref) and remote branch may be deleted by author
        exact_local = (not remote_sha and sha_to_pr.get(local_sha) == pr_num)
        is_open = pr_num in open_prs or bool(remote_sha) or exact_local
        if not is_open:
            continue
        seen.add(pr_num)

        print(f'  [{repo_name}] Fetching PR #{pr_num} commit (branch: {branch})…', flush=True)
        try:
            run(['git','-C',wt,'fetch','origin',f'refs/pull/{pr_num}/head'])
        except Exception:
            pass
        title = run(['git','-C',wt,'log','FETCH_HEAD','-1','--format=%s'])
        date  = run(['git','-C',wt,'log','FETCH_HEAD','-1','--format=%ai'])

        jira_ids = list(dict.fromkeys(i.upper() for i in JIRA_RE.findall(f'{branch} {title}')))[:10]
        pr_repo  = gh_repo_dev if repo_name == gh_repo_dev else gh_repo_test
        pr_path  = f'{gh_org}/{pr_repo}'
        dsr_e, dfr_e = dsr_for_branch(branch)

        results.append({
            'number': int(pr_num), 'title': title,
            'url':    f'https://{gh_host}/{pr_path}/pull/{pr_num}',
            'repo': repo_name, 'branch': branch, 'base': '',
            'created_at': date, 'updated_at': date,
            'jira_ids': jira_ids, 'reviewers': [],
            'dsr': dsr_e, 'dfr': dfr_e,
        })
    return results

# ── Assemble ──────────────────────────────────────────────────────────────────
dev_prs  = [enrich_gh(p, gh_repo_dev)  for p in dev_gh_prs]  if dev_cnt  > 0 else git_find_prs(gh_repo_dev,  dev_dirs)
test_prs = [enrich_gh(p, gh_repo_test) for p in test_gh_prs] if test_cnt > 0 else git_find_prs(gh_repo_test, test_dirs)

sk = lambda p: p.get('updated_at') or p.get('created_at') or ''
dev_prs.sort( key=sk, reverse=True)
test_prs.sort(key=sk, reverse=True)

output = {'generated': datetime.now(timezone.utc).isoformat(),
          'avi_dev': dev_prs, 'avi_test': test_prs}
with open(out_file,'w') as f:
    json.dump(output, f, indent=2)

print(f'  Written → {out_file}')
print(f'  avi-dev : {len(dev_prs)} PR(s)')
print(f'  avi-test: {len(test_prs)} PR(s)')
for p in dev_prs + test_prs:
    print(f'    #{p["number"]} [{p["repo"]}] {p["title"][:60]}')
PYEOF
