# -*- coding: utf-8 -*-
"""把 CKAD-Prepare.md 與 kodecloud/Exam-*.md 合併輸出成單一離線 HTML。

用法（在 repo 任何位置都可以執行）：

    python tools/build-html.py

要加一份新的筆記，只要在下面的 DOCS 加一行：
    (markdown 相對路徑, 錨點前綴, 側邊欄群組名稱, 群組上方小標)
錨點前綴讓各來源的 #q1 / #q10 不會互撞，取一個沒用過的短字串即可。
"""
import re, html, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DST = os.path.join(REPO, "CKAD-Prepare.html")

DOC_TITLE = 'CKAD 練習記錄'
DOC_LEDE = ('把「CKAD 20 題考古題」的練習過程，與 KodeKloud／CKAD 模擬測驗的作答記錄'
            '整合成一份可離線閱讀的筆記。左側可依來源切換，或用搜尋直接跳題。')

# (markdown path relative to REPO, anchor prefix, sidebar/group name, kicker)
DOCS = [
    ('CKAD-Prepare.md',            '',   '考古題 20 題',    'CKAD 考古題'),
    ('kodecloud/Exam-1.md',        'e1', '模擬測驗 Exam 1', 'KodeKloud'),
    ('kodecloud/Exam-2.md',        'e2', '模擬測驗 Exam 2', 'KodeKloud'),
    ('kodecloud/Exam-4.md',        'e4', '模擬測驗 Exam 4', 'KodeKloud'),
    ('kodecloud/Exam-ckad-A.md',   'ea', '模擬測驗 Exam A', 'CKAD'),
]
# markdown filename (as written in links) -> anchor prefix, for cross-doc links
DOC_BY_NAME = {}

# ---------------------------------------------------------------- CKAD 考綱分類
# 官方五大 Domain 與權重。考古題的歸類直接讀 md 裡既有的「對應考綱 Domain」，
# 模擬測驗沒有這個欄位，改用下面的 MOCK_DOMAIN 對照表。
DOMAINS = [
    ('d1', 'Application Design and Build', '應用設計與建置', 20,
     '容器映像檔、選對 workload 資源（Job/CronJob/Deployment）、多容器 Pod 設計模式、Volume'),
    ('d2', 'Application Deployment', '應用部署', 20,
     'Deployment 與 rolling update、回滾、blue/green 與 canary 等部署策略'),
    ('d3', 'Application Observability and Maintenance', '可觀測性與維運', 15,
     'liveness/readiness/startup 探針、日誌與事件、實際除錯流程'),
    ('d4', 'Application Environment, Configuration and Security', '環境、設定與安全', 25,
     'ConfigMap/Secret、requests/limits/quota、SecurityContext、ServiceAccount 與 RBAC'),
    ('d5', 'Services and Networking', '服務與網路', 20,
     'Service 各種類型與連線偵錯、Ingress、NetworkPolicy'),
]
DOMAIN_BY_EN = {
    'Application Design and Build': 'd1',
    'Application Deployment': 'd2',
    'Application Observability and Maintenance': 'd3',
    'Application Environment, Configuration and Security': 'd4',
    'Services and Networking': 'd5',
}
# 模擬測驗題目的考綱歸類：(文件前綴, 題號) -> domain key
MOCK_DOMAIN = {
    ('e1', '9'): 'd5',    # deny-all NetworkPolicy
    ('e1', '10'): 'd5',   # EndpointSlice 接叢集外服務
    ('e1', '12'): 'd5',   # ExternalName Service
    ('e2', '1'): 'd1',    # 多容器 Pod + emptyDir
    ('e2', '2'): 'd1',    # 多容器 Pod + env
    ('e2', '3'): 'd1',    # Job
    ('e2', '4'): 'd1',    # Pod annotation
    ('e2', '6'): 'd2',    # rollout undo
    ('e2', '10'): 'd5',   # Service + NetworkPolicy
    ('e2', '12'): 'd5',   # Service + NetworkPolicy
    ('e2', '13'): 'd4',   # SecurityContext / capabilities
    ('e2', '16'): 'd4',   # memory requests/limits
    ('e4', '1'): 'd4',    # privileged 模式
    ('e4', '2'): 'd1',    # hostPath PersistentVolume
    ('ea', '1'): 'd1',    # Job template
    ('ea', '2'): 'd1',    # CronJob
    ('ea', '3'): 'd5',    # Service + NetworkPolicy
    ('ea', '4'): 'd1',    # InitContainer + emptyDir
    ('ea', '5'): 'd2',    # rolling update / rollback
}
# 總覽卡片上的來源標籤
SRC_TAG = {'': '考古題', 'e1': 'Exam 1', 'e2': 'Exam 2', 'e4': 'Exam 4', 'ea': 'Exam A'}

# the document currently being rendered
CUR = {'prefix': '', 'dir': ''}

# ---------------------------------------------------------------- slug
_slug_seen = {}


def slug_base(text):
    t = re.sub(r'`([^`]*)`', r'\1', text)
    t = re.sub(r'\*\*([^*]*)\*\*', r'\1', t)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = t.lower()
    t = re.sub(r'[^\w\s-]', '', t, flags=re.UNICODE)
    return re.sub(r'\s', '-', t)


def qualify(frag, prefix):
    """Namespace a GitHub-style fragment with its document's prefix."""
    return ('%s-%s' % (prefix, frag)) if prefix else frag


def slug(text):
    t = qualify(slug_base(text), CUR['prefix'])
    if t in _slug_seen:
        _slug_seen[t] += 1
        t = '%s-%d' % (t, _slug_seen[t])
    else:
        _slug_seen[t] = 0
    return t


def esc(s):
    return html.escape(s, quote=False)


# ---------------------------------------------------------------- syntax highlight
BASH_KW = {'kubectl', 'docker', 'podman', 'buildah', 'skopeo', 'minikube', 'sudo', 'curl',
           'echo', 'cat', 'grep', 'egrep', 'sed', 'awk', 'cd', 'ls', 'cp', 'mv', 'rm', 'mkdir',
           'export', 'nano', 'vim', 'diff', 'tar', 'wget', 'for', 'do', 'done', 'if', 'then',
           'fi', 'while', 'chmod', 'head', 'tail', 'wc', 'sort', 'uniq', 'ifconfig'}


def _emit(toks):
    out = []
    for txt, cls in toks:
        if cls:
            out.append('<span class="t-%s">%s</span>' % (cls, esc(txt)))
        else:
            out.append(esc(txt))
    return ''.join(out)


def hl_bash(line):
    toks = []
    buf = []
    i, n = 0, len(line)

    def flush():
        if buf:
            toks.append((''.join(buf), None))
            del buf[:]

    while i < n:
        c = line[i]
        if c == '#' and (i == 0 or line[i - 1].isspace()):
            flush()
            toks.append((line[i:], 'c'))
            return _emit(toks)
        if c == '"' or c == "'":
            flush()
            q = c
            j = i + 1
            while j < n and line[j] != q:
                j += 2 if line[j] == '\\' else 1
            j = min(j + 1, n)
            toks.append((line[i:j], 's'))
            i = j
            continue
        m = re.match(r'--?[A-Za-z][\w.-]*', line[i:])
        if m and (i == 0 or line[i - 1] in ' \t|('):
            flush()
            toks.append((m.group(0), 'f'))
            i += m.end()
            continue
        m = re.match(r'[A-Za-z_][\w-]*', line[i:])
        if m:
            w = m.group(0)
            prev = line[i - 1] if i else ''
            if w in BASH_KW and not (prev.isalnum() or prev in '-_./='):
                flush()
                toks.append((w, 'k'))
            else:
                buf.append(w)
            i += m.end()
            continue
        m = re.match(r'\d+(\.\d+)*', line[i:])
        if m:
            prev = line[i - 1] if i else ''
            if not (prev.isalnum() or prev in '-_.'):
                flush()
                toks.append((m.group(0), 'n'))
                i += m.end()
                continue
        buf.append(c)
        i += 1
    flush()
    return _emit(toks)


def _yaml_val(v):
    if not v:
        return ''
    ci = v.find(' #')
    comment = ''
    if ci >= 0:
        comment = '<span class="t-c">%s</span>' % esc(v[ci:])
        v = v[:ci]
    if re.match(r'^\s*["\']', v):
        return '<span class="t-s">%s</span>' % esc(v) + comment
    if re.match(r'^\s*(true|false|null|~)\s*$', v, re.I):
        return '<span class="t-k">%s</span>' % esc(v) + comment
    if re.match(r'^\s*[\d.]+%?\s*$', v):
        return '<span class="t-n">%s</span>' % esc(v) + comment
    return '<span class="t-v">%s</span>' % esc(v) + comment


def hl_yaml(line):
    m = re.match(r'^(\s*)(#.*)$', line)
    if m:
        return esc(m.group(1)) + '<span class="t-c">%s</span>' % esc(m.group(2))
    m = re.match(r'^(\s*)((?:-\s+)*)([A-Za-z0-9_.\-/"\']+)(:)(\s*)(.*)$', line)
    if m:
        ind, dash, key, colon, sp, rest = m.groups()
        out = esc(ind)
        if dash:
            out += '<span class="t-p">%s</span>' % esc(dash)
        out += '<span class="t-key">%s</span><span class="t-p">%s</span>%s' % (esc(key), colon, esc(sp))
        return out + _yaml_val(rest)
    m = re.match(r'^(\s*)(-\s+)(.*)$', line)
    if m:
        return esc(m.group(1)) + '<span class="t-p">%s</span>' % esc(m.group(2)) + _yaml_val(m.group(3))
    return _yaml_val(line)


DOCKER_KW = ('FROM', 'LABEL', 'USER', 'RUN', 'COPY', 'ADD', 'CMD', 'ENTRYPOINT',
             'ENV', 'WORKDIR', 'EXPOSE', 'VOLUME', 'ARG', 'SHELL', 'HEALTHCHECK')


def hl_docker(line):
    m = re.match(r'^(\s*)(#.*)$', line)
    if m:
        return esc(m.group(1)) + '<span class="t-c">%s</span>' % esc(m.group(2))
    m = re.match(r'^(\s*)(%s)(\s+)(.*)$' % '|'.join(DOCKER_KW), line)
    if not m:
        return esc(line)
    ind, kw, sp, rest = m.groups()
    out = esc(ind) + '<span class="t-k">%s</span>%s' % (kw, esc(sp))
    pos = 0
    for sm in re.finditer(r'"[^"]*"', rest):
        out += esc(rest[pos:sm.start()])
        out += '<span class="t-s">%s</span>' % esc(sm.group(0))
        pos = sm.end()
    return out + esc(rest[pos:])


def highlight(lang, code_lines):
    fn = {'bash': hl_bash, 'yaml': hl_yaml, 'dockerfile': hl_docker}.get(lang)
    if not fn:
        return '\n'.join(esc(l) for l in code_lines)
    return '\n'.join(fn(l) for l in code_lines)


# ---------------------------------------------------------------- links
def resolve_href(href):
    """Map a markdown link onto the merged document.

    #frag                 -> this document's namespaced anchor
    Other-Doc.md#frag     -> that document's namespaced anchor (now inline)
    Other-Doc.md          -> that document's group header
    everything else       -> a path relative to the HTML at the repo root
    """
    if href.startswith('#'):
        return '#' + qualify(href[1:], CUR['prefix']), 'lk lk-in'
    m = re.match(r'^([^#]*\.md)(?:#(.*))?$', href, re.I)
    if m:
        name = m.group(1).split('/')[-1]
        if name in DOC_BY_NAME:
            prefix = DOC_BY_NAME[name]
            frag = m.group(2)
            if frag:
                return '#' + qualify(frag, prefix), 'lk lk-in'
            return '#grp-' + (prefix or 'main'), 'lk lk-in'
    if re.match(r'^[a-z]+:', href, re.I) or href.startswith('/'):
        return href, 'lk lk-file'
    # plain relative path: rebase from the source file's folder to the repo root
    rel = os.path.normpath(os.path.join(CUR['dir'], href)).replace('\\', '/')
    return rel.lstrip('./') or href, 'lk lk-file'


# ---------------------------------------------------------------- inline
INLINE = re.compile(r'(`[^`]+`)|(\[[^\]]*\]\([^)]+\))|(\*\*[^*]+\*\*)')


def inline(text, allow_link=True):
    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        code, link, bold = m.group(1), m.group(2), m.group(3)
        if code:
            out.append('<code>%s</code>' % esc(code[1:-1]))
        elif link:
            lm = re.match(r'\[([^\]]*)\]\(([^)]+)\)', link)
            label, href = lm.group(1), lm.group(2)
            if not allow_link:
                out.append(inline(label, False))
            else:
                href, cls = resolve_href(href)
                out.append('<a class="%s" href="%s">%s</a>' % (cls, esc(href), inline(label, False)))
        elif bold:
            out.append('<strong>%s</strong>' % inline(bold[2:-2], allow_link))
        pos = m.end()
    out.append(esc(text[pos:]))
    return ''.join(out)


def plain(text):
    t = re.sub(r'`([^`]*)`', r'\1', text)
    t = re.sub(r'\*\*([^*]*)\*\*', r'\1', t)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    return t


# ---------------------------------------------------------------- label blocks
LABELS = {
    # CKAD-Prepare.md
    '題目敘述': ('task', '題目敘述'),
    'Task': ('task', 'Task'),
    '情境（Context）': ('task', '情境 Context'),
    '備註（原題）': ('note', '備註（原題）'),
    '相關資源': ('ref', '相關資源'),
    '解法指令': ('solve', '解法指令'),
    '驗證': ('verify', '驗證'),
    '對應考綱 Domain': ('domain', '對應考綱 Domain'),
    '易錯點／踩坑筆記': ('pitfall', '易錯點／踩坑筆記'),
    'Quick Reference': ('quick', 'Quick Reference'),
    # kodecloud/Exam-*.md
    '題目': ('task', '題目'),
    '解法': ('solve', '解法'),
    '解法（YAML）': ('solve', '解法（YAML）'),
    '排查': ('debug', '排查'),
    '重點整理': ('pitfall', '重點整理'),
    '流量路徑圖': ('note', '流量路徑圖'),
    '先觀察現況': ('debug', '先觀察現況'),
}
LBL_RE = re.compile(r'^\*\*([^*]+)\*\*(：|:)?\s*(.*)$')


def label_of(line):
    m = LBL_RE.match(line.strip())
    if not m:
        return None
    raw, colon, rest = m.group(1).strip(), m.group(2), m.group(3).strip()
    if '：' in raw or ':' in raw:
        return None
    if raw in LABELS:
        cls, disp = LABELS[raw]
        return (cls, disp, rest)
    if len(plain(raw)) <= 24 and (colon or not rest):
        return ('plain', plain(raw), rest)
    return None


# ---------------------------------------------------------------- block parse
def parse(lines):
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            blocks.append(('h', len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        m = re.match(r'^```(\w*)\s*$', line)
        if m:
            lang = m.group(1)
            i += 1
            buf = []
            while i < n and not re.match(r'^```\s*$', lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            while buf and not buf[-1].strip():
                buf.pop()
            blocks.append(('code', lang, buf))
            continue
        if re.match(r'^---+\s*$', line):
            blocks.append(('hr',))
            i += 1
            continue
        if line.lstrip().startswith('|') and i + 1 < n and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i + 1]):
            rows = []
            while i < n and lines[i].lstrip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            blocks.append(('table', rows))
            continue
        if line.lstrip().startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            blocks.append(('quote', parse(buf)))
            continue
        m = re.match(r'^(\s*)([-*]|\d+[.)])\s+(.*)$', line)
        if m:
            ordered = bool(re.match(r'\d', m.group(2)))
            base = len(m.group(1))
            items = []          # each item: list of raw lines (first already dedented)
            offset = base + len(m.group(2)) + 1
            while i < n:
                cur = lines[i]
                if not cur.strip():
                    # blank line: keep the list open only if indented content follows
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and (lines[j].startswith(' ' * (base + 1))
                                  or re.match(r'^(\s*)([-*]|\d+[.)])\s+', lines[j])
                                  and len(re.match(r'^(\s*)', lines[j]).group(1)) == base):
                        if items:
                            items[-1].append('')
                        i = j
                        continue
                    break
                mm = re.match(r'^(\s*)([-*]|\d+[.)])\s+(.*)$', cur)
                if mm and len(mm.group(1)) == base:
                    items.append([mm.group(3)])
                    offset = base + len(mm.group(2)) + 1
                    i += 1
                    continue
                if cur.startswith(' ' * (base + 1)) and items:
                    strip_n = 0
                    while strip_n < offset and strip_n < len(cur) and cur[strip_n] == ' ':
                        strip_n += 1
                    items[-1].append(cur[strip_n:])
                    i += 1
                    continue
                break
            blocks.append(('list', ordered, [parse(raw) for raw in items]))
            continue
        buf = []
        while i < n and lines[i].strip() \
                and not re.match(r'^(#{1,6}\s|```|>|\||---+\s*$)', lines[i]) \
                and not re.match(r'^(\s*)([-*]|\d+[.)])\s+', lines[i]):
            buf.append(lines[i])
            i += 1
        if buf:
            blocks.append(('para', buf))
        else:
            i += 1
    return blocks


# ---------------------------------------------------------------- render
COPY_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="9" y="9" width="11" height="11" rx="2"/>'
            '<path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>')


def render_blocks(blocks, out):
    for b in blocks:
        t = b[0]
        if t == 'para':
            out.append('<p>%s</p>' % inline(' '.join(x.strip() for x in b[1])))
        elif t == 'code':
            lang = b[1] or 'text'
            body = highlight(b[1], b[2])
            out.append('<figure class="code">')
            out.append('<figcaption><span class="lang">%s</span>'
                       '<button class="copy" type="button" aria-label="複製這段程式碼">'
                       '%s<span>複製</span></button></figcaption>' % (esc(lang), COPY_SVG))
            out.append('<pre><code>%s</code></pre></figure>' % body)
        elif t == 'table':
            rows = b[1]
            head = [c.strip() for c in rows[0].strip('|').split('|')]
            out.append('<div class="tw"><table><thead><tr>')
            for c in head:
                out.append('<th>%s</th>' % inline(c))
            out.append('</tr></thead><tbody>')
            for r in rows[2:]:
                cells = [c.strip() for c in r.strip('|').split('|')]
                out.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in cells) + '</tr>')
            out.append('</tbody></table></div>')
        elif t == 'quote':
            out.append('<blockquote>')
            render_blocks(b[1], out)
            out.append('</blockquote>')
        elif t == 'list':
            tag = 'ol' if b[1] else 'ul'
            out.append('<%s>' % tag)
            for item in b[2]:
                out.append('<li>')
                if len(item) == 1 and item[0][0] == 'para':
                    out.append(inline(' '.join(x.strip() for x in item[0][1])))
                else:
                    render_blocks(item, out)
                out.append('</li>')
            out.append('</%s>' % tag)
        elif t == 'hr':
            out.append('<hr>')
    return out


K_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
         '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/>'
         '<path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/></svg>')

# ---------------------------------------------------------------- CKAD/ file panels
CKAD_DIR = os.path.join(REPO, 'CKAD')
# files the prose points at by exam path rather than by repo path
EXTRA_FOR_Q = {'3': ['CKAD/Dockerfile']}


def list_repo_files():
    found = {}
    for dirpath, _dirs, names in os.walk(CKAD_DIR):
        for nm in names:
            full = os.path.join(dirpath, nm)
            rel = os.path.relpath(full, REPO).replace('\\', '/')
            found[rel] = full
    return found


REPO_FILES = list_repo_files()


def files_for_section(num, text):
    """Explicit CKAD/... references in the prose + files whose name is prefixed
    with this question's number (04-… == 題目4)."""
    hits = []
    for ref in re.findall(r'CKAD/[A-Za-z0-9_./-]+', text):
        ref = ref.rstrip('.,;:）)')
        if ref in REPO_FILES and ref not in hits:
            hits.append(ref)
    if num:
        pat = re.compile(r'^0*%s[.\-]' % re.escape(num))
        for rel in REPO_FILES:
            base = rel.split('/')[-1]
            if rel.count('/') == 1 and pat.match(base) and rel not in hits:
                hits.append(rel)
        for rel in EXTRA_FOR_Q.get(num, []):
            if rel in REPO_FILES and rel not in hits:
                hits.append(rel)
    return sorted(hits)


def kind_of(rel):
    base = rel.split('/')[-1].lower()
    if base.endswith(('.yaml', '.yml')):
        return 'yaml', 'YAML'
    if base == 'dockerfile' or base.startswith('dockerfile'):
        return 'dockerfile', 'DOCKERFILE'
    return '', 'TEXT'


CHEV = ('<svg class="chev" viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M9 6l6 6-6 6"/></svg>')
DOC_SVG = ('<svg class="fico" viewBox="0 0 24 24" aria-hidden="true">'
           '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>'
           '<path d="M14 3v5h5"/></svg>')


def render_file_panels(rels, out):
    if not rels:
        return
    out.append('<div class="files">')
    out.append('<p class="files-h">此題的 YAML 檔案（點開可直接看內容）</p>')
    for rel in rels:
        try:
            body = open(REPO_FILES[rel], encoding='utf-8').read().replace('\r\n', '\n')
        except (OSError, UnicodeDecodeError):
            continue
        lines = body.split('\n')
        while lines and not lines[-1].strip():
            lines.pop()
        lang, label = kind_of(rel)
        name = rel.split('/')[-1]
        path = '/'.join(rel.split('/')[:-1])
        out.append('<details class="file">')
        out.append('<summary>%s%s<span class="fname">%s</span>'
                   '<span class="fpath">%s/</span>'
                   '<span class="fmeta">%s · %d 行</span></summary>'
                   % (CHEV, DOC_SVG, esc(name), esc(path), label, len(lines)))
        out.append('<div class="fbody"><figure class="code">')
        out.append('<figcaption><span class="lang">%s</span>'
                   '<button class="copy" type="button" aria-label="複製 %s 的內容">'
                   '%s<span>複製</span></button></figcaption>' % (esc(label), esc(name), COPY_SVG))
        out.append('<pre><code>%s</code></pre></figure></div></details>'
                   % highlight(lang, lines))
    out.append('</div>')


def render_doc(path, prefix, out, toc):
    """Render one markdown source into `out`; append its nav entries to `toc`.
    Returns (doc_title, intro_html, index_cards, section_count)."""
    CUR['prefix'] = prefix
    CUR['dir'] = os.path.dirname(path)
    full = os.path.join(REPO, path.replace('/', os.sep))
    raw = open(full, encoding='utf-8').read().replace('\r\n', '\n')
    blocks = parse(raw.split('\n'))

    doc_title, intro, idx_items = '', '', []
    start = 0
    if blocks and blocks[0][0] == 'h' and blocks[0][1] == 1:
        doc_title = plain(blocks[0][2])
        start = 1
    if start < len(blocks) and blocks[start][0] == 'para':
        intro = ' '.join(x.strip() for x in blocks[start][1])
        start += 1
    if start < len(blocks) and blocks[start][0] == 'list':
        for item in blocks[start][2]:
            if not item or item[0][0] != 'para':
                continue
            txt = ' '.join(x.strip() for x in item[0][1]).strip()
            m = re.match(r'^\[([^\]]*)\]\(([^)]+)\)$', txt)
            if m:
                idx_items.append((m.group(1), resolve_href(m.group(2))[0]))
        if idx_items:
            start += 1

    # per-section CKAD/ file references + 考綱 domain, keyed by the section's plain title
    section_files, section_domain = {}, {}
    for chunk in re.split(r'\n(?=## )', raw):
        if not chunk.startswith('## '):
            continue
        sec_title = plain(chunk.split('\n', 1)[0][3:].strip())
        m = re.match(r'^題目(\d+)', sec_title)
        # the numeric-prefix rule (04-… == 題目4) only applies to the 考古題 doc
        num = m.group(1) if (m and prefix == '') else ''
        section_files[sec_title] = files_for_section(num, chunk)
        dm = re.search(r'\*\*對應考綱 Domain\*\*[^\n]*\n+\s*`([^`]+)`', chunk)
        if dm:
            section_domain[sec_title] = DOMAIN_BY_EN.get(dm.group(1).strip(), '')

    state = {'sec': False, 'blk': None, 'files': []}
    nsec = 0

    def flush_files():
        if state['files']:
            render_file_panels(state['files'], out)
            state['files'] = []

    def close_blk():
        if state['blk']:
            if state['blk'] == 'ref':
                flush_files()
            out.append('</div>')
            state['blk'] = None

    def close_sec():
        close_blk()
        if state['sec']:
            flush_files()   # section had no 相關資源 block
            out.append('</section>')
            state['sec'] = False

    for b in blocks[start:]:
        if b[0] == 'h':
            lvl, text = b[1], b[2]
            if lvl == 2:
                close_sec()
                sid = slug(text)
                m = re.match(r'^(?:題目|Q)(\d+)\s*[-–]\s*(.*)$', plain(text))
                num, name, kind = ('', plain(text), 'k')
                if m:
                    num, name, kind = m.group(1), m.group(2), 'q'
                dom = ''
                if num:
                    dom = (section_domain.get(plain(text), '') if prefix == ''
                           else MOCK_DOMAIN.get((prefix, num), ''))
                    if not dom:
                        raise SystemExit(
                            '缺少考綱歸類：%s 的「%s」。考古題請在 md 補上「對應考綱 Domain」，'
                            '模擬測驗請在 build-html.py 的 MOCK_DOMAIN 加一筆 (%r, %r)。'
                            % (path, plain(text), prefix, num))
                toc.append({'id': sid, 'lvl': 2, 'num': num, 'name': name,
                            'grp': prefix, 'dom': dom})
                nsec += 1
                out.append('<section class="sec sec-%s" id="%s">' % (kind, sid))
                badge = ('<span class="qnum">%s</span>' % esc(num)) if num \
                    else '<span class="qnum qnum-k">%s</span>' % K_SVG
                heading = inline(name) if num else inline(text)
                out.append('<h2 class="sec-h">%s<span class="sec-t">%s</span>'
                           '<a class="anchor" href="#%s" aria-label="複製此段落連結">#</a></h2>'
                           % (badge, heading, sid))
                state['sec'] = True
                state['files'] = section_files.get(plain(text), [])
            else:
                close_blk()
                sid = slug(text)
                toc.append({'id': sid, 'lvl': 3, 'num': '', 'name': plain(text),
                            'grp': prefix, 'dom': ''})
                out.append('<h3 id="%s">%s<a class="anchor" href="#%s" '
                           'aria-label="複製此段落連結">#</a></h3>' % (sid, inline(text), sid))
            continue

        if b[0] == 'para' and b[1]:
            lb = label_of(b[1][0])
            if lb and state['sec']:
                cls, disp, tail_txt = lb
                close_blk()
                out.append('<div class="blk blk-%s">' % cls)
                out.append('<p class="blk-h"><span class="chip chip-%s">%s</span></p>' % (cls, esc(disp)))
                state['blk'] = cls
                tail = b[1][1:]
                if tail_txt:
                    tail = [tail_txt] + tail
                if tail:
                    out.append('<p>%s</p>' % inline(' '.join(x.strip() for x in tail)))
                continue
            m = re.match(r'^\*\*([^*]+)\*\*\s*$', b[1][0].strip())
            if m and state['sec']:
                out.append('<p class="step">%s</p>' % inline(m.group(1)))
                tail = b[1][1:]
                if tail:
                    out.append('<p>%s</p>' % inline(' '.join(x.strip() for x in tail)))
                continue

        if b[0] == 'hr':
            close_blk()
            continue

        render_blocks([b], out)

    close_sec()
    return doc_title, inline(intro), idx_items, nsec


def cards_html(idx_items):
    cards = []
    for label, href in idx_items:
        m = re.match(r'^(?:題目|Q)(\d+)\s*[-–]\s*(.*)$', label)
        if m:
            cards.append('<a class="card" href="%s"><span class="card-n">%s</span>'
                         '<span class="card-t">%s</span></a>'
                         % (esc(href), esc(m.group(1)), esc(m.group(2))))
        else:
            cards.append('<a class="card card-k" href="%s"><span class="card-n">K</span>'
                         '<span class="card-t">%s</span></a>' % (esc(href), esc(label)))
    return '\n'.join(cards)


def overview_html(toc):
    """開頭的考綱分類總覽：五大類，每類列出跨全部來源的題目連結。"""
    order = {prefix: i for i, (_p, prefix, _n, _k) in enumerate(DOCS)}
    out = ['<nav class="ovw" id="overview" aria-label="考綱分類總覽">']
    out.append('<p class="ovw-h">依 CKAD 考綱分類</p>')
    out.append('<p class="ovw-lede">同一類的題目散在考古題與各份模擬測驗裡，'
               '這裡依官方五大 Domain 收攏成一份索引，想補哪一塊就從這裡進去。</p>')
    for key, en, zh, weight, desc in DOMAINS:
        items = [e for e in toc if e.get('dom') == key]
        items.sort(key=lambda e: (order.get(e['grp'], 99), int(e['num'])))
        out.append('<section class="dom" id="dom-%s">' % key)
        out.append('<div class="dom-h">')
        out.append('<span class="dom-w"><b>%d</b><i>%%</i></span>' % weight)
        out.append('<span class="dom-name"><span class="dom-zh">%s</span>'
                   '<span class="dom-en">%s</span></span>' % (esc(zh), esc(en)))
        out.append('<span class="dom-n">%d 題</span>' % len(items))
        out.append('</div>')
        out.append('<p class="dom-desc">%s</p>' % esc(desc))
        out.append('<div class="qrefs">')
        for e in items:
            tag = SRC_TAG.get(e['grp'], e['grp'])
            out.append('<a class="qref" href="#%s" title="%s %s - %s">'
                       '<span class="qref-n">%s</span>'
                       '<span class="qref-t">%s</span>'
                       '<span class="qref-s">%s</span></a>'
                       % (e['id'], esc(tag), esc(e['num']), html.escape(e['name'], quote=True),
                          esc(e['num']), esc(e['name']), esc(tag)))
        out.append('</div></section>')
    out.append('</nav>')
    return '\n'.join(out)


def main():
    for path, prefix, _name, _kicker in DOCS:
        DOC_BY_NAME[path.split('/')[-1]] = prefix

    out, toc, groups = [], [], []
    for path, prefix, name, kicker in DOCS:
        gid = 'grp-' + (prefix or 'main')
        before = len(out)
        doc_title, intro_html, idx_items, nsec = render_doc(path, prefix, out, toc)
        body = out[before:]
        del out[before:]

        out.append('<section class="grp" id="%s">' % gid)
        out.append('<p class="grp-kicker">%s</p>' % esc(kicker))
        out.append('<h2 class="grp-h">%s</h2>' % esc(name))
        if intro_html:
            out.append('<p class="grp-lede">%s</p>' % intro_html)
        out.append('<p class="grp-src">來源：<code>%s</code></p>' % esc(path))
        if idx_items:
            out.append('<div class="grid">%s</div>' % cards_html(idx_items))
        out.append('</section>')
        out.extend(body)

        groups.append({'id': gid, 'name': name, 'kicker': kicker,
                       'prefix': prefix, 'n': nsec, 'title': doc_title})

    # ---- sidebar: 總覽捷徑，接著每份來源一組
    nav = ['<div class="nav-grp">',
           '<a class="nv nv2 nv-ovw" href="#overview" data-t="考綱 分類 總覽 domain">'
           '<span class="n n-k">◎</span><span class="tx">考綱分類總覽</span></a>',
           '</div>']
    for g in groups:
        nav.append('<div class="nav-grp">')
        nav.append('<a class="nav-g" href="#%s"><span class="nav-g-t">%s</span>'
                   '<span class="nav-g-n">%d</span></a>' % (g['id'], esc(g['name']), g['n']))
        for e in toc:
            if e['grp'] != g['prefix']:
                continue
            key = esc((e['name'] + ' ' + e['num'] + ' ' + g['name']).lower())
            if e['lvl'] == 2:
                n = ('<span class="n">%s</span>' % esc(e['num'])) if e['num'] \
                    else '<span class="n n-k">K</span>'
                nav.append('<a class="nv nv2" href="#%s" data-t="%s">%s<span class="tx">%s</span></a>'
                           % (e['id'], key, n, esc(e['name'])))
            else:
                nav.append('<a class="nv nv3" href="#%s" data-t="%s"><span class="tx">%s</span></a>'
                           % (e['id'], key, esc(e['name'])))
        nav.append('</div>')

    qcount = sum(1 for e in toc if e['lvl'] == 2 and e['num'])
    kcount = sum(1 for e in toc if e['lvl'] == 3)
    mock = sum(g['n'] for g in groups if g['prefix'])

    stats = [
        '<span class="stat"><b>%d</b> 題練習記錄</span>' % qcount,
        '<span class="stat"><b>%d</b> 題來自模擬測驗</span>' % mock,
        '<span class="stat"><b>%d</b> 則通用知識</span>' % kcount,
        '<span class="stat"><b>%d</b> 份來源筆記</span>' % len(groups),
    ]

    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    doc = (tpl.replace('{{TITLE}}', esc(DOC_TITLE))
              .replace('{{INTRO}}', esc(DOC_LEDE))
              .replace('{{NAV}}', '\n'.join(nav))
              .replace('{{STATS}}', '\n        '.join(stats))
              .replace('{{OVERVIEW}}', overview_html(toc))
              .replace('{{CONTENT}}', '\n'.join(out)))
    open(DST, 'w', encoding='utf-8').write(doc)
    print('OK docs=%d sections=%d (考古題 %d / 模擬 %d) bytes=%d'
          % (len(groups), len(toc), qcount - mock, mock, len(doc)))


main()
