import base64
import hashlib
import io
import os

import streamlit as st
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)
from PIL import Image, ImageOps, UnidentifiedImageError

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_SIDE = 1024
NO_FACE_MESSAGE = "얼굴이 확인되지 않아요. 정면 사진을 올려주세요."

SYSTEM_PROMPT = f"""당신은 재미로 관상을 풀이해 주는 친근한 관상 전문가입니다.

[지켜야 할 원칙]
- 사진 속 인물이 누구인지 절대 추측하거나 언급하지 않습니다.
- 외모에 대한 비하, 의학적 진단, 범죄·질병 등에 대한 부정적 단정은 하지 않습니다.
- 긍정적이고 따뜻한 톤으로 한국어로 답하며, 단정적 예언 대신 "~한 인상이에요", "~할 수 있어요"처럼 부드럽게 표현합니다.
- 사진에 얼굴이 없거나 얼굴이 너무 흐려서 판단하기 어려우면, 다른 말 없이 정확히 다음 한 문장만 답하세요: {NO_FACE_MESSAGE}

[출력 형식 - 마크다운]
## ✨ 첫인상 한 줄 요약
(한 줄)

## 👀 부위별 풀이
- **이마**: ...
- **눈·눈썹**: ...
- **코**: ...
- **입**: ...
- **턱·얼굴형**: ...
- **귀**: ... (사진에 보이지 않으면 "사진에서 확인하기 어려워요"라고 적기)

## 🧭 종합 성향
(성격과 대인관계)

## 🍀 운세 한 스푼 (재미로 보세요)
- **재물운**: ...
- **직업운**: ...
- **연애운**: ...

## 💌 조언 한마디
(따뜻한 한마디)
"""


def get_config(name: str, default: str | None = None) -> str | None:
    """st.secrets → 환경변수(.env) 순서로 설정값을 읽는다."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # secrets.toml이 없는 로컬 환경
        pass
    # 대소문자 구분 OS(Mac/Linux)에서도 .env에 소문자로 적은 변수명을 읽을 수 있게 함
    return os.getenv(name) or os.getenv(name.lower()) or default


def to_data_uri(raw: bytes) -> str:
    """이미지를 RGB·1024px 이하로 줄여 JPEG base64 data URI로 변환한다. (메모리에서만 처리)"""
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def analyze_face(api_key: str, model: str, data_uri: str) -> str:
    """OpenAI Vision으로 관상 풀이를 받아온다. 실패 시 사용자용 메시지를 담은 RuntimeError를 던진다."""
    client = OpenAI(api_key=api_key, timeout=60, max_retries=1)
    try:
        response = client.chat.completions.create(
            model=model,
            max_completion_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 사진의 관상을 봐주세요."},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri, "detail": "low"},
                        },
                    ],
                },
            ],
        )
    except AuthenticationError:
        raise RuntimeError("API 키가 올바르지 않아요. OPENAI_API_KEY를 확인해주세요.") from None
    except RateLimitError:
        raise RuntimeError("요청이 너무 많거나 사용 한도를 초과했어요. 잠시 후 다시 시도해주세요.") from None
    except (APITimeoutError, APIConnectionError):
        raise RuntimeError("OpenAI 서버에 연결하지 못했어요. 네트워크를 확인하고 다시 시도해주세요.") from None
    except BadRequestError:
        raise RuntimeError(
            "요청이 처리되지 않았어요. 이미지를 바꿔 보거나 OPENAI_MODEL 설정(이미지 지원 모델인지)을 확인해주세요."
        ) from None
    except APIStatusError as e:
        raise RuntimeError(f"OpenAI 서버에서 오류가 발생했어요. (코드 {e.status_code}) 잠시 후 다시 시도해주세요.") from None

    choice = response.choices[0]
    message = choice.message
    if getattr(message, "refusal", None) or choice.finish_reason == "content_filter":
        raise RuntimeError("AI가 이 사진의 분석을 거절했어요. 다른 사진으로 시도해주세요.")
    text = (message.content or "").strip()
    if not text:
        raise RuntimeError("AI가 빈 응답을 보냈어요. 다시 시도해주세요.")
    return text


STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;800&display=swap');

.block-container { max-width: 720px; padding-top: 2rem; padding-bottom: 4rem; }

.hero { text-align: center; padding: 1.2rem 0 1.5rem; }
.hero-icon { font-size: 3rem; line-height: 1; }
.hero h1 {
  font-family: 'Noto Serif KR', serif; font-weight: 800; letter-spacing: -0.02em;
  font-size: clamp(1.8rem, 7vw, 2.6rem); margin: 0.4rem 0 0.2rem; padding: 0;
}
.hero-sub { margin: 0 0 0.9rem; opacity: 0.75; font-size: 1.05rem; }
.hero-badge {
  display: inline-block; font-size: 0.8rem; padding: 0.3rem 0.8rem; border-radius: 999px;
  background: rgba(183, 49, 44, 0.1); color: #8f2420; border: 1px solid rgba(183, 49, 44, 0.25);
}

.step { display: flex; align-items: center; gap: 0.7rem; margin: 1.8rem 0 0.6rem; }
.step-num {
  flex: none; width: 2rem; height: 2rem; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-weight: 700;
  background: #b7312c; color: #fff;
}
.step-title { font-family: 'Noto Serif KR', serif; font-weight: 600; font-size: 1.25rem; line-height: 1.2; }
.step-hint { font-size: 0.85rem; opacity: 0.65; }

div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stDownloadButton"] button { font-weight: 700; padding: 0.7rem 1rem; border-radius: 12px; }
div[data-testid="stImage"] img { max-height: 40vh; width: auto !important; max-width: 100%; object-fit: contain; margin: 0 auto; }
div[data-testid="stImage"] { display: flex; flex-direction: column; align-items: center; }
div[data-testid="stMarkdownContainer"] h2 {
  font-family: 'Noto Serif KR', serif !important; font-size: 1.15rem !important;
  font-weight: 600 !important; padding: 0 0 0.4rem !important; margin: 0 !important;
}
</style>
"""


def step_header(num: int, title: str, hint: str) -> None:
    st.markdown(
        f'<div class="step"><div class="step-num">{num}</div>'
        f'<div><div class="step-title">{title}</div><div class="step-hint">{hint}</div></div></div>',
        unsafe_allow_html=True,
    )


def split_sections(markdown: str) -> list[str]:
    """'## ' 제목 기준으로 결과를 섹션별로 나눈다. 제목이 없으면 통째로 반환."""
    sections: list[str] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


st.set_page_config(page_title="AI 관상 분석기", page_icon="🔮", layout="centered")

api_key = get_config("OPENAI_API_KEY")
model = get_config("OPENAI_MODEL", DEFAULT_MODEL)

st.markdown(STYLE, unsafe_allow_html=True)
st.markdown(
    """
<div class="hero">
  <div class="hero-icon">🔮</div>
  <h1>AI 관상 분석기</h1>
  <p class="hero-sub">사진 한 장으로 읽어보는 나의 얼굴 이야기</p>
  <span class="hero-badge">⚠️ 재미로 보는 콘텐츠입니다 · 과학적·의학적 근거가 없어요</span>
</div>
""",
    unsafe_allow_html=True,
)

if not api_key:
    st.error(
        "OPENAI_API_KEY가 설정되지 않았습니다. "
        "로컬에서는 .env 파일에, Streamlit Cloud에서는 Secrets에 키를 등록해주세요."
    )
    st.stop()

step_header(1, "사진 올리기", "정면이 잘 보이는 얼굴 사진이 가장 잘 나와요")
uploaded = st.file_uploader(
    "얼굴 사진 (jpg, png / 최대 5MB)",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
)
st.caption("🔒 사진은 분석을 위해 OpenAI API로 전송되며 이 앱은 저장하지 않습니다. 본인 또는 동의받은 사진만 사용해주세요.")

if uploaded is None:
    st.stop()

raw = uploaded.getvalue()
if len(raw) > MAX_UPLOAD_BYTES:
    st.error(f"파일이 너무 커요. 5MB 이하의 사진을 올려주세요. (현재 {len(raw) / 1024 / 1024:.1f}MB)")
    st.stop()

try:
    preview = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
except (UnidentifiedImageError, OSError):
    st.error("이미지를 열 수 없어요. 올바른 jpg/png 파일인지 확인해주세요.")
    st.stop()

step_header(2, "관상 보기", "버튼을 누르면 AI가 얼굴의 기운을 읽어드려요")
_, center, _ = st.columns([1, 3, 1])
with center:
    st.image(preview, caption="업로드한 사진", width="stretch")

image_hash = hashlib.sha256(raw).hexdigest()
cache: dict[str, str] = st.session_state.setdefault("results", {})

if st.button("🔮 관상 보기", type="primary", width="stretch"):
    # 같은 사진은 캐시된 결과를 재사용하되, "얼굴 없음" 결과는 다시 시도할 수 있게 한다
    if image_hash not in cache or NO_FACE_MESSAGE in cache[image_hash]:
        try:
            with st.spinner("얼굴의 기운을 읽는 중..."):
                cache[image_hash] = analyze_face(api_key, model, to_data_uri(raw))
        except RuntimeError as e:
            st.error(str(e))
        except Exception:
            st.error("예상치 못한 오류가 발생했어요. 다른 사진으로 다시 시도해주세요.")

result = cache.get(image_hash)
if result:
    step_header(3, "관상 결과", "재미로 즐겨주세요 😊")
    if NO_FACE_MESSAGE in result:
        st.warning(NO_FACE_MESSAGE, icon="🙈")
    else:
        for section in split_sections(result):
            with st.container(border=True):
                st.markdown(section)
        st.download_button(
            "📥 결과 저장하기 (.md)",
            data=result,
            file_name="관상_결과.md",
            mime="text/markdown",
            width="stretch",
        )
