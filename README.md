# AI 관상 분석기

얼굴 사진을 업로드하면 OpenAI 이미지 분석 모델이 재미로 관상을 풀이해 주는 Streamlit 앱입니다. 자세한 요구사항은 `PRD.md`를 참고하세요.

## 로컬 실행

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # 이후 .env에 OPENAI_API_KEY 입력
streamlit run app.py
```

http://localhost:8501 에서 확인할 수 있습니다.

## 환경변수

| 이름 | 설명 | 기본값 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 (필수) | - |
| `OPENAI_MODEL` | 사용할 모델 | `gpt-4o-mini` |

## Streamlit Cloud 배포

1. GitHub에 push (`.env`는 `.gitignore`로 제외됨)
2. share.streamlit.io에서 저장소와 `app.py` 지정
3. 앱 설정 → Secrets에 입력:
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-4o-mini"
   ```
