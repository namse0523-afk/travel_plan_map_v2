# 여행 계획 (Streamlit)

메인 앱은 **`app.py`** (여행 플래너)입니다.

## GitHub에 올리기

현재 원격: `origin` → `https://github.com/namse0523-afk/travel_plan_map_v2.git` (브랜치 `master`).

```bash
git status
git add -A
git commit -m "Describe your change"
git push origin master
```

- `.env`는 `.gitignore`에 있어 커밋되지 **않습니다**. API 키는 GitHub에 넣지 마세요.
- 새 GitHub 저장소를 쓰는 경우:

  ```bash
  git remote remove origin   # 기존 origin이 있을 때만
  git remote add origin https://github.com/<사용자>/<새레포>.git
  git push -u origin master
  ```

## Streamlit Share 배포 (Community Cloud)

배포 URL: [share.streamlit.io](https://share.streamlit.io) — GitHub 저장소와 연동해 빌드합니다.

**체크리스트**

| 항목 | 내용 |
|------|------|
| GitHub | 코드가 push된 저장소·브랜치(예: `master`) |
| Main file | 루트의 `app.py` |
| 의존성 | 루트 `requirements.txt` (Cloud가 자동 `pip install`) |
| Python | **Advanced settings**에서 버전 선택(로컬·`runtime.txt`와 맞추면 안전, 기본은 보통 3.12) |
| Secrets | 앱 **⚙ Settings → Secrets**에 `OPENAI_API_KEY` (아래 TOML 형식) |

**순서**

1. [share.streamlit.io](https://share.streamlit.io) 로그인 → GitHub 연동 허용.
2. **Create app** → 저장소·브랜치 선택.
3. **Main file path**: `app.py`
4. **Advanced settings** → **Python version** 선택.
5. **⚙ Settings → Secrets**에 붙여 넣기 (`.streamlit/secrets.toml.example` 참고):

   ```toml
   OPENAI_API_KEY = "sk-proj-여기에_본인_키"
   ```

6. 저장 후 빌드 완료까지 대기. 이후 `git push` 시 자동 재배포됩니다.

로컬 비밀값은 `.streamlit/secrets.toml` 또는 `.env` — `secrets.toml`은 **커밋하지 마세요** (`.gitignore` 처리됨).

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows에서는 `run_app.bat`을 사용할 수 있습니다.

## 레포 구성 요약

| 경로 | 설명 |
|------|------|
| `app.py` | 여행 계획 메인 앱 |
| `requirements.txt` | Cloud가 설치하는 패키지 |
| `runtime.txt` | 로컬·문서용 Python 버전 메모 (`python-3.12`; Cloud는 UI에서 지정) |
| `.streamlit/config.toml` | Streamlit 동작 옵션 |
| `.streamlit/secrets.toml.example` | Secrets 입력 예시 (비밀 아님) |
