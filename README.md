---
title: 한국 ETF 예측기
emoji: 📈
colorFrom: indigo
colorTo: green
sdk: streamlit
app_file: streamlit_app.py
pinned: false
---

# 한국 ETF 예측기

매일 오전 8시(KST)에 XGBoost 모델을 재학습하여 다음 거래일 **2.5% 이상** 상승할 한국 ETF를 추천합니다. 결과는 Supabase에 저장되고 Streamlit UI에서 조회합니다.

## 아키텍처

```
GitHub Actions cron (KST 08:00)
  └─ uv run python -m ml.train
       ├─ FinanceDataReader  → ETF 시세
       ├─ XGBoost            → 학습 + 예측
       └─ Supabase           → 결과 저장

HuggingFace Spaces (Streamlit)
  └─ Supabase 조회 → 표/차트 렌더
```

## 디렉토리

| 경로 | 역할 |
|---|---|
| `ml/` | 데이터/피처/학습/추론 |
| `app/` | Supabase 클라이언트 |
| `streamlit_app.py` | HF Spaces 진입점 |
| `db/schema.sql` | Supabase DDL |
| `.github/workflows/daily_train.yml` | cron 트리거 |
| `pyproject.toml` | 의존성 선언 (소스 오브 트루스) |
| `uv.lock` | 정확한 버전 락 — 커밋 필수 |
| `requirements.txt` | `uv export` 결과물, HF Spaces용 |

## 의존성 관리 (uv)

이 프로젝트는 [uv](https://docs.astral.sh/uv/)로 의존성을 관리합니다. Poetry/pip 대비 빠르고, PEP 621 `pyproject.toml` 기반입니다.

### 처음 셋업
```powershell
# uv 미설치 시 (Windows PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 가상환경 + 의존성 설치 (uv.lock 그대로)
uv sync
```

`.venv/`가 자동 생성되고 락 파일과 동일한 버전이 설치됩니다. 별도로 `python -m venv` 할 필요 없어요.

### 의존성 추가/제거
```powershell
uv add pandas-ta              # 런타임 의존성
uv add --dev pytest-cov       # 개발 전용
uv remove tqdm
```
명령 실행 시 `pyproject.toml`과 `uv.lock`이 함께 갱신됩니다.

### HF Spaces용 requirements.txt 갱신
HuggingFace Spaces의 Streamlit SDK는 `requirements.txt`만 읽기 때문에 락 파일에서 export 한 카피본을 커밋해둡니다. 의존성을 바꿨다면:
```powershell
uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt
git add pyproject.toml uv.lock requirements.txt
```
`requirements.txt`는 자동 생성 파일이니 직접 편집하지 마세요. 헤더 주석에 재생성 명령이 박혀 있습니다.

### 명령 실행
```powershell
uv run python -m ml.train         # 가상환경 활성화 없이 바로 실행
uv run pytest                     # 테스트
uv run streamlit run streamlit_app.py
```
또는 `.venv\Scripts\Activate.ps1`로 활성화 후 평소처럼 사용해도 됩니다.

### 락 파일 동기화 검증
```powershell
uv lock --check                   # 락이 pyproject와 동기화돼있는지 확인 (CI에서 유용)
uv sync --frozen                  # 락 파일에서만 설치, 갱신 시 실패
```

## 셋업 절차

1. **Supabase 프로젝트 생성** → SQL 에디터에서 `db/schema.sql` 실행
2. `.env.example`을 `.env`로 복사 후 `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` 입력
3. **로컬 실행**
   ```powershell
   uv sync
   uv run python -m ml.train               # 1회 학습 + 예측 + DB 적재
   uv run streamlit run streamlit_app.py   # http://localhost:8501
   ```
4. **GitHub repo 생성 후 push** → Settings → Secrets에 `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 등록 → Actions 탭에서 `daily-train` 수동 실행해 검증
5. **HuggingFace Space 생성**(Streamlit SDK) → GitHub repo와 연결, Space Secrets에 `SUPABASE_URL`, `SUPABASE_ANON_KEY` 등록

## 핵심 파라미터 (`ml/config.py`)

| 이름 | 값 | 의미 |
|---|---|---|
| `WINDOW` | 100 | 입력 시퀀스 길이(일) |
| `RISE_THRESHOLD` | 1.025 | 다음날 +2.5% 이상이면 양성 |
| `PROB_THRESHOLD` | 0.70 | 추천에 포함되는 최소 확률 |
| `XGB_DEVICE` (env) | `cpu` | GH Actions에선 CPU, 로컬 GPU 환경에선 `cuda`로 |

## 알려진 제약

- GitHub Actions runner에는 GPU가 없어 CPU로 학습합니다. ETF 수가 늘면 학습 시간이 길어질 수 있어요.
- FDR가 일시적으로 응답하지 않는 종목은 자동으로 스킵합니다.
- HuggingFace Spaces 무료 티어는 비활성 시 슬립 — 첫 접속에 콜드스타트가 있습니다.
