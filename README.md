# 여행 계획 (Streamlit)

메인 앱은 **`app.py`** (여행 플래너)입니다.

## GitHub에 올리기

현재 원격 예시: `origin` → `https://github.com/namse0523-afk/travel.git` (브랜치 `master`).

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

## Streamlit Community Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) (Streamlit Community Cloud) 로그인 후 GitHub 권한 허용.
2. **Create app** (또는 **New app**) → 저장소·브랜치(`master`) 선택.
3. **Main file path**: `app.py`
4. **Advanced settings** → **Python version**: 로컬과 맞출 것(기본은 보통 3.12). 루트 `runtime.txt`는 팀이 맞추는 Python 버전 메모용입니다.
5. 앱 **⚙ Settings → Secrets**에 아래를 붙여 넣고 저장 (`/.streamlit/secrets.toml.example` 참고). 형식은 TOML 그대로입니다.

   ```toml
   OPENAI_API_KEY = "sk-proj-여기에_본인_키"
   ```

6. **Save** 후 빌드가 끝날 때까지 대기. 코드 push 시 자동으로 다시 배포됩니다.

로컬에서만 쓰는 비밀값은 `.streamlit/secrets.toml`에 두되, 이 파일은 **절대 커밋하지 마세요**.

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
| `runtime.txt` | (선택) Cloud Python 버전 |
| `.streamlit/config.toml` | Streamlit 동작 옵션 |
| `.streamlit/secrets.toml.example` | Secrets 입력 예시 (비밀 아님) |
