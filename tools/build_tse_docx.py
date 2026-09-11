#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_tse_docx.py  ---  정본 .md 를 한국섬유공학회지 제출 서식 .docx 로 빌드

논문생성규칙 §명령 3 「최종 제출용 DOCX 물리 서식」을 따른다.

  docx 생성은 템플릿 패키지 통째 복사 + word/document.xml 본문만 교체 방식으로
  한다. styles/numbering/settings/헤더·푸터를 그대로 물려받으므로 제목·절
  자동번호·줄간격·여백·꼬리말 쪽번호가 저절로 일치한다.

즉 서식의 원본은 그 저널에 실제로 제출했던 과거 docx (template/TSE_DrapeAssess.docx)
이며, 이 스크립트는 그 패키지에서 본문만 갈아 끼운다. docx 라이브러리로 처음부터
새로 만들지 않는다.

본문 XML 은 pandoc 이 만든 docx 에서 가져온다. pandoc 이 마크다운·수식(OMML)·표·
그림을 이미 해석해 주므로 마크다운 파서를 새로 쓰지 않고, 문단마다 스타일만
템플릿의 것으로 바꿔 끼운다.

스타일 매핑 (템플릿 TSE_DrapeAssess.docx 에서 확인한 실제 사용값)
  a3                   국문·영문 제목
  MS                   저자·소속·교신저자
  1                    절 제목  (numId 19 / ilvl 0 으로 자동번호)
  2                    소절 제목 (스타일 자체에 numId 19 / ilvl 1)
  -center              그림 문단
  Figure               그림 캡션
  Table0               표 캡션
  Table                표 셀 문단
  a5                   표 격자(tblStyle)
  EndNoteBibliography  참고문헌

2026-09-11 — 사용자가 Word 에서 고친 TSE_TomoSh4.docx 의 서식을 기준으로 삼았다.
  · 템플릿 word/styles.xml 을 그 파일 것으로 갈아 끼움 (Table 스타일 들여쓰기
    firstLine 200 → hanging 120; 그 밖의 스타일은 그대로)
  · 표 셀 문단은 Table 스타일만 쓰고 keepNext·ind 직접 서식을 얹지 않음
  · 번호 붙는 절·소절 제목 앞에 빈 문단 하나 (서론과 제목 바로 뒤 소절은 예외)
  · 교신저자 줄 들여쓰기 260, 그 뒤의 빈 문단 없음

사용
  uv run python tools/build_tse_docx.py draft_sh4/src/TSE_TomoSh4.md
  uv run python tools/build_tse_docx.py draft_sh4/src/TSE_TomoSh4.md --pdf
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile

# 자동번호를 붙이지 않는 절 제목 (본문 절이 아닌 것)
NONUM_HEADINGS = {'Abstract', 'Keywords', '감사의 글', '참고문헌',
                  '데이터·코드 가용성 및 고지'}  # 마지막은 2026-09-11 피어리뷰 C-8 (가용성·AI·저자 기여·이해상충)

SOFFICE = r'C:\Program Files\LibreOffice\program\soffice.exe'


# ==========================================================================
# 정본 .md 읽기
# ==========================================================================
def split_front_matter(text):
    """--- 로 둘러싼 머리말을 뽑는다.

    `key: value` 와 여러 줄짜리 `key: |` 만 쓴다. 서식이 이 두 가지뿐이므로
    YAML 파서를 끌어오지 않는다.
    """
    if not text.startswith('---'):
        return {}, text
    end = text.index('\n---', 3)
    head, body = text[3:end], text[end + 4:]
    meta, key, buf = {}, None, []

    def flush():
        if key:
            meta[key] = '\n'.join(buf).strip('\n')

    for line in head.splitlines():
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(\|?)\s*(.*)$', line)
        if m and (m.group(2) or not line.startswith(' ')):
            flush()
            key, buf = m.group(1), []
            if not m.group(2) and m.group(3):
                buf = [m.group(3).strip().strip('"')]
        elif key is not None:
            buf.append(line.strip())
    flush()
    return meta, body.lstrip('\n')


# ==========================================================================
# XML 조각 만들기
# ==========================================================================
def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def runs_from_plain(text):
    """평문 한 줄을 run 으로 바꾼다. ^x^ 는 위첨자."""
    out = []
    for part in re.split(r'(\^[^^]+\^)', text):
        if not part:
            continue
        if part.startswith('^') and part.endswith('^') and len(part) > 2:
            out.append('<w:r><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/>'
                       '<w:vertAlign w:val="superscript"/></w:rPr>'
                       '<w:t xml:space="preserve">%s</w:t></w:r>' % esc(part[1:-1]))
        else:
            out.append('<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % esc(part))
    return ''.join(out)


def para(style, runs, extra_ppr=''):
    ppr = ''
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    ppr += extra_ppr
    return '<w:p><w:pPr>%s</w:pPr>%s</w:p>' % (ppr, runs)


def title_block(meta):
    """제출본 첫머리: 국문 제목·저자·소속 → 영문 제목·저자·소속 → 교신저자."""
    ind = '<w:ind w:firstLine="200"/>'
    center = '<w:jc w:val="center"/>'
    out = []

    def multiline(style, text, extra=''):
        lines = [l for l in text.splitlines() if l.strip()]
        runs = []
        for i, l in enumerate(lines):
            if i:
                runs.append('<w:r><w:br/></w:r>')
            runs.append(runs_from_plain(l.strip()))
        out.append(para(style, ''.join(runs), extra))

    multiline('a3', meta['title_ko'], '<w:ind w:firstLine="314"/>')
    out.append(para('MS', runs_from_plain(meta['authors_ko']), ind + center))
    out.append(para('MS', runs_from_plain(meta['affil_ko']), ind + center))
    multiline('a3', meta['title_en'], '<w:ind w:firstLine="314"/>')
    out.append(para(None, runs_from_plain(meta['authors_en']), ind + center))
    out.append(para('MS', runs_from_plain(meta['affil_en']), ind + center))
    # 교신저자 줄의 들여쓰기 260 과 그 뒤에 빈 문단을 두지 않는 것은 사용자가 Word 에서
    # 고친 TSE_TomoSh4.docx (2026-09-11) 를 그대로 따른 것이다.
    out.append(para('MS', runs_from_plain(meta['corresp']),
                    '<w:ind w:firstLine="260"/>' + center))
    return ''.join(out)


# ==========================================================================
# pandoc 산출물 갈아 끼우기
# ==========================================================================
def top_level_blocks(body_xml):
    """<w:body> 안의 <w:p> / <w:tbl> 을 순서대로 잘라낸다."""
    blocks, pos = [], 0
    tok = re.compile(r'<w:(p|tbl)(?:\s[^>]*)?(/?)>')
    while True:
        m = tok.search(body_xml, pos)
        if not m:
            break
        tag = 'w:' + m.group(1)
        if m.group(2) == '/':                      # <w:p/> 같은 빈 요소
            blocks.append((tag, m.group(0)))
            pos = m.end()
            continue
        close = '</%s>' % tag
        end = body_xml.index(close, m.start()) + len(close)
        blocks.append((tag, body_xml[m.start():end]))
        pos = end
    return blocks


def block_text(seg):
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', seg))


def inner_runs(p_xml):
    """<w:p> 에서 pPr 을 뺀 나머지(run·수식·하이퍼링크)를 돌려준다."""
    body = re.sub(r'^<w:p(?:\s[^>]*)?>', '', p_xml)
    body = re.sub(r'</w:p>$', '', body)
    body = re.sub(r'<w:pPr>.*?</w:pPr>', '', body, count=1, flags=re.S)
    return body


def style_of(p_xml):
    m = re.search(r'<w:pStyle w:val="([^"]+)"\s*/>', p_xml)
    return m.group(1) if m else ''


def convert_paragraph(p_xml, in_refs):
    """pandoc 문단 하나를 템플릿 스타일의 문단으로 바꾼다."""
    st = style_of(p_xml)
    runs = inner_runs(p_xml)
    text = block_text(p_xml).strip()
    ind = '<w:ind w:firstLine="200"/>'

    if '<w:drawing>' in p_xml:
        return para('-center', runs, '<w:keepNext/><w:ind w:firstLine="220"/>')

    if st in ('Heading1', 'Heading2', 'Heading3'):
        if st == 'Heading1':
            if text in NONUM_HEADINGS:
                return para('1', runs, '<w:ind w:firstLine="280"/>')
            return para('1', runs,
                        '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="19"/></w:numPr>'
                        '<w:ind w:firstLineChars="0"/>')
        return para('2', runs, '<w:ind w:firstLine="240"/>')

    if re.match(r'^Figure\s+\d+\.', text):
        return para('Figure', runs, ind)

    if re.match(r'^Table\s+\d+\.', text):
        return para('Table0', runs, '<w:keepNext/><w:ind w:firstLine="220"/>')

    if in_refs:
        m = re.match(r'^(\d+)\.\s*', text)
        if m:
            n = m.group(1)
            # 앞머리의 "n." 을 지우고 번호 run + 탭으로 다시 만든다
            rest = re.sub(r'<w:t([^>]*)>(\s*%s\.\s*)' % re.escape(n),
                          r'<w:t\1>', runs, count=1)
            head = ('<w:r><w:t>%s.</w:t></w:r><w:r><w:tab/></w:r>' % n)
            return para('EndNoteBibliography', head + rest,
                        '<w:ind w:left="720" w:firstLine="200"/>')

    return para(None, runs, ind)


PANEL_RE = re.compile(r'^\(?[a-z]\)?$')


def convert_table(tbl_xml):
    """pandoc 표를 템플릿 표로 바꾼다.

    셀이 모두 (a) (b) 같은 패널 라벨이면 그림 아래에 붙는 무테두리 표로,
    그 밖이면 a5 격자 표로 만든다.
    """
    rows = re.findall(r'<w:tr(?:\s[^>]*)?>.*?</w:tr>', tbl_xml, flags=re.S)
    grid = []
    for r in rows:
        cells = re.findall(r'<w:tc(?:\s[^>]*)?>(.*?)</w:tc>', r, flags=re.S)
        grid.append(cells)
    if not grid:
        return tbl_xml
    ncol = max(len(r) for r in grid)

    texts = [block_text(c).strip() for r in grid for c in r]
    is_panel = (len(grid) == 1 and all(PANEL_RE.match(t.replace('\\', '')) for t in texts if t))

    total = 9600 if not is_panel else 6803   # 본문 폭 10,466 twip 안에서 최대한
    # 열 너비를 칸 내용 길이에 비례해 나눈다. 균등 분할하면 'Measurement' 같은
    # 머리글이 두 줄로 접히면서 표가 읽기 나빠진다.
    widths = []
    if is_panel:
        widths = [total // ncol] * ncol
    else:
        span = []
        for c in range(ncol):
            longest = 1
            for r in grid:
                if c < len(r):
                    longest = max(longest, len(block_text(r[c]).strip()))
            # 칸 전체 길이로 잰다. 가장 긴 낱말로 재면 "82.49 (10.7%)" 처럼
            # 값과 오차가 한 줄에 들어가야 하는 칸이 접힌다.
            span.append(min(max(longest, 5), 18))
        s = sum(span)
        widths = [max(600, int(total * v / s)) for v in span]
        total = sum(widths)

    def cell(content, header, panel, colw):
        p_all = re.findall(r'<w:p(?:\s[^>]*)?>.*?</w:p>', content, flags=re.S)
        paras = []
        for p in p_all:
            runs = inner_runs(p)
            if panel:
                paras.append(para(None, runs,
                                  '<w:spacing w:line="240" w:lineRule="auto"/>'
                                  '<w:ind w:firstLineChars="0" w:firstLine="0"/>'
                                  '<w:jc w:val="center"/>'))
            else:
                # 셀 문단은 Table 스타일만 쓰고 직접 서식을 얹지 않는다. 들여쓰기·줄간격은
                # 템플릿의 Table 스타일이 정한다 — 사용자가 Word 에서 고친
                # TSE_TomoSh4.docx (2026-09-11) 의 셀 서식을 그대로 따른 것이다.
                paras.append(para('Table', runs))
        if not paras:
            paras.append(para('Table', '') if not panel
                         else para(None, '', '<w:ind w:firstLine="0"/>'))
        shd = ('<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>'
               if header and not panel else '')
        return ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s'
                '<w:vAlign w:val="center"/></w:tcPr>%s</w:tc>'
                % (colw, shd, ''.join(paras)))

    tbl_pr = ('<w:tblPr>'
              + ('' if is_panel else '<w:tblStyle w:val="a5"/>')
              + '<w:tblW w:w="%d" w:type="dxa"/><w:jc w:val="center"/>' % total
              + ('<w:tblLayout w:type="fixed"/>' if is_panel else '')
              + '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
                'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
              + '</w:tblPr>')
    grid_xml = ('<w:tblGrid>'
                + ''.join('<w:gridCol w:w="%d"/>' % w for w in widths)
                + '</w:tblGrid>')

    out = ['<w:tbl>', tbl_pr, grid_xml]
    for i, r in enumerate(grid):
        cells = ''.join(cell(c, i == 0, is_panel, widths[j])
                        for j, c in enumerate(r))
        cells += ''.join(cell('', i == 0, is_panel, widths[j])
                         for j in range(len(r), ncol))
        out.append('<w:tr><w:trPr><w:jc w:val="center"/>'
                   + ('<w:tblHeader/>' if i == 0 and not is_panel else '')
                   + '</w:trPr>' + cells + '</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)


# ==========================================================================
# 빌드
# ==========================================================================
def check_manuscript(body_md):
    """투고 규정과 어조 규칙 중 기계로 볼 수 있는 것만 확인한다.

    - 영문 초록 200 단어 이내, 키워드 5개 이내 (한국섬유공학회지 투고요령)
    - 그림·표 번호가 본문 첫 인용 순서와 일치하는지 (논문생성규칙 §그림 규칙)
    - 본문에 bold 강조가 없는지 (논문어조규칙 1). 참고문헌의 권 표기는 뺀다.
    """
    problems = []
    sections = re.split(r'^# ', body_md, flags=re.M)
    by_name = {}
    for s in sections:
        if not s.strip():
            continue
        name, _, rest = s.partition('\n')
        by_name[name.strip()] = rest

    abstract = by_name.get('Abstract', '')
    n_words = len(abstract.split())
    if n_words > 200:
        problems.append('영문 초록 %d 단어 (200 초과)' % n_words)
    kw = [k for k in by_name.get('Keywords', '').strip().split(';') if k.strip()]
    if len(kw) > 5:
        problems.append('키워드 %d 개 (5 초과)' % len(kw))

    # 캡션 줄과 참고문헌을 뺀 본문에서 인용만 센다
    body_only = []
    in_refs = False
    for line in body_md.splitlines():
        if line.startswith('# '):
            in_refs = line[2:].strip() == '참고문헌'
        if in_refs or re.match(r'^(Figure|Table)\s+\d+\.', line.strip()):
            continue
        body_only.append(line)
    body_only = '\n'.join(body_only)

    for kind in ('Figure', 'Table'):
        seen = []
        for m in re.finditer(r'\b%s\s+(\d+)' % kind, body_only):
            n = int(m.group(1))
            if n not in seen:
                seen.append(n)
        if seen != list(range(1, len(seen) + 1)):
            problems.append('%s 인용 순서가 번호와 어긋남: %s' % (kind, seen))

    for m in re.finditer(r'\*\*[^*]+\*\*', body_only):
        problems.append('본문 bold 강조: %s' % m.group(0)[:30])

    # [14](괄호) 처럼 인용 바로 뒤에 여는 괄호가 오면 마크다운이 그것을 링크로 읽는다.
    # 눈으로는 멀쩡한데 docx 에는 바깥 주소를 가리키는 하이퍼링크가 되어 들어간다.
    for m in re.finditer(r'(?<!!)\[[^\]\n]*\]\(', body_md):
        problems.append('마크다운 링크로 읽히는 자리: %s'
                        % body_md[m.start():m.start() + 40].replace('\n', ' '))
    return problems


def run_pandoc(md_path, work, resource_path):
    out = os.path.join(work, '_pandoc.docx')
    subprocess.run(['pandoc', md_path, '-f', 'markdown', '-t', 'docx',
                    '--resource-path', resource_path, '-o', out], check=True)
    return out


def build(md_path, make_pdf=False):
    md_path = os.path.abspath(md_path)
    src_dir = os.path.dirname(md_path)
    draft = os.path.dirname(src_dir)
    work = os.path.join(draft, 'build')
    template = os.path.join(draft, 'template', 'TSE_DrapeAssess.docx')
    name = os.path.splitext(os.path.basename(md_path))[0]
    out_docx = os.path.join(draft, name + '.docx')

    if not os.path.isfile(template):
        sys.exit('서식 템플릿이 없다: %s' % template)
    os.makedirs(work, exist_ok=True)

    text = open(md_path, encoding='utf-8').read()
    meta, body_md = split_front_matter(text)
    for k in ('title_ko', 'authors_ko', 'affil_ko', 'title_en', 'authors_en',
              'affil_en', 'corresp'):
        if k not in meta:
            sys.exit('머리말에 %s 가 없다' % k)

    problems = check_manuscript(body_md)
    for p in problems:
        print('검수: %s' % p)
    if not problems:
        print('검수: 초록 분량·키워드 수·그림표 인용 순서·본문 강조 모두 이상 없음')

    body_path = os.path.join(work, '_body.md')
    with open(body_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(body_md)

    pandoc_docx = run_pandoc(body_path, work, src_dir)

    with zipfile.ZipFile(pandoc_docx) as z:
        pan_doc = z.read('word/document.xml').decode('utf-8')
        pan_rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
        pan_media = {n: z.read(n) for n in z.namelist() if n.startswith('word/media/')}

    with zipfile.ZipFile(template) as z:
        pkg = {n: z.read(n) for n in z.namelist()}

    # ---- 그림 관계 ID 를 템플릿과 겹치지 않게 옮긴다 ----
    # pandoc 은 속성 순서를 Type, Id, Target 으로 쓰고 Word 는 Id 를 먼저 쓴다.
    # 순서에 기대지 않도록 관계 요소마다 속성을 따로 뽑는다.
    pan_img, pan_link = {}, {}
    for rel in re.findall(r'<Relationship\b[^>]*/>', pan_rels):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', rel))
        kind = attrs.get('Type', '')
        if kind.endswith('/image'):
            pan_img[attrs['Id']] = attrs['Target']
        elif kind.endswith('/hyperlink'):
            # 본문이 r:id 로 가리키는데 옮기지 않으면 끊긴 관계가 남는다. 그것만으로
            # Word 는 파일 복구를 요구한다(LibreOffice 는 그냥 열어 PDF 까지 만든다).
            pan_link[attrs['Id']] = attrs['Target']
    if not pan_img:
        print('경고: pandoc 산출물에 그림 관계가 없다')
    used = set(re.findall(r'Id="rId(\d+)"', pkg['word/_rels/document.xml.rels'].decode('utf-8')))
    next_id = max(int(v) for v in used) + 1
    rel_add, id_map = [], {}
    for old_id, target in pan_img.items():
        base = os.path.basename(target)
        new_name = 'word/media/new_' + base
        pkg[new_name] = pan_media['word/' + target]
        new_id = 'rId%d' % next_id
        next_id += 1
        id_map[old_id] = new_id
        rel_add.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships/image" Target="media/new_%s"/>'
                       % (new_id, base))
    for old_id, target in pan_link.items():
        new_id = 'rId%d' % next_id
        next_id += 1
        id_map[old_id] = new_id
        rel_add.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships/hyperlink" Target="%s" '
                       'TargetMode="External"/>' % (new_id, target))

    # ---- 본문 변환 ----
    body_xml = pan_doc[pan_doc.index('<w:body>') + len('<w:body>'):pan_doc.rindex('</w:body>')]
    body_xml = re.sub(r'<w:bookmark(Start|End)[^>]*/>', '', body_xml)
    body_xml = re.sub(r'<w:sectPr>.*?</w:sectPr>', '', body_xml, flags=re.S)

    out_blocks, in_refs = [], False
    # 번호가 붙는 절·소절 제목 앞에는 빈 문단을 하나 둔다. 첫 절(서론)과 제목 바로 뒤에
    # 오는 소절 제목은 예외다. 사용자가 Word 에서 고친 TSE_TomoSh4.docx (2026-09-11) 의
    # 배치를 그대로 따른 것이다.
    prev_heading, seen_numbered = False, False
    for tag, seg in top_level_blocks(body_xml):
        if tag == 'w:tbl':
            out_blocks.append(convert_table(seg))
            prev_heading = False
            continue
        st = style_of(seg)
        if st == 'Heading1':
            in_refs = block_text(seg).strip() == '참고문헌'
        numbered = ((st == 'Heading1' and block_text(seg).strip() not in NONUM_HEADINGS)
                    or st == 'Heading2')
        if numbered and seen_numbered and not prev_heading:
            out_blocks.append(para(None, '', '<w:ind w:firstLine="200"/>'))
        out_blocks.append(convert_paragraph(seg, in_refs))
        prev_heading = st in ('Heading1', 'Heading2', 'Heading3')
        seen_numbered = seen_numbered or numbered

    new_body = title_block(meta) + ''.join(out_blocks)
    # 한 번에 바꾼다. 순차 치환은 이미 바뀐 새 ID 가 다음 옛 ID 와 겹쳐
    # 그림이 서로 뒤바뀐다(예: rId12 -> rId24 로 바꾼 뒤 옛 rId24 를 찾으면 걸린다).
    new_body = re.sub(r'r:(embed|id)="([^"]+)"',
                      lambda m: 'r:%s="%s"' % (m.group(1),
                                               id_map.get(m.group(2), m.group(2))),
                      new_body)

    tpl_doc = pkg['word/document.xml'].decode('utf-8')
    head = tpl_doc[:tpl_doc.index('<w:body>') + len('<w:body>')]
    # pandoc 의 그림 XML 은 a: 와 pic: 접두사를 루트에서 선언된 것으로 보고 쓴다.
    # 템플릿은 그림마다 인라인으로 선언했으므로 루트에 없다. 없으면 채워 넣는다.
    for pfx, uri in (('a', 'http://schemas.openxmlformats.org/drawingml/2006/main'),
                     ('pic', 'http://schemas.openxmlformats.org/drawingml/2006/picture')):
        if 'xmlns:%s=' % pfx not in head:
            head = head.replace('<w:document ',
                                '<w:document xmlns:%s="%s" ' % (pfx, uri), 1)
    tail_start = tpl_doc.rindex('<w:sectPr')
    tail = tpl_doc[tail_start:]
    pkg['word/document.xml'] = (head + new_body + tail).encode('utf-8')

    rels = pkg['word/_rels/document.xml.rels'].decode('utf-8')
    pkg['word/_rels/document.xml.rels'] = rels.replace(
        '</Relationships>', ''.join(rel_add) + '</Relationships>').encode('utf-8')

    # 템플릿이 쓰던 옛 그림은 더 이상 참조되지 않으므로 뺀다
    for n in [n for n in list(pkg) if re.match(r'word/media/image\d+\.', n)]:
        del pkg[n]

    # 그림을 지웠으면 그 관계도 지운다. 대상이 없는 관계를 남겨 두지 않는다.
    rels = pkg['word/_rels/document.xml.rels'].decode('utf-8')

    def alive(rel):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', rel))
        if attrs.get('TargetMode') == 'External':
            return True
        t = attrs.get('Target', '')
        if t.startswith('..') or t.startswith('http'):
            return True
        return ('word/' + t) in pkg

    found = re.findall(r'<Relationship\b[^>]*/>', rels)
    if len(found) != rels.count('<Relationship '):
        raise SystemExit('관계 요소를 다 읽지 못했다(%d/%d) — 스스로 닫지 않는 표기가 있다'
                         % (len(found), rels.count('<Relationship ')))
    kept = ''.join(r for r in found if alive(r))
    pkg['word/_rels/document.xml.rels'] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">' + kept + '</Relationships>').encode('utf-8')

    # 마지막 관문 — 본문이 가리키는 관계가 전부 풀리는지 본다. 하나라도 끊겨 있으면
    # Word 는 「파일을 복구해야 한다」며 열지 않는데, LibreOffice 는 그냥 열어 PDF 까지
    # 만들어 준다. 검사하지 않으면 이 결함이 조용히 투고본으로 나간다.
    declared = set(re.findall(r'Id="([^"]+)"', kept))
    referenced = set(re.findall(r'r:(?:id|embed)="([^"]+)"',
                                pkg['word/document.xml'].decode('utf-8')))
    dangling = sorted(referenced - declared)
    if dangling:
        raise SystemExit('끊긴 관계 %s — 본문이 가리키는데 rels 에 없다.' % dangling)

    with zipfile.ZipFile(out_docx, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in pkg.items():
            z.writestr(n, data)
    print('wrote %s' % out_docx)

    if make_pdf:
        subprocess.run([SOFFICE, '--headless', '--convert-to', 'pdf',
                        '--outdir', work, out_docx], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pdf = os.path.join(work, name + '.pdf')
        print('wrote %s' % pdf)
        # 투고요령: 표·그림 포함 A4 20면 이내. 면수를 여기서 바로 찍는다 —
        # 빌드 폴더에 남아 있는 옛 pg-*.png 를 세다가 낡은 값을 믿은 적이 있다.
        # 외부 라이브러리 없이 페이지 트리의 /Count 를 읽는다.
        with open(pdf, 'rb') as fh:
            m = re.findall(rb'/Type\s*/Pages[^>]*?/Count\s+(\d+)', fh.read())
        if m:
            n_pages = max(int(x) for x in m)
            print('면수 %d%s' % (n_pages, '' if n_pages <= 20 else '  ⚠ 20면 초과'))
    return out_docx


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('markdown', help='정본 .md (draft_*/src/*.md)')
    ap.add_argument('--pdf', action='store_true', help='build/ 에 PDF 도 만든다')
    a = ap.parse_args()
    build(a.markdown, a.pdf)


if __name__ == '__main__':
    main()
