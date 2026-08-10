# tmdrud0.github.io

백엔드 포트폴리오. <https://tmdrud0.github.io> 로 바로 열린다.

| 파일 | 내용 |
|---|---|
| `index.html` | 본문 — 프로필 · 대회 제출 파이프라인 · 스코어보드 전달·복구 · 남은 한계 |
| `measurements.html` | 근거 — 측정 환경, 런 목록, 적체·복구 그래프, 폐기한 실행과 그 이유 |
| `assets/site.css` | 스타일 한 벌. 두 페이지가 같이 쓴다 |
| `build.py` | 원고(Markdown) → 위 두 HTML |

## 원고

두 HTML은 **손으로 고치지 않는다.** 원고는 프로젝트 저장소에 있다.

    github.com/tmdrud0/web  →  docs/portfolio/SUBMISSION.md
                                docs/portfolio/MEASUREMENTS.md
                                docs/portfolio/diagrams/*.svg

내용을 고칠 때는 저 Markdown을 고치고 다시 굽는다.

```bash
python build.py
```

기본 경로는 형제 디렉터리(`../web/web/docs/portfolio`)이고, 다르면 인자로 준다.

```bash
python build.py D:/path/to/web/docs/portfolio
```

`pip install markdown` 이 필요하다.

## 빌드가 하는 일

- `SUBMISSION.md`의 프로필 블록(첫 `---` 앞)은 히어로·역량 카드로 **`build.py` 안에 손으로 짜여 있다.**
  표로 두면 훑는 사람에게 수치가 걸리지 않는다. 이름·연락처·지표를 바꾸려면 `HERO` 상수를 고친다.
- `diagrams/*.svg` 9종을 **HTML 안에 인라인**한다. 외부 파일로 두면 인쇄와 오프라인 저장에서 빠진다.
- 원고가 지면 때문에 싣지 않은 측정 차트 3종을 본문에 끼운다 (`CHART_INSERTS`).
- 그림 뒤의 `> **그림 N.** …` 인용을 `<figcaption>` 안으로 합친다.
- `MEASUREMENTS.md` 같은 저장소 안 링크를 사이트 안 주소로 돌린다 (`LINK_REWRITES`).

### 알려진 것

`make-charts.py`가 차트 캔버스를 760px로 잡는데 범례 글자가 x=652에서 시작해서
`judge outbox (MySQL)` 같은 긴 라벨이 잘린다. 여기서는 `widen_chart()`가 캔버스를 넓혀
피하지만, **PDF 쪽은 그대로 잘린다** — `make-charts.py`의 `W, H = 760, 340`을 고치는 게 근본 해결이다.
(`make-rank-chart.py`는 900px로 그리므로 해당 없다.)

`CHART_INSERTS`의 앵커는 원고의 **문장 앞부분**만 잡는다. 그래도 그 부분을 고치면 빌드가
`차트 앵커가 0번 걸렸습니다`로 멈춘다 — 조용히 엉뚱한 자리에 붙는 것보다 낫다고 보고 그렇게 뒀다.
멈추면 `build.py`의 앵커 문자열을 새 문장에 맞추면 된다.

## 배포

`main`에 push하면 `.github/workflows/github-pages.yml`이 저장소 루트를 그대로 올린다.
Jekyll을 쓰지 않으므로 `.nojekyll`을 지우면 안 된다 (`assets/`가 `_`로 시작하지는 않지만,
Jekyll 파이프라인이 끼면 빌드가 달라진다).

## 폰트

한글 본문은 Pretendard(dynamic subset, jsDelivr)를 쓰고, CDN이 막힌 망에서는
Malgun Gothic 등 시스템 폰트로 폴백된다. 폰트가 없어도 레이아웃은 그대로다.
