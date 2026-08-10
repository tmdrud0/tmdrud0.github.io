"""docs/portfolio/*.md 를 GitHub Pages 두 장으로 굽는다.

    index.html         본문 — 프로필 + 1~4장 (SUBMISSION.md)
    measurements.html  근거 — 측정 기록 (MEASUREMENTS.md)

원고는 이 저장소가 아니라 프로젝트 저장소에 있다. 기본 경로는 형제 디렉터리이고
첫 번째 인자로 덮어쓸 수 있다.

    python build.py                       # ../web/web/docs/portfolio
    python build.py D:/some/other/path

프로필(이름·지표·역량 카드)은 SUBMISSION.md 상단을 그대로 옮기되 마크다운 표가
아니라 카드로 짠다. 표로 두면 훑는 사람에게 수치가 걸리지 않는다.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.exit("markdown 패키지가 필요합니다:  pip install markdown")


HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / "web" / "web" / "docs" / "portfolio"

REPO = "https://github.com/tmdrud0/web"
EMAIL = "tmdrud049@gmail.com"


# ---------------------------------------------------------------- 원고 손질

# SUBMISSION.md 는 차트를 싣지 않는다(지면 때문). 웹에서는 넣는다.
# prefetch 차트는 본문을 줄이면서 MEASUREMENTS §7 로 내렸으므로 여기서 넣지 않는다.
# (앵커 줄의 앞부분, before|after, 삽입할 마크다운)
# 앵커는 원고를 고쳐도 잘 안 바뀌는 앞부분만 잡는다. 문장 끝까지 적으면 표현을 다듬을 때마다
# 빌드가 깨진다. 두 번 이상 걸리면 실패시켜서 엉뚱한 자리에 붙는 것을 막는다.
CHART_INSERTS = [
    (
        "각 값은 그 버퍼의 개별 피크이고",
        "after",
        "![단계별 적체와 배수. 부하는 150초에 끝나는데 RabbitMQ ready 는 209초까지"
        " 계속 올라 94,211이 된다. 백로그는 상한이 꺾이는 지점 바로 앞에만 앉는다."
        " `20260808-104446/pipeline.csv`.](diagrams/chart-backlog.svg)",
    ),
    (
        "꼬리가 나빠진 것은 재전달 지연 때문이 아니다.",
        "before",
        "![노드 사망과 회수. `prefetch=1` 이라 unacked 수가 곧 일하는 consumer 수이고,"
        " 32 → 16 → 32 가 노드의 생사를 그대로 보여준다. 주황 음영이 죽어 있던 구간."
        " `20260808-115115`(주입) vs `-114654`(무주입 짝).](diagrams/chart-nodekill.svg)",
    ),
]

# 저장소에 아직 올라가지 않은 파일로 가는 링크는 죽는다. 사이트 안으로 돌린다.
LINK_REWRITES = {
    # 링크 주소만 바꾸면 화면에 "SUBMISSION.md" 라는 글자가 남는다. 문구째 바꾼다.
    "포트폴리오 본문([SUBMISSION.md](SUBMISSION.md))": "[포트폴리오 본문](index.html)",
    "](MEASUREMENTS.md)": "](measurements.html)",
    "](SUBMISSION.md)": "](index.html)",
    "[`make-charts.py`](make-charts.py)": "`make-charts.py`",
}


def apply_inserts(md_text: str) -> str:
    lines = md_text.splitlines()
    for anchor, where, payload in CHART_INSERTS:
        hits = [i for i, line in enumerate(lines) if line.strip().startswith(anchor)]
        if len(hits) != 1:
            raise SystemExit(
                f"차트 앵커가 {len(hits)}번 걸렸습니다(1이어야 함): {anchor[:40]}..."
            )
        at = hits[0] + 1 if where == "after" else hits[0]
        lines[at:at] = ["", payload, ""]
    return "\n".join(lines)


def rewrite_links(md_text: str) -> str:
    for old, new in LINK_REWRITES.items():
        md_text = md_text.replace(old, new)
    return md_text


# ---------------------------------------------------------------- 렌더링

def slugify(text: str, separator: str = "-") -> str:
    """한글 제목을 살리는 heading id 규칙.

    python-markdown 기본 slugify 는 NFKD 후 ASCII 인코딩이라 한글이 통째로
    사라진다("측정 전제" -> "_1"). 목차 링크와 본문 id 가 같은 규칙을 써야 한다.
    """
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(rf"[{re.escape(separator)}\s]+", separator, text) or "s"


def make_md() -> markdown.Markdown:
    return markdown.Markdown(
        extensions=["extra", "fenced_code", "tables", "sane_lists"]
    )


CHART_LEGEND_PAD = 80


def widen_chart(svg: str) -> str:
    """차트 캔버스를 오른쪽으로 넓힌다.

    make-charts.py 가 캔버스를 760 으로 잡는데 범례 글자는 x=652 에서 시작한다.
    "judge outbox (MySQL)", "scoreboard 반영 대기" 처럼 긴 라벨이 viewBox 밖으로
    나가 잘린다. 원고를 건드리지 않고 여기서 여백만 더한다 —
    make-charts.py 의 `W, H = 760, 340` 을 고치면 PDF 쪽도 같이 낫는다.
    """
    box = re.search(r'viewBox="0 0 (?P<w>[\d.]+) (?P<h>[\d.]+)"', svg)
    if not box:
        return svg

    old_w, height = box.group("w"), box.group("h")
    new_w = f"{float(old_w) + CHART_LEGEND_PAD:g}"

    svg = svg.replace(box.group(0), f'viewBox="0 0 {new_w} {height}"', 1)
    svg = re.sub(rf'\bwidth="{re.escape(old_w)}"', f'width="{new_w}"', svg, count=2)
    return svg


def inline_svg(html_text: str, diagram_dir: Path) -> str:
    """<img src="diagrams/x.svg"> -> <figure> + SVG 본문.

    외부 파일로 두면 인쇄와 오프라인 저장에서 그림이 빠진다. 9종 합쳐 50KB 남짓이라
    통째로 넣는 편이 낫다.
    """
    # 마크다운이 이미지 한 줄을 <p>로 감싼다. <figure>가 <p> 안에 들어가면 안 되므로
    # 감싼 문단째로 걷어낸다.
    pattern = re.compile(
        r'(?:<p>\s*)?<img\s+[^>]*?src="diagrams/(?P<name>[\w.-]+\.svg)"[^>]*?/?>'
        r"(?:\s*</p>)?"
    )

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        path = diagram_dir / name
        if not path.exists():
            raise SystemExit(f"다이어그램이 없습니다: {path}")

        alt_match = re.search(r'alt="(?P<alt>[^"]*)"', match.group(0))
        alt = alt_match.group("alt") if alt_match else ""

        svg = re.sub(r"^<\?xml[^>]*\?>\s*", "", path.read_text(encoding="utf-8").strip())
        svg = svg.replace("<svg ", '<svg preserveAspectRatio="xMidYMid meet" ', 1)
        if name.startswith("chart-"):
            svg = widen_chart(svg)

        caption = f"<figcaption>{alt}</figcaption>" if alt else ""
        # 그림은 900 폭 기준으로 그렸다. 폰 화면에 통째로 욱여넣으면 글자가 4px 가 되므로
        # 최소 폭을 두고 가로로 넘겨 보게 한다.
        kind = "diagram chart" if name.startswith("chart-") else "diagram"
        return (
            f'<figure class="{kind}">'
            f'<div class="fig-scroll">{svg}</div>{caption}</figure>'
        )

    return pattern.sub(replace, html_text)


def merge_figure_captions(html_text: str) -> str:
    """그림 바로 뒤의 `> **그림 N.** ...` 인용을 figcaption 안으로 넣는다.

    원고에서는 alt 와 캡션 인용이 따로였다. 웹에서는 한 카드로 묶여야 그림과 설명이
    떨어지지 않는다.
    """
    pattern = re.compile(
        r"<figcaption>[^<]*</figcaption>\s*</figure>\s*"
        r"<blockquote>\s*<p>(?P<body>\s*<strong>그림\s*\d+\..*?)</p>\s*</blockquote>",
        re.DOTALL,
    )
    return pattern.sub(
        lambda m: f"<figcaption>{m.group('body').strip()}</figcaption></figure>",
        html_text,
    )


ROLE_CLASS = {"MySQL": "sql", "Redis": "redis", "RabbitMQ": "mq"}


def role_cards(html_text: str) -> str:
    """저장소 역할 세 줄을 다이어그램 색을 쓴 카드로 바꾼다.

    이 세 줄이 이후 모든 판단의 기준이라 목록으로 흘려보내면 안 된다.
    """

    def build(match: re.Match[str]) -> str:
        cards = []
        for item in re.findall(r"<li>(.*?)</li>", match.group(0), re.DOTALL):
            parsed = re.match(
                r"\s*<strong>(?P<key>[^<]+)</strong>\s*—\s*(?P<rest>.*)", item, re.DOTALL
            )
            if not parsed:
                return match.group(0)
            key = parsed.group("key").strip()
            cards.append(
                f'<li class="role-card {ROLE_CLASS.get(key, "")}">'
                f'<b>{key}</b><span>{parsed.group("rest").strip()}</span></li>'
            )
        return f'<ul class="roles">{"".join(cards)}</ul>'

    return re.sub(
        r"<ul>\s*<li><strong>MySQL</strong>.*?</ul>",
        build,
        html_text,
        count=1,
        flags=re.DOTALL,
    )


def wrap_tables(html_text: str) -> str:
    """표를 가로 스크롤 컨테이너에 넣고, 머리가 빈 표는 라벨 표로 표시한다."""

    def replace(match: re.Match[str]) -> str:
        table = match.group(0)
        head = re.search(r"<thead>.*?</thead>", table, re.DOTALL)
        if head and not re.sub(r"<[^>]+>|\s", "", head.group(0)):
            table = table.replace("<table>", '<table class="plain">', 1)
        return f'<div class="table-wrap">{table}</div>'

    return re.sub(r"<table>.*?</table>", replace, html_text, flags=re.DOTALL)


def demote_headings(html_text: str, by: int = 1) -> str:
    """h1..h4 를 한 단계 내린다. 페이지의 h1 은 이름 하나뿐이어야 한다."""
    return re.sub(
        r"<(/?)h([1-4])>",
        lambda m: f"<{m.group(1)}h{int(m.group(2)) + by}>",
        html_text,
    )


def add_heading_ids(html_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """제목에 id 를 달고 (레벨, id, 텍스트) 목록을 함께 돌려준다."""
    found: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        level = int(match.group("lv"))
        inner = match.group("inner")
        text = re.sub(r"<[^>]+>", "", inner).strip()

        base = slugify(text)
        seen[base] = seen.get(base, 0) + 1
        anchor = base if seen[base] == 1 else f"{base}-{seen[base]}"

        found.append((level, anchor, text))
        return f'<h{level} id="{anchor}">{inner}</h{level}>'

    html_text = re.sub(
        r"<h(?P<lv>[2-4])>(?P<inner>.*?)</h(?P=lv)>", replace, html_text, flags=re.DOTALL
    )
    return html_text, found


def render_markdown(md_text: str, diagram_dir: Path, demote: int = 1) -> str:
    md = make_md()
    out = md.convert(md_text)
    out = demote_headings(out, demote)
    out = inline_svg(out, diagram_dir)
    out = merge_figure_captions(out)
    out = role_cards(out)
    out = wrap_tables(out)
    return out


# ---------------------------------------------------------------- 페이지 뼈대

def page(*, title: str, description: str, body: str, extra_head: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="author" content="신승경">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/site.css">
<link rel="icon" href="data:image/svg+xml,\
%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E\
%3Crect width='32' height='32' rx='7' fill='%230f766e'/%3E\
%3Ctext x='16' y='22' font-family='sans-serif' font-size='17' font-weight='700' \
fill='white' text-anchor='middle'%3ES%3C/text%3E%3C/svg%3E">
{extra_head}</head>
<body>
<div id="progress" aria-hidden="true"></div>
<a class="skip" href="#main">본문으로 건너뛰기</a>
{body}
<script>
(function () {{
  var bar = document.getElementById('progress');
  var ticking = false;
  function paint() {{
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    bar.style.transform = 'scaleX(' + (max > 0 ? h.scrollTop / max : 0) + ')';
    ticking = false;
  }}
  addEventListener('scroll', function () {{
    if (!ticking) {{ ticking = true; requestAnimationFrame(paint); }}
  }}, {{ passive: true }});
  paint();

  var links = [].slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (!links.length || !('IntersectionObserver' in window)) return;
  var byId = {{}};
  var targets = [];
  links.forEach(function (a) {{
    var el = document.getElementById(decodeURIComponent(a.hash.slice(1)));
    if (el) {{ byId[el.id] = a; targets.push(el); }}
  }});
  var visible = new Set();
  var io = new IntersectionObserver(function (entries) {{
    entries.forEach(function (e) {{
      if (e.isIntersecting) visible.add(e.target.id); else visible.delete(e.target.id);
    }});
    // 장과 그 안의 소제목이 같이 걸린다. 문서 순서상 마지막 = 지금 읽는 자리.
    var current = null;
    for (var i = targets.length - 1; i >= 0; i--) {{
      if (visible.has(targets[i].id)) {{ current = targets[i].id; break; }}
    }}
    if (!current) return;
    links.forEach(function (a) {{ a.classList.remove('on', 'cur'); }});
    var leaf = byId[current];
    leaf.classList.add('on');
    var owner = leaf.getAttribute('data-ch');
    if (owner && byId[owner]) byId[owner].classList.add('cur');
  }}, {{ rootMargin: '-10% 0px -70% 0px', threshold: 0 }});
  targets.forEach(function (el) {{ io.observe(el); }});
}})();
</script>
</body>
</html>
"""


def toc_html(items: list[tuple[str, str, list[tuple[str, str]]]], foot: str = "") -> str:
    parts = ['<nav class="toc" aria-label="목차">', "<h2>목차</h2>", "<ol>"]
    for anchor, label, subs in items:
        parts.append(f'<li><a href="#{anchor}">{label}</a>')
        if subs:
            parts.append('<ol class="sub">')
            parts.extend(
                f'<li><a href="#{a}" data-ch="{anchor}">{t}</a></li>' for a, t in subs
            )
            parts.append("</ol>")
        parts.append("</li>")
    parts.append("</ol>")
    if foot:
        parts.append(f'<div class="foot">{foot}</div>')
    parts.append("</nav>")
    return "\n".join(parts)


# ---------------------------------------------------------------- 프로필

HERO = f"""<header class="hero">
  <div class="hero-inner">
    <p class="eyebrow">백엔드 개발자 · 신입</p>
    <h1>신승경 <span class="role">· Backend</span></h1>
    <p class="tagline">장애가 났을 때 <em>어디까지 복구되는지 말할 수 있는</em>
      시스템을 만드는 데 관심이 있다.</p>
    <p class="hero-lede">대회 중 제출이 몰릴 때 데이터가 유실되거나 실시간 순위가 최종 순위와
      어긋나는 문제를 주제로 삼았다. 메시지 중복 전달과 이벤트 순서 역전은 분산 구성에서
      피할 수 없으므로 그것을 전제로 설계했다.</p>
    <p class="hero-lede">Java 17 · Spring Boot 3.4 · MySQL · Redis · RabbitMQ로 온라인 저지
      API 서버를 혼자 만들었다 (2025.09 ~, 11개월). 요구사항은
      <a href="https://codeforces.com/profile/tmdrud" target="_blank" rel="noopener">Codeforces</a>
      Candidate Master로 대회를 뛰며 겪은 것들에서 나왔다.</p>

    <ul class="metrics">
      <li class="metric">
        <span class="cond">제출 1,000/s × 150초</span>
        <span class="fig">127,687건 <small>전량 채점</small></span>
        <span class="note">접수 132,510건 · 중복 제외 · 유실 0 · 적체 해소 10.4분</span>
      </li>
      <li class="metric">
        <span class="cond">judge 노드 1대 SIGKILL</span>
        <span class="fig">max 9.8<small>초</small></span>
        <span class="note">4초 만에 미확인 메시지 회수 · end-to-end 기준</span>
      </li>
      <li class="metric">
        <span class="cond">Redis 스코어보드 롤백</span>
        <span class="fig">2초대 <small>수렴</small></span>
        <span class="note">되감긴 offset + 1부터 replay · 상한 관찰값</span>
      </li>
      <li class="metric">
        <span class="cond">순위 정합성</span>
        <span class="fig">순서·중복 <small>무관</small></span>
        <span class="note">어떤 순서로 적용해도 수렴 · 회귀 테스트로 고정</span>
      </li>
    </ul>
    <p class="metrics-caveat">단일 호스트에서, 부하 발생기와 서버가 자원을 나눠 쓰는
      조건으로 쟀다. 절대 성능으로 읽으면 안 된다. 구조가 어디서 막히는가의 증거로 읽어야 하고,
      무엇을 재지 않았는지는 <a href="#측정-전제">측정 전제</a>에 적었다.</p>

    <ul class="contact">
      <li><a href="mailto:{EMAIL}"><span class="k">이메일</span> {EMAIL}</a></li>
      <li><a href="{REPO}" target="_blank" rel="noopener">
        <span class="k">저장소</span> github.com/tmdrud0/web</a></li>
      <li><a href="https://github.com/tmdrud0" target="_blank" rel="noopener">
        <span class="k">GitHub</span> tmdrud0</a></li>
      <li><a href="https://codeforces.com/profile/tmdrud" target="_blank" rel="noopener">
        <span class="k">Codeforces</span> Candidate Master</a></li>
      <li><button class="btn" type="button" onclick="window.print()">PDF로 저장</button></li>
    </ul>
  </div>
</header>"""


STRENGTHS = """<section class="chapter" id="핵심-역량">
  <p class="chapter-no">STRENGTHS</p>
  <h2>핵심 역량</h2>
  <p class="chapter-lede">스스로 확인한 것만 적는다. 각 항목은 아래 본문에서
    어떤 실험으로 그렇게 말할 수 있는지까지 이어진다.</p>
  <div class="strengths">
    <article class="strength">
      <h3>정합성을 순서와 중복에 의존하지 않게 설계한다.</h3>
      <p>채점 완료 순서는 제출 순서와 다르다. 누적 방식 스코어보드는 이것 때문에 대회 중
        참가자가 본 순위와 최종 순위를 다르게 만들었다. 누적을 버리고 매번 재계산하도록 바꿨다.</p>
      <a class="ref" href="#다시-흘려보내도-안전한가">→ 3장 · 다시 흘려보내도 안전한가</a>
    </article>
    <article class="strength">
      <h3>측정 조건을 의심하고, 근거로 쓸 수 있는 수치와 없는 수치를 구분한다.</h3>
      <p><code>prefetch</code>를 올렸을 때의 꼬리 악화는 포화 상태에서 재면 +25%로 보이고,
        포화를 걷어내면 +334%다. 백로그라는 지배항이 분자와 분모를 함께 키워 효과를 희석하기
        때문이다. 부하 발생기와 서버가 같은 호스트를 나눠 쓰므로 절대 처리량은 용량 수치로
        쓰지 않고, 모든 비교는 짝실험으로 설계했다.</p>
      <a class="ref" href="measurements.html#73-같은-변경을-포화-상태에서-재면">→ 측정 기록 §7.3 · 포화 여부에 따른 차이</a>
    </article>
    <article class="strength">
      <h3>내가 틀린 것을 측정으로 찾아낸다.</h3>
      <p>judge CPU가 72–78%로 관측돼 CPU 한도가 병목이라고 판단했다. 두 런의 CPU 시계열을
        비교하니 JIT 컴파일이 감쇠하는 곡선이었고, 샘플러의 “피크 CPU”가 그 초반 스파이크를
        집고 있었다. 정상 CPU는 7–9%였고, 병목은 다른 데 있었다.</p>
      <a class="ref" href="#백로그는-병목-바로-앞에만-앉는다">→ 2장 · 병목은 채점인데 CPU 때문은 아니다</a>
    </article>
    <article class="strength">
      <h3>실행계획과 락 경로까지 내려가서 원인을 가른다.</h3>
      <p>깊은 페이지 랭킹 조회가 233초까지 갔다. 집계 테이블과 스냅숏으로 뒤쪽 페이지를
        0.113ms까지 줄였지만 solved 랭킹은 아직 47.7초다. 병목이 tie group 안으로 옮겨간
        것이고, 실행계획이 그걸 보여준다. 데드락 세 건도
        격리 수준·잠금 진입점·인덱스로 원인 층이 매번 달랐다.</p>
      <a class="ref" href="#ch4">→ 4장 · 랭킹 조회와 데드락</a>
    </article>
  </div>
</section>"""


LINKS = f"""<section class="chapter" id="보조-자료">
  <p class="chapter-no">APPENDIX</p>
  <h2>보조 자료</h2>
  <p class="chapter-lede">본문은 주장이고, 근거 문서는 그 주장의 출처다.
    본문에 실린 모든 수치는 런 이름과 함께 추적된다.</p>
  <div class="links">
    <a class="link-card" href="measurements.html">
      <b>부하 · 회복 측정 기록</b>
      <span>측정 환경 기준선, 런 11개의 조건과 원자료, 적체 · 복구 그래프,
        지표와 알림 규칙, 테스트 범위, 그리고 폐기한 실행과 그 이유.</span>
    </a>
    <a class="link-card" href="{REPO}" target="_blank" rel="noopener">
      <b>github.com/tmdrud0/web</b>
      <span>코드. 역할별(web / batch / judge) 기동 계약과 실행 방법은 README에 있다.</span>
    </a>
    <a class="link-card" href="mailto:{EMAIL}">
      <b>{EMAIL}</b>
      <span>연락처. 이 문서에 대한 질문이라면 어느 장의 어느 수치인지만 알려주면 된다.</span>
    </a>
  </div>
</section>"""


FOOT = f"""<footer class="site-foot">
  <div class="inner">
    <div><span>신승경 · 백엔드 개발자</span><span>{EMAIL}</span></div>
    <div>
      <a href="{REPO}" target="_blank" rel="noopener">저장소</a>
      <a href="measurements.html">측정 기록</a>
      <a href="https://codeforces.com/profile/tmdrud" target="_blank" rel="noopener">Codeforces</a>
    </div>
  </div>
</footer>"""


# 장마다 훑는 사람이 결론부터 읽도록 머리 요약을 단다.
CHAPTER_LEDES = {
    1: "제출 · 채점 · 순위를 돌려주는 API 서버. 다루는 범위는 대회 제출 경로다. "
    "MySQL은 원본, Redis는 파생, RabbitMQ는 전달. 저장소마다 역할을 하나씩만 준 것이 "
    "이후 두 장의 판단 기준이 된다.",
    2: "채점 작업 분배를 DB claim에서 RabbitMQ work queue로 옮겼다. "
    "제출 1,000/s를 150초 넣어 127,687건 전량 채점, 유실 0을 확인했다. "
    "<code>prefetch</code>가 대시보드에 안 보이는 곳에서 꼬리를 어떻게 키우는지도 짝실험으로 갈랐다.",
    3: "스코어보드 전달을 DB outbox에서 RabbitMQ stream으로 옮겼다. "
    "이유는 처리 성능이 아니라 checkpoint의 위치다. Redis를 스냅샷으로 되돌렸을 때 "
    "되감긴 offset + 1이 곧 재시작점이 된다.",
    4: "읽기 경로와 잠금에서 부딪힌 것. 깊은 페이지 랭킹 조회가 233초까지 갔고, "
    "집계 테이블과 스냅숏으로 0.113ms까지 줄였다. "
    "데드락 세 건은 격리 수준 · 잠금 진입점 · 인덱스로 원인 층이 매번 달랐다.",
    5: "검증하지 않은 것을 먼저 적는다. 채점이 <code>Thread.sleep</code>이라는 것, "
    "재현한 장애가 프로세스 즉사 한 종류라는 것, 아직 재지 않은 부대 I/O, "
    "대회·일반 제출이 같은 큐를 쓴다는 것, 그리고 데드락에 회귀 테스트가 없다는 것.",
}


def build_index(source: Path, out: Path) -> None:
    text = source.joinpath("SUBMISSION.md").read_text(encoding="utf-8")

    # 프로필 블록(첫 `---` 앞)은 히어로/역량 카드로 손으로 짰다. 본문만 변환한다.
    body_md = text.split("\n---\n", 1)[1]
    body_md = rewrite_links(apply_inserts(body_md))

    chapters_md = [c.strip() for c in re.split(r"\n---\n", body_md) if c.strip()]

    sections: list[str] = []
    toc_items: list[tuple[str, str, list[tuple[str, str]]]] = [
        ("핵심-역량", "핵심 역량", []),
    ]

    for md_chunk in chapters_md:
        head, _, rest = md_chunk.partition("\n")
        no, _, title = head.lstrip("# ").partition(". ")
        anchor = f"ch{no}"

        # "온라인 저지 (개인 프로젝트, 2025.09 ~ ...)" 처럼 괄호가 붙은 제목은
        # 제목과 기간을 나눠 단다. 한 줄로 두면 제목이 두 줄로 접힌다.
        main, paren, meta = title.partition(" (")
        meta = meta.rstrip(")").replace(", ", " · ") if paren else ""

        rendered = render_markdown(rest.strip(), source / "diagrams")
        rendered, headings = add_heading_ids(rendered)

        lede = CHAPTER_LEDES.get(int(no), "")
        sections.append(
            f'<section class="chapter" id="{anchor}">\n'
            f'  <p class="chapter-no">CHAPTER {no}</p>\n'
            f"  <h2>{html.escape(main)}</h2>\n"
            + (f'  <p class="chapter-meta">{html.escape(meta)}</p>\n' if meta else "")
            + (f'  <p class="chapter-lede">{lede}</p>\n' if lede else "")
            + f"{rendered}\n</section>"
        )
        toc_items.append(
            (anchor, f"{no}. {main}", [(a, t) for lv, a, t in headings if lv == 3])
        )

    # 마지막 장의 `## 보조 자료`는 카드로 다시 만들었으므로 본문에서 걷어낸다.
    sections[-1] = re.sub(
        r'<h3 id="보조-자료">.*?(?=</section>)', "", sections[-1], flags=re.DOTALL
    )
    toc_items[-1] = (
        toc_items[-1][0],
        toc_items[-1][1],
        [s for s in toc_items[-1][2] if s[0] != "보조-자료"],
    )
    toc_items.append(("보조-자료", "보조 자료", []))

    nav = toc_html(
        toc_items,
        foot='<a href="measurements.html">측정 기록 →</a><br>'
        f'<a href="{REPO}" target="_blank" rel="noopener">저장소 →</a>',
    )

    body = f"""{HERO}
<div class="shell">
{nav}
<main class="doc" id="main">
{STRENGTHS}
{chr(10).join(sections)}
{LINKS}
</main>
</div>
{FOOT}"""

    out.write_text(
        page(
            title="신승경 · 백엔드 개발자 포트폴리오",
            description="온라인 저지 대회 제출 파이프라인 — 제출 1,000/s에서 127,687건 "
            "전량 채점·유실 0, 노드 사망 후 9.8초, Redis 롤백 후 2초대 수렴. "
            "측정 조건까지 함께 적은 백엔드 신입 포트폴리오.",
            body=body,
        ),
        encoding="utf-8",
    )
    print(f"index.html          장 {len(sections)}개")


def build_measurements(source: Path, out: Path) -> None:
    text = source.joinpath("MEASUREMENTS.md").read_text(encoding="utf-8")

    head, _, rest = text.partition("\n")
    title = head.lstrip("# ").strip()

    # 원고 첫 문단은 리드로 올린다.
    lede_md, _, rest = rest.strip().partition("\n---\n")
    lede = re.sub(r"</?p>", "", make_md().convert(rewrite_links(lede_md.strip()))).strip()

    rendered = render_markdown(rewrite_links(rest.strip()), source / "diagrams", demote=0)
    rendered, headings = add_heading_ids(rendered)

    nav = toc_html(
        [(a, t, []) for lv, a, t in headings if lv == 2],
        foot='<a href="index.html">← 본문으로</a>',
    )

    body = f"""<header class="subpage-head">
  <div class="inner">
    <a class="back" href="index.html">← 신승경 · 백엔드 포트폴리오</a>
    <h1>{html.escape(title)}</h1>
    <p>{lede}</p>
  </div>
</header>
<div class="shell">
{nav}
<main class="doc subpage" id="main">
{rendered}
</main>
</div>
{FOOT}"""

    out.write_text(
        page(
            title=f"{title} · 신승경",
            description="포트폴리오 본문 수치의 출처 — 측정 환경 기준선, 런별 조건과 원자료, "
            "적체·복구 그래프, 관측·테스트 범위, 폐기한 실행과 그 이유.",
            body=body,
        ),
        encoding="utf-8",
    )
    print(f"measurements.html   절 {len([h for h in headings if h[0] == 2])}개")


def main() -> None:
    source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not source.is_dir():
        sys.exit(f"원고 디렉터리를 찾을 수 없습니다: {source}")

    print(f"원고: {source}")
    build_index(source, HERE / "index.html")
    build_measurements(source, HERE / "measurements.html")


if __name__ == "__main__":
    main()
