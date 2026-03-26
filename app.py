import html
import json
import math
import os
import re
from datetime import date, timedelta
from itertools import permutations
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import pandas as pd
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# 상단 브랜드 바 문구
APP_BRAND_TITLE = "J에게"
APP_BRAND_SUBTITLE = "전국의 P들이여, 우리도 할 수 있다."
APP_BRAND_ORG = "전국P구조연합"

# 상부바 왼쪽 여행 로고(비행기·항로 SVG, HTML용)
_TRAVEL_LOGO_SVG = """
<svg class="app-brand-travel-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" focusable="false" aria-hidden="true">
  <defs>
    <linearGradient id="brandPlaneGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4ba3f5"/>
      <stop offset="100%" stop-color="#1565c0"/>
    </linearGradient>
  </defs>
  <path d="M 14 70 Q 46 18 86 36" fill="none" stroke="rgba(21,101,192,0.32)" stroke-width="3.2"
        stroke-dasharray="7 6" stroke-linecap="round"/>
  <circle cx="86" cy="36" r="4.5" fill="#1976d2" opacity="0.85"/>
  <circle cx="14" cy="70" r="3.8" fill="#42a5f5" opacity="0.75"/>
  <g transform="translate(52,46) rotate(-38)">
    <ellipse cx="0" cy="0" rx="30" ry="10" fill="url(#brandPlaneGrad)"/>
    <path d="M -6 -10 L 24 -32 L 20 -14 L -2 -10 Z" fill="#1e88e5"/>
    <path d="M -6 10 L 24 32 L 20 14 L -2 10 Z" fill="#1565c0"/>
    <path d="M -34 0 L -48 -16 L -44 0 L -48 16 Z" fill="#0d47a1"/>
  </g>
</svg>
"""

# 상부바 배경: 은은한 벚꽃잎(타원) 문양 SVG → data URI
_BRAND_SAKURA_PETALS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 280" preserveAspectRatio="xMidYMid slice">
<g fill="#ffb8d2" opacity="0.32">
  <ellipse cx="110" cy="70" rx="20" ry="8" transform="rotate(22 110 70)"/>
  <ellipse cx="260" cy="175" rx="15" ry="6" transform="rotate(-35 260 175)"/>
  <ellipse cx="420" cy="55" rx="18" ry="8" transform="rotate(48 420 55)"/>
  <ellipse cx="590" cy="200" rx="13" ry="5" transform="rotate(-18 590 200)"/>
  <ellipse cx="750" cy="88" rx="17" ry="7" transform="rotate(30 750 88)"/>
  <ellipse cx="920" cy="165" rx="16" ry="6" transform="rotate(-42 920 165)"/>
  <ellipse cx="1080" cy="62" rx="19" ry="8" transform="rotate(14 1080 62)"/>
  <ellipse cx="1280" cy="210" rx="14" ry="6" transform="rotate(38 1280 210)"/>
  <ellipse cx="1450" cy="95" rx="16" ry="7" transform="rotate(-28 1450 95)"/>
  <ellipse cx="190" cy="220" rx="12" ry="5" transform="rotate(-25 190 220)"/>
  <ellipse cx="350" cy="125" rx="11" ry="4" transform="rotate(55 350 125)"/>
  <ellipse cx="520" cy="235" rx="15" ry="6" transform="rotate(10 520 235)"/>
  <ellipse cx="680" cy="40" rx="12" ry="5" transform="rotate(-50 680 40)"/>
  <ellipse cx="850" cy="240" rx="10" ry="4" transform="rotate(33 850 240)"/>
  <ellipse cx="1020" cy="130" rx="13" ry="5" transform="rotate(-12 1020 130)"/>
  <ellipse cx="1180" cy="48" rx="14" ry="6" transform="rotate(44 1180 48)"/>
  <ellipse cx="1360" cy="170" rx="11" ry="4" transform="rotate(-33 1360 170)"/>
  <ellipse cx="1520" cy="250" rx="12" ry="5" transform="rotate(20 1520 250)"/>
</g>
<g fill="#fff8fc" opacity="0.4">
  <ellipse cx="165" cy="105" rx="11" ry="4" transform="rotate(28 165 105)"/>
  <ellipse cx="310" cy="210" rx="9" ry="3" transform="rotate(-20 310 210)"/>
  <ellipse cx="470" cy="140" rx="10" ry="4" transform="rotate(52 470 140)"/>
  <ellipse cx="640" cy="75" rx="8" ry="3" transform="rotate(-15 640 75)"/>
  <ellipse cx="800" cy="195" rx="10" ry="4" transform="rotate(36 800 195)"/>
  <ellipse cx="990" cy="42" rx="9" ry="3" transform="rotate(-40 990 42)"/>
  <ellipse cx="1155" cy="155" rx="11" ry="4" transform="rotate(18 1155 155)"/>
  <ellipse cx="1320" cy="85" rx="8" ry="3" transform="rotate(-55 1320 85)"/>
  <ellipse cx="1485" cy="200" rx="10" ry="4" transform="rotate(24 1485 200)"/>
</g>
</svg>"""
_BRAND_SAKURA_BG_URI = "data:image/svg+xml;charset=utf-8," + quote(
    _BRAND_SAKURA_PETALS_SVG, safe=""
)

try:
    # openai v1 SDK
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


st.set_page_config(
    page_title="J에게",
    layout="wide",
)

# Streamlit 기본 글꼴 크기가 작게 느껴질 때를 대비해
# 화면 전체에 적용할 CSS를 주입합니다.
st.markdown(
    """
    <style>
      /* 고정 상단바 높이(대략): 본문·사이드바가 가려지지 않게 동일 값 사용 */
      :root {
        --app-brand-offset: clamp(6.35rem, 18vh, 11.5rem);
      }
      html, body {
        font-size: 18px;
        font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        /* 페이지 전체 배경: 아주 연하고 산뜻하게, 과하지 않게 */
        background:
          radial-gradient(1100px circle at 10% 0%, rgba(255, 215, 232, 0.45) 0%, rgba(255, 255, 255, 0) 60%),
          radial-gradient(900px circle at 92% 12%, rgba(198, 238, 255, 0.45) 0%, rgba(255, 255, 255, 0) 58%),
          linear-gradient(180deg, #fffdfb 0%, #fbf7ff 45%, #f4feff 100%);
      }
      .stButton>button {
        font-family: inherit !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
      }
      /* Streamlit 루트 배경이 덮지 않도록 */
      .stApp {
        background: transparent !important;
      }
      .stText, .stMarkdown, .stDataFrame, .stButton>button {
        font-size: 18px;
      }
      .stTitle, h1 {
        font-size: 2.0rem;
      }
      .stSubheader, h2 {
        font-size: 1.4rem;
      }
      /* 제목 박스: 페이지(뷰포트) 최상단 고정, 전체 너비 */
      .app-brand-bar-bleed {
        width: 100vw;
        max-width: 100vw;
        box-sizing: border-box;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        margin: 0;
        z-index: 1000020;
        color: #5a1834;
        padding: 1.2rem 1.65rem 1.35rem;
        margin-bottom: 0;
        box-shadow: 0 4px 22px rgba(214, 90, 130, 0.22);
        border-bottom: 1px solid rgba(233, 140, 175, 0.45);
        overflow: hidden;
        background: linear-gradient(148deg, #fff8fb 0%, #ffe0ef 32%, #ffcae0 58%, #ffb3d4 100%);
      }
      /* fixed 바가 문서 흐름에서 빠지므로 레이아웃용 높이 확보 */
      .app-brand-flow-spacer {
        display: block;
        width: 100%;
        min-height: var(--app-brand-offset);
        margin: 0 0 0.85rem 0;
        pointer-events: none;
      }
      section[data-testid="stSidebar"] {
        padding-top: var(--app-brand-offset) !important;
      }
      .app-brand-bar-bleed::before {
        content: "";
        position: absolute;
        z-index: 0;
        inset: -14% -8%;
        background-image: url("__BRAND_SAKURA_BG__");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        opacity: 0.52;
        pointer-events: none;
        animation: brandSakuraDrift 24s ease-in-out infinite;
        will-change: transform;
      }
      .app-brand-bar-bleed::after {
        content: "";
        position: absolute;
        z-index: 0;
        inset: 0;
        pointer-events: none;
        background:
          radial-gradient(ellipse 90px 55px at 10% 25%, rgba(255, 255, 255, 0.48) 0%, transparent 62%),
          radial-gradient(ellipse 70px 48px at 88% 35%, rgba(255, 210, 232, 0.42) 0%, transparent 58%),
          radial-gradient(ellipse 55px 40px at 72% 85%, rgba(255, 245, 250, 0.5) 0%, transparent 50%);
      }
      @keyframes brandSakuraDrift {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
        35% { transform: translate3d(2%, -1.4%, 0) scale(1.04) rotate(0.4deg); }
        65% { transform: translate3d(-1.8%, 1.1%, 0) scale(0.98) rotate(-0.3deg); }
      }
      .app-brand-inner {
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 1rem 1.75rem;
        position: relative;
        z-index: 1;
      }
      .app-brand-left {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        flex: 1;
        min-width: 0;
      }
      .app-brand-logo-icon {
        width: 68px;
        height: 68px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: 0 2px 10px rgba(214, 90, 130, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.95);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 6px;
        border: 1px solid rgba(233, 140, 175, 0.4);
        flex-shrink: 0;
      }
      .app-brand-travel-svg {
        width: 52px;
        height: 52px;
        display: block;
      }
      .app-brand-titles {
        min-width: 0;
      }
      .app-brand-title {
        font-size: 2.15rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.18;
        margin: 0;
        color: #4a0f28;
        text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
      }
      .app-brand-sub {
        font-size: 1.3rem;
        font-weight: 500;
        color: #722244;
        opacity: 0.95;
        margin: 0.4rem 0 0 0;
        line-height: 1.45;
      }
      .app-brand-org-wrap {
        padding: 0.5rem 1rem;
        background: rgba(255, 255, 255, 0.62);
        border-radius: 8px;
        text-align: right;
        border: 1px solid rgba(233, 140, 175, 0.38);
      }
      .app-brand-org {
        font-size: 1.2rem;
        font-weight: 700;
        color: #6b1539;
        white-space: nowrap;
      }
      @media (max-width: 640px) {
        .app-brand-inner { flex-direction: column; align-items: flex-start; }
        .app-brand-left { width: 100%; }
        .app-brand-org-wrap { text-align: left; width: 100%; }
        .app-brand-org { white-space: normal; }
      }
      section[data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-bottom: 0.35rem !important;
      }
      /* 사이드바 입력 사이의 'Divider/마크다운 여백'도 같이 줄임 */
      section[data-testid="stSidebar"] div[data-testid="stDivider"] {
        margin: 0.25rem 0 !important;
      }
      section[data-testid="stSidebar"] hr {
        margin: 0.25rem 0 !important;
      }
      section[data-testid="stSidebar"] div[data-testid="stMarkdown"] p {
        margin: 0.25rem 0 !important;
      }
      section[data-testid="stSidebar"] div[data-testid="stMarkdown"] {
        margin-bottom: 0.25rem !important;
      }
      /* 사이드바 # 제목: 사각 박스형 */
      section[data-testid="stSidebar"] h1 {
        font-size: 1.32rem !important;
        font-weight: 700 !important;
        line-height: 1.35 !important;
        margin: 0 0 0.6rem 0 !important;
        padding: 0.55rem 0.8rem !important;
        border: 1px solid rgba(233, 140, 175, 0.55) !important;
        border-radius: 8px !important;
        background: linear-gradient(148deg, #fff8fb 0%, #ffe8f2 48%, #ffd6e8 100%) !important;
        color: #5a1834 !important;
        letter-spacing: -0.015em !important;
        box-shadow: 0 2px 8px rgba(214, 90, 130, 0.14) !important;
      }
      /* 여행계획표 요약: 가로로 긴 스트립 + 큰 글자 */
      div.plan-strip {
        box-sizing: border-box;
        width: 100%;
        margin: 0 0 0.95rem 0;
        padding: 0.85rem 1.15rem 0.95rem;
        border: 1px solid rgba(210, 150, 175, 0.42);
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.78);
        box-shadow: 0 2px 10px rgba(120, 60, 95, 0.08);
      }
      p.plan-strip-label {
        margin: 0 0 0.45rem 0 !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
        color: #6b4558 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
      }
      p.plan-strip-body {
        margin: 0 !important;
        font-size: 1.28rem !important;
        line-height: 1.58 !important;
        color: #24161e !important;
      }
      p.plan-strip-body.plan-strip-mono {
        font-family: ui-monospace, "Cascadia Code", Consolas, monospace !important;
        font-size: 1.3rem !important;
      }
      div.plan-basis-inner {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-top: 0.35rem;
      }
      div.plan-basis-box {
        flex: 1 1 260px;
        box-sizing: border-box;
        min-width: 0;
        padding: 0.7rem 0.85rem 0.8rem;
        border: 1px solid rgba(200, 160, 185, 0.55);
        border-radius: 8px;
        background: linear-gradient(160deg, #fffafc 0%, #fff3f8 100%);
        box-shadow: 0 1px 5px rgba(120, 60, 95, 0.07);
      }
      p.plan-basis-box-title {
        margin: 0 0 0.35rem 0 !important;
        font-size: 1.12rem !important;
        font-weight: 800 !important;
        color: #662244 !important;
        letter-spacing: -0.02em !important;
      }
      p.plan-basis-box-body {
        margin: 0 !important;
        font-size: 1.12rem !important;
        line-height: 1.55 !important;
        color: #2a1e24 !important;
      }
      div.plan-basis-intro {
        font-size: 1.22rem !important;
        line-height: 1.55 !important;
        color: #2a1e24 !important;
        margin: 0 0 0.65rem 0 !important;
        white-space: pre-line !important;
      }
    </style>
    """.replace("__BRAND_SAKURA_BG__", _BRAND_SAKURA_BG_URI),
    unsafe_allow_html=True,
)


def _today_dates(trip_days: int) -> List[str]:
    start = date.today()
    return [(start + timedelta(days=i)).isoformat() for i in range(trip_days)]


# MVP용 예시 데이터: "후보군" + 좌표 + 대표 사진 URL(위키미디어 커먼스 현장 사진, 파일별 CC BY-SA 등 라이선스).
CITY_CATALOG: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "Seoul": {
        "places": [
            {
                "id": "gyeongbokgung",
                "name": "경복궁",
                "category": "관광",
                "area_tag": "종로/광화문",
                "price_tier": "중",
                "duration_minutes": 120,
                "lat": 37.579617,
                "lon": 126.977041,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Water_reflection_of_Hyangwonjeong_Pavilion_at_Gyeongbokgung_Palace_in_Seoul.jpg/500px-Water_reflection_of_Hyangwonjeong_Pavilion_at_Gyeongbokgung_Palace_in_Seoul.jpg",
            },
            {
                "id": "bukchon",
                "name": "북촌한옥마을",
                "category": "관광",
                "area_tag": "종로/북촌",
                "price_tier": "중",
                "duration_minutes": 90,
                "lat": 37.582157,
                "lon": 126.983173,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Bukchon-ro_11-gil_street_with_hanok_houses_at_blue_hour_in_Bukchon_Hanok_Village_Seoul.jpg/500px-Bukchon-ro_11-gil_street_with_hanok_houses_at_blue_hour_in_Bukchon_Hanok_Village_Seoul.jpg",
            },
            {
                "id": "hongdae_st",
                "name": "홍대 거리",
                "category": "쇼핑",
                "area_tag": "홍대",
                "price_tier": "중",
                "duration_minutes": 120,
                "lat": 37.556295,
                "lon": 126.922397,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Hongdae%2C_Seoul.jpg/500px-Hongdae%2C_Seoul.jpg",
            },
            {
                "id": "hanriver",
                "name": "한강공원(여의도)",
                "category": "야경",
                "area_tag": "여의도",
                "price_tier": "저",
                "duration_minutes": 90,
                "lat": 37.524684,
                "lon": 126.926954,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Yeouido_Hangang_Park_from_Mapo_Bridge_1.jpg/500px-Yeouido_Hangang_Park_from_Mapo_Bridge_1.jpg",
            },
            {
                "id": "gwangjang_market",
                "name": "광장시장",
                "category": "식사",
                "area_tag": "종로/시장",
                "price_tier": "저",
                "duration_minutes": 60,
                "lat": 37.57035,
                "lon": 126.990669,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Gwangjang_Market%2C_Seoul_02.jpg/500px-Gwangjang_Market%2C_Seoul_02.jpg",
                "meal_type": "점심",
            },
            {
                "id": "hongdae_food",
                "name": "홍대 로컬 맛집 골목",
                "category": "식사",
                "area_tag": "홍대",
                "price_tier": "중",
                "duration_minutes": 75,
                "lat": 37.556917,
                "lon": 126.92308,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Street_hongdae_Seoul.jpg/500px-Street_hongdae_Seoul.jpg",
                "meal_type": "저녁",
            },
            {
                "id": "cafe_muni",
                "name": "서촌 카페 거리",
                "category": "카페/휴식",
                "area_tag": "서촌",
                "price_tier": "중",
                "duration_minutes": 70,
                "lat": 37.575,
                "lon": 126.9667,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Seochon_Cafe.jpg/500px-Seochon_Cafe.jpg",
            },
            {
                "id": "seoul_museum",
                "name": "국립현대미술관(과천/서울)",
                "category": "전시/박물관",
                "area_tag": "강남/전시",
                "price_tier": "중",
                "duration_minutes": 120,
                "lat": 37.517,
                "lon": 127.004,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/MMCA_Seoul.jpg/500px-MMCA_Seoul.jpg",
            },
        ]
    },
    "Tokyo": {
        "places": [
            {
                "id": "sensoji",
                "name": "센소지(아사쿠사)",
                "category": "관광",
                "area_tag": "아사쿠사",
                "price_tier": "중",
                "duration_minutes": 120,
                "lat": 35.714765,
                "lon": 139.796692,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Hozomon_with_visitors_under_their_umbrellas%2C_a_rainy_day_in_Tokyo%2C_Japan.jpg/500px-Hozomon_with_visitors_under_their_umbrellas%2C_a_rainy_day_in_Tokyo%2C_Japan.jpg",
            },
            {
                "id": "shibuya_scramble",
                "name": "시부야 스크램블 교차로",
                "category": "야경",
                "area_tag": "시부야",
                "price_tier": "저",
                "duration_minutes": 60,
                "lat": 35.6592,
                "lon": 139.7016,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Tokyo_Shibuya_Scramble_Crossing_2018-10-09.jpg/500px-Tokyo_Shibuya_Scramble_Crossing_2018-10-09.jpg",
            },
            {
                "id": "meiji_jingu",
                "name": "메이지진구",
                "category": "자연",
                "area_tag": "하라주쿠/오모테산도",
                "price_tier": "저",
                "duration_minutes": 90,
                "lat": 35.6764,
                "lon": 139.7005,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ee/Meiji_Shrine_-_Main_building.jpg/500px-Meiji_Shrine_-_Main_building.jpg",
            },
            {
                "id": "tokyo_sky",
                "name": "도쿄 스카이트리",
                "category": "관광",
                "area_tag": "오시아게/스미다",
                "price_tier": "중",
                "duration_minutes": 110,
                "lat": 35.710062,
                "lon": 139.8107,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Worm%27s-eye_view_of_Tokyo_Skytree_with_vertical_symmetry_impression%2C_a_sunny_day%2C_in_Japan.jpg/500px-Worm%27s-eye_view_of_Tokyo_Skytree_with_vertical_symmetry_impression%2C_a_sunny_day%2C_in_Japan.jpg",
            },
            {
                "id": "asakusa_soba",
                "name": "아사쿠사 소바/텐푸라 거리",
                "category": "식사",
                "area_tag": "아사쿠사",
                "price_tier": "중",
                "duration_minutes": 60,
                "lat": 35.714,
                "lon": 139.797,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Hozomon_Gate%2C_Tokyo%2C_South_view_from_Nakamise_Shopping_Street_20190420_1.jpg/500px-Hozomon_Gate%2C_Tokyo%2C_South_view_from_Nakamise_Shopping_Street_20190420_1.jpg",
                "meal_type": "점심",
            },
            {
                "id": "shinjuku_yokocho",
                "name": "신주쿠 야키토리 골목",
                "category": "식사",
                "area_tag": "신주쿠",
                "price_tier": "중",
                "duration_minutes": 75,
                "lat": 35.6895,
                "lon": 139.7005,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Shinjuku-West_Omoide-Yokocho.jpg/500px-Shinjuku-West_Omoide-Yokocho.jpg",
                "meal_type": "저녁",
            },
            {
                "id": "akihabara_cafe",
                "name": "아키하바라 카페/체험존",
                "category": "카페/휴식",
                "area_tag": "아키하바라",
                "price_tier": "중",
                "duration_minutes": 75,
                "lat": 35.6984,
                "lon": 139.772,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Claw_cranes_with_kawaii_stuffed_mascots_and_a_woman_playing%2C_Akihabara%2C_Chiyoda%2C_Tokyo%2C_Japan.jpg/500px-Claw_cranes_with_kawaii_stuffed_mascots_and_a_woman_playing%2C_Akihabara%2C_Chiyoda%2C_Tokyo%2C_Japan.jpg",
            },
            {
                "id": "teamlab_mock",
                "name": "팀랩(도쿄 체험 계열)",
                "category": "액티비티",
                "area_tag": "오다이바/팀랩",
                "price_tier": "고",
                "duration_minutes": 120,
                "lat": 35.6348,
                "lon": 139.883,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Photos_at_teamlab_planets_tokyo.jpg/500px-Photos_at_teamlab_planets_tokyo.jpg",
            },
        ]
    },
    "Paris": {
        "places": [
            {
                "id": "louvre",
                "name": "루브르 박물관",
                "category": "전시/박물관",
                "area_tag": "루브르/센강",
                "price_tier": "고",
                "duration_minutes": 150,
                "lat": 48.860611,
                "lon": 2.337644,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Louvre_Courtyard%2C_Looking_West.jpg/500px-Louvre_Courtyard%2C_Looking_West.jpg",
            },
            {
                "id": "eiffel",
                "name": "에펠탑(전망)",
                "category": "관광",
                "area_tag": "에펠탑/샹드마르스",
                "price_tier": "고",
                "duration_minutes": 120,
                "lat": 48.85837,
                "lon": 2.294481,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Paris_-_The_Eiffel_Tower_in_spring_-_2307.jpg/500px-Paris_-_The_Eiffel_Tower_in_spring_-_2307.jpg",
            },
            {
                "id": "montmartre",
                "name": "몽마르트르/사크레쾨르",
                "category": "야경",
                "area_tag": "몽마르트르",
                "price_tier": "중",
                "duration_minutes": 90,
                "lat": 48.886707,
                "lon": 2.343104,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Sacre_Coeur_cor_Jesu-DSC_1455w.jpg/500px-Sacre_Coeur_cor_Jesu-DSC_1455w.jpg",
            },
            {
                "id": "seine_cruise",
                "name": "센강 크루즈(야간)",
                "category": "야경",
                "area_tag": "센강",
                "price_tier": "중",
                "duration_minutes": 75,
                "lat": 48.854,
                "lon": 2.331,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Vue_depuis_bateau-mouche_sur_la_Seine_8.jpg/500px-Vue_depuis_bateau-mouche_sur_la_Seine_8.jpg",
            },
            {
                "id": "le_marais_bistro",
                "name": "르마레 비스트로",
                "category": "식사",
                "area_tag": "르마레",
                "price_tier": "중",
                "duration_minutes": 70,
                "lat": 48.85837,
                "lon": 2.362,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/H%C3%B4tel_H%C3%A9rouet%2C_Le_Marais%2C_Paris_May_2017.jpg/500px-H%C3%B4tel_H%C3%A9rouet%2C_Le_Marais%2C_Paris_May_2017.jpg",
                "meal_type": "점심",
            },
            {
                "id": "latin_quarter_dinner",
                "name": "라틴지구 디너 거리",
                "category": "식사",
                "area_tag": "라틴지구",
                "price_tier": "중",
                "duration_minutes": 80,
                "lat": 48.846,
                "lon": 2.344,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Rue_de_la_Huchette_December_13%2C_2012.jpg/500px-Rue_de_la_Huchette_December_13%2C_2012.jpg",
                "meal_type": "저녁",
            },
            {
                "id": "cafe_st_ger",
                "name": "생제르맹 카페 거리",
                "category": "카페/휴식",
                "area_tag": "생제르맹",
                "price_tier": "중",
                "duration_minutes": 75,
                "lat": 48.857,
                "lon": 2.333,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Saint-Germain_des_Pr%C3%A9s_%283363718209%29.jpg/500px-Saint-Germain_des_Pr%C3%A9s_%283363718209%29.jpg",
            },
            {
                "id": "lux_walk",
                "name": "샹젤리제 산책(쇼핑/구경)",
                "category": "쇼핑",
                "area_tag": "샹젤리제",
                "price_tier": "고",
                "duration_minutes": 100,
                "lat": 48.8698,
                "lon": 2.3079,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Crowds_of_French_patriots_line_the_Champs_Elysees-edit2.jpg/500px-Crowds_of_French_patriots_line_the_Champs_Elysees-edit2.jpg",
            },
        ]
    },
    "Rome": {
        "places": [
            {
                "id": "colosseum",
                "name": "콜로세움",
                "category": "관광",
                "area_tag": "콜로세움/포로 로마노",
                "price_tier": "고",
                "duration_minutes": 140,
                "lat": 41.89021,
                "lon": 12.492231,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Colosseo_2020.jpg/500px-Colosseo_2020.jpg",
            },
            {
                "id": "roman_forum",
                "name": "포로 로마노(로마 포럼)",
                "category": "유적지/역사",
                "area_tag": "콜로세움/포로 로마노",
                "price_tier": "고",
                "duration_minutes": 150,
                "lat": 41.892462,
                "lon": 12.485325,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Roman_Forum_%28Rome%29.jpg/500px-Roman_Forum_%28Rome%29.jpg",
            },
            {
                "id": "pantheon",
                "name": "판테온",
                "category": "유적지/역사",
                "area_tag": "판테온/나보나",
                "price_tier": "중",
                "duration_minutes": 80,
                "lat": 41.89861,
                "lon": 12.476872,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Pantheon_Rome_Italy.jpg/500px-Pantheon_Rome_Italy.jpg",
            },
            {
                "id": "trevi",
                "name": "트레비 분수",
                "category": "관광",
                "area_tag": "트레비/스페인 계단",
                "price_tier": "저",
                "duration_minutes": 45,
                "lat": 41.900932,
                "lon": 12.483313,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Trevi_Fountain_Rome_%28Italy%29.jpg/500px-Trevi_Fountain_Rome_%28Italy%29.jpg",
            },
            {
                "id": "spanish_steps",
                "name": "스페인 계단",
                "category": "관광",
                "area_tag": "트레비/스페인 계단",
                "price_tier": "저",
                "duration_minutes": 55,
                "lat": 41.905999,
                "lon": 12.482775,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Spanish_Steps_Rome_Italy.jpg/500px-Spanish_Steps_Rome_Italy.jpg",
            },
            {
                "id": "piazza_navona",
                "name": "나보나 광장",
                "category": "산책/드라이브",
                "area_tag": "판테온/나보나",
                "price_tier": "저",
                "duration_minutes": 65,
                "lat": 41.899163,
                "lon": 12.473101,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Piazza_Navona_Rome_Italy_2015.jpg/500px-Piazza_Navona_Rome_Italy_2015.jpg",
            },
            {
                "id": "castel_santangelo",
                "name": "산탄젤로 성(카스텔 산탄젤로)",
                "category": "관광",
                "area_tag": "산탄젤로/바티칸",
                "price_tier": "중",
                "duration_minutes": 110,
                "lat": 41.903056,
                "lon": 12.466306,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Castel_Sant%27Angelo%2C_Rome%2C_Italy.jpg/500px-Castel_Sant%27Angelo%2C_Rome%2C_Italy.jpg",
            },
            {
                "id": "vatican_museums",
                "name": "바티칸 박물관",
                "category": "전시/박물관",
                "area_tag": "산탄젤로/바티칸",
                "price_tier": "고",
                "duration_minutes": 180,
                "lat": 41.906487,
                "lon": 12.45362,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Vatican_Museums_entrance.jpg/500px-Vatican_Museums_entrance.jpg",
            },
            {
                "id": "st_peters",
                "name": "성 베드로 대성당",
                "category": "유적지/역사",
                "area_tag": "산탄젤로/바티칸",
                "price_tier": "저",
                "duration_minutes": 130,
                "lat": 41.902168,
                "lon": 12.453937,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/St._Peter%27s_Basilica_facade%2C_Rome%2C_Italy.jpg/500px-St._Peter%27s_Basilica_facade%2C_Rome%2C_Italy.jpg",
            },
            {
                "id": "trastevere_walk",
                "name": "트라스테베레 골목 산책",
                "category": "산책/드라이브",
                "area_tag": "트라스테베레",
                "price_tier": "저",
                "duration_minutes": 90,
                "lat": 41.8897,
                "lon": 12.4708,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/60/Trastevere_Rome_Italy.jpg/500px-Trastevere_Rome_Italy.jpg",
            },
            {
                "id": "campo_de_fiori",
                "name": "캄포 데 피오리(시장)",
                "category": "야시장/마켓",
                "area_tag": "캄포 데 피오리",
                "price_tier": "저",
                "duration_minutes": 60,
                "lat": 41.8955,
                "lon": 12.4726,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Campo_de%27_Fiori_Rome.jpg/500px-Campo_de%27_Fiori_Rome.jpg",
                "meal_type": "점심",
            },
            {
                "id": "trastevere_dinner",
                "name": "트라스테베레 디너 거리",
                "category": "식사",
                "area_tag": "트라스테베레",
                "price_tier": "중",
                "duration_minutes": 85,
                "lat": 41.8912,
                "lon": 12.4697,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Trastevere_rome_restaurant.jpg/500px-Trastevere_rome_restaurant.jpg",
                "meal_type": "저녁",
            },
            {
                "id": "cafe_corso",
                "name": "비아 델 코르소 카페/젤라또",
                "category": "카페/휴식",
                "area_tag": "코르소",
                "price_tier": "중",
                "duration_minutes": 60,
                "lat": 41.9034,
                "lon": 12.4797,
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Gelato_in_Rome.jpg/500px-Gelato_in_Rome.jpg",
            },
        ]
    },
}

# 국제 관광 도착·여행 수요 지표에서 상위권에 자주 등장하는 국가 10곳(대략적 선별) + 국가별 관광객 선호 도시 5곳.
TRAVEL_TOP10_COUNTRY_CITIES: Dict[str, List[str]] = {
    "프랑스": ["Paris", "Nice", "Lyon", "Marseille", "Strasbourg"],
    "스페인": ["Barcelona", "Madrid", "Seville", "Valencia", "Granada"],
    "미국": ["NewYork", "LosAngeles", "LasVegas", "Miami", "SanFrancisco"],
    "이탈리아": ["Rome", "Venice", "Florence", "Milan", "Naples"],
    "일본": ["Tokyo", "Kyoto", "Osaka", "Yokohama", "Sapporo"],
    "태국": ["Bangkok", "Phuket", "ChiangMai", "Pattaya", "Krabi"],
    "영국": ["London", "Edinburgh", "Manchester", "Liverpool", "Oxford"],
    "튀르키예": ["Istanbul", "Antalya", "Cappadocia", "Izmir", "Bodrum"],
    "멕시코": ["Cancun", "MexicoCity", "PlayaDelCarmen", "LosCabos", "Guadalajara"],
    "독일": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne"],
}

CITY_DISPLAY_KR: Dict[str, str] = {
    "Paris": "파리",
    "Nice": "니스",
    "Lyon": "리옹",
    "Marseille": "마르세유",
    "Strasbourg": "스트라스부르",
    "Barcelona": "바르셀로나",
    "Madrid": "마드리드",
    "Seville": "세비야",
    "Valencia": "발렌시아",
    "Granada": "그라나다",
    "NewYork": "뉴욕",
    "LosAngeles": "로스앤젤레스",
    "LasVegas": "라스베이거스",
    "Miami": "마이애미",
    "SanFrancisco": "샌프란시스코",
    "Rome": "로마",
    "Venice": "베네치아",
    "Florence": "피렌체",
    "Milan": "밀라노",
    "Naples": "나폴리",
    "Tokyo": "도쿄",
    "Kyoto": "교토",
    "Osaka": "오사카",
    "Yokohama": "요코하마",
    "Sapporo": "삿포로",
    "Bangkok": "방콕",
    "Phuket": "푸켓",
    "ChiangMai": "치앙마이",
    "Pattaya": "파타야",
    "Krabi": "크라비",
    "London": "런던",
    "Edinburgh": "에든버러",
    "Manchester": "맨체스터",
    "Liverpool": "리버풀",
    "Oxford": "옥스퍼드",
    "Istanbul": "이스탄불",
    "Antalya": "안탈리아",
    "Cappadocia": "카파도키아",
    "Izmir": "이즈미르",
    "Bodrum": "보드룸",
    "Cancun": "칸쿤",
    "MexicoCity": "멕시코시티",
    "PlayaDelCarmen": "플라야 델 카르멘",
    "LosCabos": "로스카보스",
    "Guadalajara": "과달라하라",
    "Berlin": "베를린",
    "Munich": "뮌헨",
    "Hamburg": "함부르크",
    "Frankfurt": "프랑크푸르트",
    "Cologne": "쾰른",
    "Seoul": "서울",
}

# 상세 카탈로그가 없는 도시: 대략 도심 좌표 + 범용 후보 장소(동선·일정 생성용)
CITY_CENTER_COORDS: Dict[str, Tuple[float, float]] = {
    "Paris": (48.8566, 2.3522),
    "Nice": (43.7102, 7.2620),
    "Lyon": (45.7640, 4.8357),
    "Marseille": (43.2965, 5.3698),
    "Strasbourg": (48.5734, 7.7521),
    "Barcelona": (41.3851, 2.1734),
    "Madrid": (40.4168, -3.7038),
    "Seville": (37.3891, -5.9845),
    "Valencia": (39.4699, -0.3763),
    "Granada": (37.1773, -3.5886),
    "NewYork": (40.7128, -74.0060),
    "LosAngeles": (34.0522, -118.2437),
    "LasVegas": (36.1699, -115.1398),
    "Miami": (25.7617, -80.1918),
    "SanFrancisco": (37.7749, -122.4194),
    "Rome": (41.9028, 12.4964),
    "Venice": (45.4408, 12.3155),
    "Florence": (43.7696, 11.2558),
    "Milan": (45.4642, 9.1900),
    "Naples": (40.8518, 14.2681),
    "Tokyo": (35.6762, 139.6503),
    "Kyoto": (35.0116, 135.7681),
    "Osaka": (34.6937, 135.5023),
    "Yokohama": (35.4437, 139.6380),
    "Sapporo": (43.0618, 141.3545),
    "Bangkok": (13.7563, 100.5018),
    "Phuket": (7.8804, 98.3923),
    "ChiangMai": (18.7883, 98.9853),
    "Pattaya": (12.9236, 100.8825),
    "Krabi": (8.0863, 98.9063),
    "London": (51.5074, -0.1278),
    "Edinburgh": (55.9533, -3.1883),
    "Manchester": (53.4808, -2.2426),
    "Liverpool": (53.4084, -2.9916),
    "Oxford": (51.7520, -1.2577),
    "Istanbul": (41.0082, 28.9784),
    "Antalya": (36.8969, 30.7133),
    "Cappadocia": (38.6431, 34.8286),
    "Izmir": (38.4237, 27.1428),
    "Bodrum": (37.0344, 27.4305),
    "Cancun": (21.1619, -86.8515),
    "MexicoCity": (19.4326, -99.1332),
    "PlayaDelCarmen": (20.6296, -87.0739),
    "LosCabos": (22.8905, -109.9167),
    "Guadalajara": (20.6597, -103.3496),
    "Berlin": (52.5200, 13.4050),
    "Munich": (48.1351, 11.5820),
    "Hamburg": (53.5511, 9.9937),
    "Frankfurt": (50.1109, 8.6821),
    "Cologne": (50.9375, 6.9603),
}

_GENERIC_WM_IMAGES: List[str] = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Vue_depuis_bateau-mouche_sur_la_Seine_8.jpg/500px-Vue_depuis_bateau-mouche_sur_la_Seine_8.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Gwangjang_Market%2C_Seoul_02.jpg/500px-Gwangjang_Market%2C_Seoul_02.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Paris_-_The_Eiffel_Tower_in_spring_-_2307.jpg/500px-Paris_-_The_Eiffel_Tower_in_spring_-_2307.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ee/Meiji_Shrine_-_Main_building.jpg/500px-Meiji_Shrine_-_Main_building.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Louvre_Courtyard%2C_Looking_West.jpg/500px-Louvre_Courtyard%2C_Looking_West.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Tokyo_Shibuya_Scramble_Crossing_2018-10-09.jpg/500px-Tokyo_Shibuya_Scramble_Crossing_2018-10-09.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/7/79/Hongdae%2C_Seoul.jpg/500px-Hongdae%2C_Seoul.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Saint-Germain_des_Pr%C3%A9s_%283363718209%29.jpg/500px-Saint-Germain_des_Pr%C3%A9s_%283363718209%29.jpg",
]


def _generic_city_places(city_key: str, lat0: float, lon0: float) -> List[Dict[str, Any]]:
    """상세 카탈로그 없음: 도심 좌표를 기준으로 범용 일정 후보만 생성."""
    label = CITY_DISPLAY_KR.get(city_key, city_key)
    h = sum(ord(c) for c in city_key)
    pool = _GENERIC_WM_IMAGES
    # 후보 수가 너무 적으면 N박 일정에서 반복이 심해져 마커 겹침/가려짐이 발생합니다.
    # 도심 중심 기준으로 "그럴듯한 후보"를 넉넉히(18개) 만들어 반복을 줄입니다.
    radii = [0.0035, 0.0055, 0.007]
    offs: List[Tuple[float, float]] = []
    for r_i, r in enumerate(radii):
        for k in range(6):
            ang = (k * 60 + (h % 17)) * math.pi / 180.0
            offs.append((r * math.sin(ang), r * math.cos(ang)))
    # 18개 스펙(관광/전시/야경/시장/카페/식사 등을 섞고, 점심/저녁은 각각 최소 2개)
    specs: List[Tuple[str, str, str, str, str, int, Optional[str]]] = [
        ("landmark", f"{label} 대표 랜드마크·광장", "관광", "도심", "중", 110, None),
        ("oldtown", f"{label} 구시가 산책 코스", "관광", "구시가/산책", "저", 90, None),
        ("museum", f"{label} 시내 미술관·전시", "전시/박물관", "문화권", "중", 100, None),
        ("river", f"{label} 강변/해변 산책", "산책/드라이브", "리버워크", "저", 70, None),
        ("market_lunch", f"{label} 로컬 시장·먹거리", "식사", "시장/로컬", "중", 75, "점심"),
        ("streetfood", f"{label} 길거리 간식 존", "식사", "로컬푸드", "저", 55, "점심"),
        ("cafe_1", f"{label} 카페 거리(핫플)", "카페/휴식", "카페거리", "중", 65, None),
        ("view_1", f"{label} 전망 포인트(해질녘)", "야경", "전망", "저", 70, None),
        ("park", f"{label} 공원/정원 산책", "공원/정원", "공원", "저", 75, None),
        ("shopping", f"{label} 메인 쇼핑 스트리트", "쇼핑", "중심가", "중", 90, None),
        ("gallery", f"{label} 소규모 갤러리/전시", "전시/박물관", "문화권", "중", 70, None),
        ("night_market", f"{label} 야시장/마켓", "야시장/마켓", "야시장", "저", 80, "저녁"),
        ("dinner_1", f"{label} 저녁 식사 거리(현지식)", "식사", "식사권", "중", 85, "저녁"),
        ("dinner_2", f"{label} 저녁 식사(분위기픽)", "식사", "식사권", "고", 90, "저녁"),
        ("cafe_2", f"{label} 디저트/젤라또 카페", "카페/휴식", "디저트", "중", 55, None),
        ("photo", f"{label} 사진 스팟 산책", "사진스팟", "사진스팟", "저", 60, None),
        ("local_walk", f"{label} 로컬 동네 산책", "산책/드라이브", "로컬동네", "저", 75, None),
        ("view_2", f"{label} 야경 포인트(야간)", "야경", "야경", "저", 70, None),
    ]
    base_slug = re.sub(r"[^a-z0-9]+", "_", city_key.lower()).strip("_") or "city"
    out: List[Dict[str, Any]] = []
    for i, ((lat_d, lon_d), (sid, name, cat, area, tier, dur, meal)) in enumerate(zip(offs, specs)):
        dct: Dict[str, Any] = {
            "id": f"{base_slug}_gen_{i}_{sid}",
            "name": name,
            "category": cat,
            "area_tag": area,
            "price_tier": tier,
            "duration_minutes": dur,
            "lat": lat0 + lat_d,
            "lon": lon0 + lon_d,
            "image_url": pool[(h + i) % len(pool)],
        }
        if meal:
            dct["meal_type"] = meal
        out.append(dct)
    return out


def _generic_city_places_extended(
    city_key: str,
    lat0: float,
    lon0: float,
    *,
    start_index: int,
    count: int,
) -> List[Dict[str, Any]]:
    """
    후보 개수가 부족한 도시(또는 긴 여행일정)에서 중복을 줄이기 위한 확장 후보 생성기.
    - name에 인덱스를 넣어 CITY_CATALOG 내에서도 중복을 최대한 방지합니다.
    - 좌표는 도심 중심을 기준으로 방사형으로 분산합니다.
    """
    # 확장 후보는 사용하지 않습니다.
    return []

    label = CITY_DISPLAY_KR.get(city_key, city_key)
    pool = _GENERIC_WM_IMAGES
    h = sum(ord(c) for c in city_key)

    # (category, area_tag, price_tier, duration_minutes, meal_type_or_None)
    templates: List[Tuple[str, str, str, int, Optional[str]]] = [
        ("관광", "도심 랜드마크", "중", 110, None),
        ("관광", "구시가 산책", "저", 90, None),
        ("전시/박물관", "문화권 전시", "중", 100, None),
        ("야경", "전망 포인트", "저", 70, None),
        ("카페/휴식", "카페거리", "중", 65, None),
        ("식사", "로컬 시장·먹거리", "중", 75, "점심"),
        ("식사", "저녁 식사 거리", "중", 85, "저녁"),
        ("야시장/마켓", "야시장/마켓", "저", 80, "저녁"),
        ("산책/드라이브", "강변/로컬 산책", "저", 75, None),
        ("쇼핑", "쇼핑 스트리트", "중", 90, None),
        ("사진스팟", "사진 스팟 산책", "저", 60, None),
    ]

    base_slug = re.sub(r"[^a-z0-9]+", "_", city_key.lower()).strip("_") or "city"
    out: List[Dict[str, Any]] = []

    radii = [0.0035, 0.0055, 0.0075, 0.0105]
    for i in range(count):
        t_i = start_index + i
        cat, area_tag, tier, dur, meal = templates[t_i % len(templates)]
        angle = ((t_i * 37 + h) % 360) * math.pi / 180.0
        r = radii[(t_i + 2) % len(radii)] + ((t_i % 9) - 4) * 0.00015
        lat_d = r * math.sin(angle)
        lon_d = r * math.cos(angle)

        name = f"{label} 확장 후보 {t_i + 1} ({cat})"

        dct: Dict[str, Any] = {
            "id": f"{base_slug}_ext_{t_i}_{h}",
            "name": name,
            "category": cat,
            "area_tag": area_tag,
            "price_tier": tier,
            "duration_minutes": dur,
            "lat": lat0 + lat_d,
            "lon": lon0 + lon_d,
            "image_url": pool[(h + t_i) % len(pool)],
        }
        if meal:
            dct["meal_type"] = meal
        out.append(dct)

    return out


def _jitter_lonlat_for_visibility(lon: float, lat: float, day_idx: int, seq: int) -> Tuple[float, float]:
    """
    서로 다른 일차가 같은 장소(같은 좌표)를 반복하면 마커가 겹쳐 일부만 보입니다.
    정확도를 우선해서 기본은 지터를 거의 0으로 둡니다(원 좌표 사용).
    """
    return lon, lat


def _ensure_city_catalog_for_travel_top10() -> None:
    for cities in TRAVEL_TOP10_COUNTRY_CITIES.values():
        for ck in cities:
            if ck in CITY_CATALOG:
                continue
            coord = CITY_CENTER_COORDS.get(ck)
            if not coord:
                continue
            CITY_CATALOG[ck] = {"places": _generic_city_places(ck, coord[0], coord[1])}


_ensure_city_catalog_for_travel_top10()


# 일자별 마커 색상(밝은 지도에서도 구분되도록 채도 있는 색)
_DAY_MARKER_RGB: List[List[int]] = [
    [228, 77, 77],
    [59, 118, 224],
    [56, 163, 89],
    [156, 84, 214],
    [235, 146, 52],
    [45, 168, 168],
    [166, 112, 56],
]


def _normalize_itinerary_day_label(label: str) -> str:
    """Day 1 → 1일차 등 통일 (계획표·지도 공통)."""
    s = (label or "").strip()
    if s.lower().startswith("day "):
        try:
            n = int(s.split(" ", 1)[1])
            return f"{n}일차"
        except Exception:
            return s
    return s


def _map_place_label(name: str, max_len: int = 18) -> str:
    """지도 라벨용: 너무 긴 이름은 잘라 겹침을 줄입니다."""
    s = (name or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _deck_text_character_set_for_place_labels(rows: List[Dict[str, Any]]) -> str:
    """deck.gl TextLayer는 기본 아틀라스에 한글 등이 없어 characterSet을 지정해야 합니다."""
    chars: set[str] = set(" \u00b7\u2026")  # 공백, 가운뎃점, 말줄임(…)
    for r in rows:
        label = r.get("place_label") or ""
        for ch in label:
            chars.add(ch)
    return "".join(sorted(chars, key=ord)) if chars else " "


def itinerary_day_legend_entries(
    itinerary_data: Dict[str, Any],
) -> List[Tuple[str, int, int, int]]:
    """지도 마커/경로와 동일 팔레트로 (일자 라벨, R, G, B) 목록."""
    out: List[Tuple[str, int, int, int]] = []
    for day_idx, day in enumerate(itinerary_data.get("itineraries", []) or []):
        date_label = _normalize_itinerary_day_label(day.get("date_label", "")) or f"{day_idx + 1}일차"
        rgb = _DAY_MARKER_RGB[day_idx % len(_DAY_MARKER_RGB)]
        out.append((date_label, int(rgb[0]), int(rgb[1]), int(rgb[2])))
    return out


def build_profile_basis_narrative(profile: Dict[str, Any]) -> str:
    """
    일정표 제작에 실제로 쓰인 입력을 우선순위로 골라, 최대 5개 항목만 반영 근거로 서술합니다.
    (말투: 디시 느낌 위트·반말 혼합, 정보는 그대로)
    """
    comp = profile.get("companion_presence")
    intim = profile.get("relationship_degree")
    prefs = profile.get("preferences") or []
    budget = profile.get("budget")
    pers = profile.get("personality")
    mbti = (profile.get("mbti") or "").strip() or None
    age = profile.get("age")
    waiting_pref = profile.get("waiting_preference")

    candidates: List[Tuple[int, str, str]] = []

    if prefs:
        plist = ", ".join(str(p) for p in prefs)
        candidates.append(
            (
                100,
                "관심 취향",
                f"취향이 {plist} 쪽이길래, 비슷한 성격 장소끼리 한 권역에 몰아넣음. "
                "이동 지옥·지갑 텅텅 노이즈는 줄이려고 한 거고 인정? ㅋㅋ",
            )
        )

    if waiting_pref:
        waiting_map = {
            "선호": "웨이팅 감수해서라도 인기 많은 식사/카페 쪽에 더 비중 줌(맛이 먼저 ㅇㅇ).",
            "무관": "웨이팅 여부는 크게 신경 안 쓰고, 대신 다른 취향/예산 기준으로 우선순위 잡음.",
            "비선호": "줄 서는 거 좀 싫어서 대기 체감이 덜한 식사/카페 위주로 고름.",
            "극혐": "웨이팅은 생존 문제급이라 인기 과열 코스는 최대한 피하는 방향으로 조정함.",
        }
        candidates.append((84, "웨이팅 선호", waiting_map.get(str(waiting_pref), "웨이팅 우선순위를 일정에 반영함.")))

    if budget:
        if budget == "저":
            txt = (
                "예산 ‘저’면 솔직히 입장료·밥값 사치 후보는 순위 좀 밀었음. "
                "공짜·싼 맛·발 안 아픈 코스 비중 올림. 현실은 장렬히 반영했습니다."
            )
        elif budget == "고":
            txt = (
                "예산 ‘고’ 찍은 거 보고 체험·밥·전망 쪽 퀄은 좀 더 봐줌. "
                "완전 무제한은 아님(후보군 안에서만 돈다는 뜻)."
            )
        else:
            txt = (
                "예산 ‘중’ 기준으로 무난하게 명소·밥·휴식 밸런스 맞춤. "
                "과소비 창과 절약 창 사이 어디쯤."
            )
        candidates.append((99, "예산(경비)", txt))

    comp_map = {
        "배우자": "이동 과하게 늘어나면 싸우기 쉬우니 동선 짧게·대화·휴식 이어지게",
        "연인": "야경·식사·산책 스택 깨지면 안 됨(현타 방지용)",
        "친구": "액티·식사·카페 위주로 사교 부담 덜한 쪽",
        "부모": "도보·대기·계단 지옥 피하고 쉴 곳 있는 권역",
        "자녀": "놀이랑 쉼 번갈아—애랑 부모 둘 다 과부하 금지",
        "직장동료": "공용 관광·식사 중심, 밀착 동선은 ㄴㄴ",
        "처음봄": "전시·산책·시장처럼 대화 소재 터지기 쉬운 데 위주",
    }
    intim_map = {
        "뜨거움": "몰입 각 나오는 활동·야경·식사 비중 살짝 올림",
        "절친함": "편한 사이라 이동·밥 편차 좀 있어도 된다 보고 동선 촘촘히",
        "적당히 친함": "밀착·낯선 거 연속은 피하고 무난한 장소",
        "불편함": "혼잡·대기·비좁은 데 줄이고 휴식이랑 이동 분리",
        "서먹서먹함": "실내·전시·짧은 산책으로 대화 풀어주는 코스 우선",
    }

    if comp in (None, "", "선택안함"):
        candidates.append(
            (
                35,
                "동행",
                "동행 정보 비어 있음 → 1인 프리런 가정. 남이랑 맞춰야 하는 피로는 일정에 안 박았음 ㅇㅇ",
            )
        )
    elif comp == "혼자":
        candidates.append(
            (
                90,
                "동행",
                "혼행이라 눈치 안 보고 이동·밥·휴식 템포 갈겨도 된다는 전제. "
                "이게 진짜 자유여…(여행 한정)",
            )
        )
    else:
        hint = comp_map.get(comp, "동행 관계에 맞춰 사교·이동 부담 밸런스")
        body = f"동행이 ‘{comp}’니까 {hint} 쪽으로 밀도·장소 고름."
        if intim:
            body += f" 친밀도 ‘{intim}’면 {intim_map.get(intim, '동선·휴식 비중 조절')} 패턴."
        candidates.append((92, "동행·친밀도", body))

    if pers or mbti:
        pers_hints = {
            "외향적": "번잡해도 되긴 한데, 피로 누적 방지로 관광·휴식 교차 배치",
            "내향적": "자극 연타보단 전시·산책·카페로 템포 완화",
            "차분함": "동선 짧게, 이동 사이 휴식 슬롯 껌",
            "활동적": "도보·야외 비중 살짝↑ (체력·예산이 뭐라 하면 그때 후퇴)",
            "감성적": "야경·전시·카페 같은 분위기몰이 코스에 가중치",
        }
        parts = []
        if pers:
            parts.append(f"성격 '{pers}'면 {pers_hints.get(pers, '템포·휴식만 건드림')}")
        if mbti:
            parts.append(f"MBTI {mbti}는 활동량·사교 피로 보조 신호로만 참고(과신 금지)")
        candidates.append((78, "성격·MBTI", " ".join(parts) + "."))

    if age:
        candidates.append(
            (
                70,
                "나이",
                f"{age}세 기준으로 연속 도보·밤늦게까지 동선은 좀 완만하게. "
                "무리한 체력 배틀 코스는 지양.",
            )
        )

    candidates.sort(key=lambda x: -x[0])
    top = candidates[:5]

    if not top:
        return (
            "입력이 거의 없어서 ‘그냥 기본값 인생’ 일정으로 감. "
            "뭔가 찍어주면 그때 반영 드립 가능함."
        )

    out_lines = [
        "이번 **계획표** 박을 때 아래 **주요 입력(최대 5개)** 위주로 반영함. (투명하게 갈게 ㅇㅇ)",
        "",
    ]
    for i, (_prio, title, body) in enumerate(top, start=1):
        out_lines.append(f"**{i}. {title}** — {body}")
    return "\n".join(out_lines)


_BASIS_ITEM_LINE_RE = re.compile(
    r"^\*\*\d+\.\s+(.+?)\*\*\s*[—–\-]\s*(.+)$",
)


def _parse_profile_basis_sections(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """`(소개 마크다운, [(항목제목, 본문), ...])`. 번호 항목 라인은 `**1. 제목** — 본문` 형식."""
    text = (text or "").strip()
    if not text:
        return "", []
    intro_lines: List[str] = []
    items: List[Tuple[str, str]] = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            if not items:
                intro_lines.append(line)
            continue
        m = _BASIS_ITEM_LINE_RE.match(stripped)
        if m:
            items.append((m.group(1).strip(), m.group(2).strip()))
        elif items:
            title, body = items[-1]
            items[-1] = (title, (body + " " + stripped).strip())
        else:
            intro_lines.append(line)
    intro = "\n".join(intro_lines).strip()
    return intro, items


def _simple_markdown_bold_to_html(text: str) -> str:
    """반영 근거 소개 등 한두 군데 `**굵게**`만 HTML로 변환(나머지는 이스케이프)."""
    out: List[str] = []
    rest = text
    while True:
        a = rest.find("**")
        if a == -1:
            out.append(html.escape(rest))
            break
        out.append(html.escape(rest[:a]))
        b = rest.find("**", a + 2)
        if b == -1:
            out.append(html.escape(rest[a:]))
            break
        out.append("<strong>" + html.escape(rest[a + 2 : b]) + "</strong>")
        rest = rest[b + 2 :]
    return "".join(out)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """구면 거리 근사(미터). 도시 스케일에서 연속 방문 순서만 맞추는 용도."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def _place_coords_for_city(city: str) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for p in CITY_CATALOG.get(city, {}).get("places", []) or []:
        nm = (p.get("name") or "").strip()
        if not nm:
            continue
        try:
            out[nm] = (float(p["lat"]), float(p["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


_DAY_TIME_SLOTS_REORDERED = [
    "09:00-10:45",
    "11:00-12:30",
    "12:45-13:45",
    "14:00-15:45",
    "16:00-17:30",
    "18:00-19:30",
    "19:45-21:00",
]


def _reassign_day_time_slots(items: List[Dict[str, Any]]) -> None:
    if not items:
        return
    last_i = len(_DAY_TIME_SLOTS_REORDERED) - 1
    for i, it in enumerate(items):
        it["time_slot"] = _DAY_TIME_SLOTS_REORDERED[min(i, last_i)]


def _open_path_tour_cost(perm: Tuple[int, ...], dist: List[List[float]]) -> float:
    return sum(dist[perm[i]][perm[i + 1]] for i in range(len(perm) - 1))


def _nn_open_path_order(dist: List[List[float]]) -> List[int]:
    n = len(dist)
    best: Optional[List[int]] = None
    best_c = float("inf")
    for start in range(n):
        unvisited = set(range(n))
        unvisited.remove(start)
        order = [start]
        cur = start
        while unvisited:
            nxt = min(unvisited, key=lambda j, c=cur: dist[c][j])
            unvisited.remove(nxt)
            order.append(nxt)
            cur = nxt
        c = _open_path_tour_cost(tuple(order), dist)
        if c < best_c:
            best_c = c
            best = order
    return best if best is not None else list(range(n))


def _min_travel_perm_indices(dist: List[List[float]]) -> List[int]:
    n = len(dist)
    if n <= 1:
        return list(range(n))
    if n <= 9:
        return list(min(permutations(range(n)), key=lambda p: _open_path_tour_cost(p, dist)))
    return _nn_open_path_order(dist)


def _optimize_itinerary_visit_order(data: Dict[str, Any], city: str) -> None:
    """일차별로, 카탈로그에 좌표가 있는 정류만 골라 이동거리 합이 작게 순서를 재배치."""
    coord_map = _place_coords_for_city(city)
    if not coord_map:
        return
    for day in data.get("itineraries", []) or []:
        items = list(day.get("items") or [])
        if not items:
            continue
        if len(items) < 2:
            _reassign_day_time_slots(items)
            day["items"] = items
            continue
        geo_ix = [i for i, it in enumerate(items) if (it.get("name") or "").strip() in coord_map]
        other_ix = [i for i in range(len(items)) if i not in geo_ix]
        if len(geo_ix) < 2:
            _reassign_day_time_slots(items)
            day["items"] = items
            continue
        n = len(geo_ix)
        dist: List[List[float]] = [[0.0] * n for _ in range(n)]
        for a in range(n):
            for b in range(n):
                if a == b:
                    continue
                na = (items[geo_ix[a]].get("name") or "").strip()
                nb = (items[geo_ix[b]].get("name") or "").strip()
                la, lo = coord_map[na]
                lb, bo = coord_map[nb]
                dist[a][b] = _haversine_m(la, lo, lb, bo)
        perm = _min_travel_perm_indices(dist)
        ordered_geo = [geo_ix[perm[k]] for k in range(n)]
        new_order = ordered_geo + other_ix
        new_items = [items[j] for j in new_order]
        _reassign_day_time_slots(new_items)
        day["items"] = new_items


def _cluster_itinerary_days_by_proximity(
    data: Dict[str, Any],
    city: str,
) -> None:
    """
    '근처 장소'가 가급적 '같은 일자'에 오도록 day 단위 배치를 재구성합니다.
    - 좌표(카탈로그 lat/lon)가 있는 항목만으로 클러스터링
    - 각 day의 항목 개수(capacity)는 기존 len(items) 그대로 유지
    - 최종 동선(방문 순서)은 기존 `_optimize_itinerary_visit_order`에서 다시 정렬
    """
    coord_map = _place_coords_for_city(city)
    if not coord_map:
        return

    days = data.get("itineraries", []) or []
    k = len(days)
    if k <= 1:
        return

    capacities: List[int] = [len(d.get("items") or []) for d in days]
    total_items = sum(capacities)
    if total_items <= 0:
        return

    all_items: List[Dict[str, Any]] = []
    point_items: List[Tuple[Tuple[float, float], Dict[str, Any]]] = []
    no_coord_items: List[Dict[str, Any]] = []

    for d in days:
        for it in d.get("items", []) or []:
            if not isinstance(it, dict):
                continue
            all_items.append(it)
            nm = (it.get("name") or "").strip()
            if nm and nm in coord_map:
                lat, lon = coord_map[nm]
                point_items.append(((lat, lon), it))
            else:
                no_coord_items.append(it)

    if len(all_items) != total_items:
        # 타입 섞임 등 예외가 생기면 그냥 유지
        return
    if not point_items:
        return

    # day k개를 만들기 위한 center 후보(좌표)들: farthest point sampling
    # points: (lat, lon, item)
    points: List[Tuple[float, float, Dict[str, Any]]] = [(lat, lon, it) for ((lat, lon), it) in point_items]
    # center indices는 points 배열에서의 인덱스
    centers: List[int] = []
    centers.append(0)
    while len(centers) < min(k, len(points)):
        best_i = None
        best_d = -1.0
        for i in range(len(points)):
            if i in centers:
                continue
            lat_i, lon_i, _ = points[i]
            mn = float("inf")
            for c_i in centers:
                lat_c, lon_c, _ = points[c_i]
                mn = min(mn, _haversine_m(lat_i, lon_i, lat_c, lon_c))
            if mn > best_d:
                best_d = mn
                best_i = i
        if best_i is None:
            break
        centers.append(best_i)

    # centers가 k보다 작으면 마지막 중심을 복제해서 day 수 k에 맞춤
    while len(centers) < k:
        centers.append(centers[-1])

    remaining = capacities[:]
    assigned: List[List[Dict[str, Any]]] = [[] for _ in range(k)]

    # 포인트 아이템을 "가장 가까운 center가 확실한 애"부터 배치(closest distance 오름차순)
    point_entries: List[Tuple[float, List[int], Dict[str, Any]]] = []
    for lat, lon, it in points:
        dists = []
        for ci in range(k):
            lat_c, lon_c, _ = points[centers[ci]]
            dists.append(_haversine_m(lat, lon, lat_c, lon_c))
        nearest_ci = min(range(k), key=lambda x: dists[x])
        point_entries.append((dists[nearest_ci], dists, it))

    point_entries.sort(key=lambda x: x[0])

    for _near_d, dists, it in point_entries:
        ranked = sorted(range(k), key=lambda x: dists[x])
        placed = False
        for day_idx in ranked:
            if remaining[day_idx] > 0:
                assigned[day_idx].append(it)
                remaining[day_idx] -= 1
                placed = True
                break
        if not placed:
            # theoretically unreachable
            for day_idx in range(k):
                if remaining[day_idx] > 0:
                    assigned[day_idx].append(it)
                    remaining[day_idx] -= 1
                    break

    # 좌표 없는 항목은 남은 capacity 기준으로 순서대로 분배
    if no_coord_items:
        rr = 0
        for it in no_coord_items:
            while rr < k and remaining[rr] <= 0:
                rr += 1
            if rr >= k:
                break
            assigned[rr].append(it)
            remaining[rr] -= 1

    # rebuild itineraries
    data["itineraries"] = [
        {"date_label": f"{i + 1}일차", "items": assigned[i][:]}
        for i in range(k)
    ]


def _rebuild_itineraries_from_unique_place_list_by_proximity(
    data: Dict[str, Any],
    city: str,
    *,
    per_day_cap: int = 4,
) -> None:
    """
    1) 여행 전체에서 '장소(name)'를 유니크로 List Up
    2) 카탈로그 좌표 기준으로 근처끼리 묶이게 day에 배치
    3) 동일 장소는 여행 내에서 중복 추천하지 않음
    """
    coord_map = _place_coords_for_city(city)
    if not coord_map:
        return

    days = data.get("itineraries", []) or []
    k = len(days)
    if k <= 0:
        return

    # unique place list up (first appearance order)
    selected_names: List[str] = []
    name_to_item: Dict[str, Dict[str, Any]] = {}
    seen: set[str] = set()
    for day in days:
        for it in day.get("items", []) or []:
            if not isinstance(it, dict):
                continue
            nm = (it.get("name") or "").strip()
            if not nm or nm not in coord_map:
                continue
            if nm in seen:
                continue
            seen.add(nm)
            selected_names.append(nm)
            name_to_item[nm] = it

    if not selected_names:
        return

    total_cap = k * per_day_cap
    if len(selected_names) > total_cap:
        selected_names = selected_names[:total_cap]

    # 2) 선택된 유니크 장소가 부족하면, 카탈로그에서 아직 안 쓴 장소를 추가로 채움
    #    (확장 후보를 새로 생성하진 않고, CITY_CATALOG에 이미 있는 "명확한 추천"만 사용)
    if len(selected_names) < total_cap:
        catalog_places = CITY_CATALOG.get(city, {}).get("places", [])
        used_set = set(selected_names)
        # synthetic 아이템 생성용 임시 time_slot(이후 _reassign_day_time_slots에서 다시 덮어씀)
        placeholder_slot = _DAY_TIME_SLOTS_REORDERED[0] if _DAY_TIME_SLOTS_REORDERED else "09:00-10:45"
        for p in catalog_places:
            nm = (p.get("name") or "").strip()
            if not nm or nm in used_set:
                continue
            if nm not in coord_map:
                continue
            used_set.add(nm)
            selected_names.append(nm)
            # name_to_item에 synthetic item을 만들어 넣어, 뒤에서 day 배치 가능하게 함
            name_to_item[nm] = _synthetic_itinerary_item_from_candidate(
                p,
                placeholder_slot,
                auto_pad=False,
            )
            if len(selected_names) >= total_cap:
                break

    points: List[Tuple[float, float, str]] = []
    for nm in selected_names:
        lat, lon = coord_map[nm]
        points.append((lat, lon, nm))

    # day centers: farthest-point sampling (단, points 수보다 day 수가 많으면 복제)
    center_count = min(k, len(points))
    centers: List[int] = [0] if points else []
    while len(centers) < center_count and len(centers) < len(points):
        best_i = None
        best_d = -1.0
        for i in range(len(points)):
            if i in centers:
                continue
            lat_i, lon_i, _ = points[i]
            mn = float("inf")
            for c_i in centers:
                lat_c, lon_c, _ = points[c_i]
                mn = min(mn, _haversine_m(lat_i, lon_i, lat_c, lon_c))
            if mn > best_d:
                best_d = mn
                best_i = i
        if best_i is None:
            break
        centers.append(best_i)
    while len(centers) < k and centers:
        centers.append(centers[-1])

    capacities = [per_day_cap for _ in range(k)]
    assigned: List[List[Dict[str, Any]]] = [[] for _ in range(k)]

    # 가까운 center부터 배치 (capacity 우선)
    point_entries: List[Tuple[float, int, str, float, float]] = []
    for lat, lon, nm in points:
        dists: List[Tuple[float, int]] = []
        for day_idx in range(k):
            lat_c, lon_c, _ = points[centers[day_idx]] if points else (lat, lon, nm)
            dists.append((_haversine_m(lat, lon, lat_c, lon_c), day_idx))
        dists.sort(key=lambda x: x[0])
        best_dist, best_day = dists[0]
        point_entries.append((best_dist, best_day, nm, lat, lon))
    point_entries.sort(key=lambda x: x[0])

    for _dist, best_day, nm, _lat, _lon in point_entries:
        if capacities[best_day] <= 0:
            # 가까운 day가 꽉 차면, 다음 가까운 day로 재시도
            dists = []
            lat, lon = coord_map[nm]
            for day_idx in range(k):
                lat_c, lon_c, _ = points[centers[day_idx]] if points else (lat, lon, nm)
                dists.append((_haversine_m(lat, lon, lat_c, lon_c), day_idx))
            dists.sort(key=lambda x: x[0])
            for _d2, day_idx in dists:
                if capacities[day_idx] > 0:
                    assigned[day_idx].append(name_to_item[nm])
                    capacities[day_idx] -= 1
                    break
            continue
        assigned[best_day].append(name_to_item[nm])
        capacities[best_day] -= 1

    # rebuild itineraries
    data["itineraries"] = []
    for i in range(k):
        items = assigned[i]
        _reassign_day_time_slots(items)
        data["itineraries"].append({"date_label": f"{i + 1}일차", "items": items})


def _synthetic_itinerary_item_from_candidate(
    p0: Dict[str, Any],
    time_slot: str,
    *,
    auto_pad: bool = False,
) -> Dict[str, Any]:
    """일차·항목 보강용 최소 항목(후보 `name` 그대로)."""
    nm = p0["name"]
    ar = p0.get("area_tag", "")
    cat = p0.get("category", "관광")
    why_tail = (
        " 일정 일·이후 일차 항목이 비어서 후보를 순서대로 자동 보강함—현장에서 순서는 마음대로 조정 ㅇㅇ"
        if auto_pad
        else ""
    )
    return {
        "time_slot": time_slot,
        "type": cat,
        "name": nm,
        "area": ar,
        "why": (
            f"{nm}: 후보({ar or '도심'})에서 뽑은 코스.{why_tail}"
        ),
        "intro": (
            f"{nm}: {ar or '그 근처'}에서 {cat} 느낌. 대략 {p0.get('duration_minutes', 90)}분, "
            f"티어 {p0.get('price_tier', '중')} 쯤."
        ),
        "estimated_cost_range": p0.get("price_tier", "중"),
        "duration": p0.get("duration_minutes", 90),
    }


def _ensure_itinerary_covers_trip_days(
    data: Dict[str, Any],
    trip_days: int,
    candidates: List[Dict[str, Any]],
) -> None:
    """
    LLM이 `itineraries`를 trip_days보다 짧게 주거나 일부 일차 items가 비는 경우
    후보 장소를 순환하며 일차 수·최소 항목 수를 맞춤.
    """
    if trip_days < 1:
        return
    cand = [c for c in (candidates or []) if isinstance(c, dict) and (c.get("name") or "").strip()]
    if not cand:
        return
    raw = data.get("itineraries")
    if not isinstance(raw, list):
        raw = []
    days_out: List[Dict[str, Any]] = []
    for day in raw:
        if not isinstance(day, dict):
            continue
        label = (day.get("date_label") or "").strip()
        items = day.get("items")
        if not isinstance(items, list):
            items = []
        clean_items = [x for x in items if isinstance(x, dict)]
        # 앱 로직/시간슬롯 최적화가 전제하는 기본 단위를 4개로 맞춤
        clean_items = clean_items[:4]
        days_out.append({"date_label": label or f"{len(days_out) + 1}일차", "items": clean_items})
    if len(days_out) > trip_days:
        days_out = days_out[:trip_days]
    while len(days_out) < trip_days:
        days_out.append({"date_label": f"{len(days_out) + 1}일차", "items": []})
    slot_times = ["09:30-11:30", "12:00-13:00", "15:30-17:30", "18:00-19:30"]
    rr = 0
    used_names: set[str] = set()
    for i, day in enumerate(days_out):
        day["date_label"] = f"{i + 1}일차"
        items = day["items"]
        if len(items) > 4:
            items = items[:4]
        need_more = max(0, 4 - len(items))
        for k in range(need_more):
            # 가능한 한 중복 없이(후보 다 쓰면 그때부터 재사용)
            picked = None
            for _ in range(len(cand)):
                p0_try = cand[rr % len(cand)]
                rr += 1
                nm_try = (p0_try.get("name") or "").strip()
                if nm_try and nm_try not in used_names:
                    picked = p0_try
                    break
            p0 = picked if picked is not None else cand[(rr - 1) % len(cand)]
            nm_final = (p0.get("name") or "").strip()
            if nm_final:
                used_names.add(nm_final)
            items.append(
                _synthetic_itinerary_item_from_candidate(
                    p0,
                    slot_times[min(len(items), 3)],
                    auto_pad=True,
                )
            )
        day["items"] = items
    data["itineraries"] = days_out


def _coerce_itinerary_item_names_to_candidates(
    data: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> None:
    """
    지도/사진은 `name`이 후보군(카탈로그)과 정확히 같아야 표시됩니다.
    모델이 '콜로세움' 같이 후보 밖 이름을 주면, 후보 이름으로 강제 치환해 일정을 깨지지 않게 합니다.
    """
    cand = [c for c in (candidates or []) if isinstance(c, dict) and (c.get("name") or "").strip()]
    if not cand:
        return
    cand_by_name = {(c.get("name") or "").strip(): c for c in cand}
    valid_names = set(cand_by_name.keys())
    rr = 0
    for day in data.get("itineraries", []) or []:
        items = day.get("items") or []
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            nm = (it.get("name") or "").strip()
            if nm and nm in valid_names:
                # 후보 기반 메타만 부족하면 채움
                p0 = cand_by_name.get(nm)
                if p0:
                    it.setdefault("area", p0.get("area_tag", ""))
                    it.setdefault("estimated_cost_range", p0.get("price_tier", "중"))
                    it.setdefault("duration", p0.get("duration_minutes", 90))
                continue
            p0 = cand[rr % len(cand)]
            rr += 1
            it["name"] = p0["name"]
            it["area"] = p0.get("area_tag", "")
            it.setdefault("type", p0.get("category", "관광"))
            it["estimated_cost_range"] = p0.get("price_tier", "중")
            it["duration"] = p0.get("duration_minutes", 90)


def _dedupe_itinerary_items_across_trip_days(
    data: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> None:
    """
    여행 전체(모든 일차)에 대해 같은 '장소(name)'가 중복되지 않게 합니다.
    - OpenAI가 같은 장소를 여러 날/여러 번 배치해도, 사용하지 않은 후보로 자동 치환합니다.
    """
    cand = [c for c in (candidates or []) if isinstance(c, dict) and (c.get("name") or "").strip()]
    if not cand:
        return

    cand_by_name = {(c.get("name") or "").strip(): c for c in cand}
    valid_names = set(cand_by_name.keys())

    used: set[str] = set()
    replace_targets: List[Dict[str, Any]] = []

    for day in data.get("itineraries", []) or []:
        items = day.get("items") or []
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            nm = (it.get("name") or "").strip()
            if nm and nm in valid_names and nm not in used:
                used.add(nm)
            else:
                replace_targets.append(it)

    # 사용하지 않은 후보들을 앞에서부터 소진
    cand_queue = [c for c in cand if (c.get("name") or "").strip() and (c.get("name") or "").strip() not in used]
    q_i = 0
    for it in replace_targets:
        while q_i < len(cand_queue):
            p0 = cand_queue[q_i]
            q_i += 1
            nm = (p0.get("name") or "").strip()
            if nm and nm not in used:
                break
        else:
            break

        nm_final = (p0.get("name") or "").strip()
        if not nm_final:
            continue

        used.add(nm_final)
        ar = p0.get("area_tag", "") or ""
        cat = p0.get("category", "관광") or "관광"

        it["name"] = nm_final
        it["area"] = ar
        it["type"] = cat
        it["estimated_cost_range"] = p0.get("price_tier", "중")
        it["duration"] = p0.get("duration_minutes", 90)
        # 치환된 항목은 why/intro도 이름에 맞게 간단히 업데이트
        it["why"] = f"{nm_final}: 후보로만 짜서 동선·취향 밸런스 맞춘 중복 제거 버전 ㅇㅇ"
        it["intro"] = f"{nm_final}: {ar or '그 근처'}에서 {cat} 느낌. (중복 제거 자동치환)"


def finalize_itinerary_payload(
    data: Dict[str, Any], profile: Dict[str, Any], city: Optional[str] = None
) -> None:
    """항목 서술 보정 + 같은 날 방문 순서 거리 최소화(직선근사) + 반영 근거."""
    _normalize_itinerary_narratives(data)
    if city:
        _rebuild_itineraries_from_unique_place_list_by_proximity(data, city)
        _optimize_itinerary_visit_order(data, city)
    data["profile_basis"] = build_profile_basis_narrative(profile)


def _openai_client() -> Optional[Any]:
    if OpenAI is None:
        return None
    # 1) 우선순위: .env / 환경변수(가장 안전)
    api_key = os.getenv("OPENAI_API_KEY")

    # 2) fallback: Streamlit secrets.toml (파일이 없으면 FileNotFoundError가 발생할 수 있음)
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = None

    if not api_key:
        return None
    try:
        return OpenAI(api_key=api_key)
    except TypeError:
        # httpx/httpcore 버전 불일치로 OpenAI 클라이언트 생성이 실패할 수 있습니다.
        # 이 경우 앱은 더미 플랜 모드로 동작하도록 None을 반환합니다.
        return None
    except Exception:
        return None


def _waiting_score_from_candidate(candidate: Dict[str, Any]) -> int:
    """
    후보의 '웨이팅 체감'을 대략 추정해서 점수화합니다.
    0: 낮음, 1: 중간, 2: 높음
    - 실제 대기시간 데이터를 쓰진 못해서, 카테고리/가격 티어/식사 여부로 휴리스틱 처리.
    """
    cat = (candidate.get("category") or "").strip()
    meal_type = (candidate.get("meal_type") or "").strip()
    price = (candidate.get("price_tier") or "").strip()

    score = 0
    if cat in ("식사", "야시장/마켓"):
        score = 2
    elif cat in ("카페/휴식",):
        score = 1
    else:
        score = 0

    if meal_type:
        score = max(score, 2)

    if price == "고":
        score = min(2, score + 1)
    elif price == "저":
        score = max(0, score - 1)

    return score


def _reorder_candidates_by_waiting_preference(
    candidates: List[Dict[str, Any]],
    waiting_preference: Optional[str],
) -> List[Dict[str, Any]]:
    pref = waiting_preference or "무관"
    if pref == "무관":
        return candidates

    scored: List[Tuple[int, int, Dict[str, Any]]] = []
    for i, c in enumerate(candidates):
        scored.append((_waiting_score_from_candidate(c), i, c))

    if pref == "극혐" or pref == "비선호":
        # 웨이팅이 적은 쪽 우선
        scored.sort(key=lambda x: (x[0], x[1]))
    elif pref == "선호":
        # 웨이팅이 많은 쪽 우선
        scored.sort(key=lambda x: (-x[0], x[1]))

    return [c for _, _, c in scored]


def generate_itinerary_openai(
    profile: Dict[str, Any],
    city: str,
    trip_days: int,
    budget_tier: str,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    OpenAI로 일정 생성.
    - 후보군 기반이므로 환각을 줄이기 위해 candidates를 함께 전달합니다.
    - 실패 시(키 없음/파싱 실패) MVP 더미 플랜을 반환합니다.
    """
    client = _openai_client()
    if client is None:
        # 키가 없으면 UI는 동작하도록 "더미"를 제공합니다.
        candidates_sorted = _reorder_candidates_by_waiting_preference(
            candidates,
            profile.get("waiting_preference"),
        )
        candidates = candidates_sorted
        if len(candidates) >= 6:
            fallback_order = [
                candidates[0],
                candidates[1],
                candidates[4],
                candidates[2],
                candidates[5],
            ]
        else:
            fallback_order = list(candidates)
        chosen = fallback_order[: max(3, min(len(fallback_order), len(candidates), 6))]
        itineraries = []
        slot_times = ["09:30-11:30", "12:00-13:00", "15:30-17:30"]
        for d_i in range(trip_days):
            items = []
            if chosen:
                for slot in range(3):
                    p0 = chosen[(d_i * 3 + slot) % len(chosen)]
                    nm = p0["name"]
                    ar = p0.get("area_tag", "")
                    cat = p0.get("category", "관광")
                    items.append(
                        {
                            "time_slot": slot_times[slot],
                            "type": cat,
                            "name": nm,
                            "area": ar,
                            "why": (
                                f"데모 모드임—API 키 없어서 그냥 이렇게 보여주는 중. "
                                f"진짜 맞춤 코스는 `.env`에 키 넣고 오셈. 예산은 지금 '{profile.get('budget')}' 찍혀 있음."
                            ),
                            "intro": (
                                f"{nm}: {ar or '그 근처'}에서 {cat} 느낌 나는 후보. "
                                f"대충 {p0.get('duration_minutes', 90)}분짜리, 티어는 {p0.get('price_tier', '중')} 쯤 생각하면 됨."
                            ),
                            "estimated_cost_range": p0.get("price_tier", "중"),
                            "duration": p0.get("duration_minutes", 90),
                        }
                    )
            itineraries.append({"date_label": f"{d_i+1}일차", "items": items})
        out = {
            "summary": (
                f"{city} 예시 일정—키 없어서 샘플만 돌린 거. "
                "진지하게 쓰려면 OpenAI 연결 ㄱㄱ (노잼 방지)."
            ),
            "profile_basis": "",
            "itineraries": itineraries,
            "food_plan": (
                "점심·저녁은 후보에 밥집 있으면 거기서 골라 박는 구조. "
                "공복 각오하고 다니지 말기."
            ),
            "transport_notes": (
                "앱이 카탈로그 좌표 기준으로 같은 날 순서를 직선거리 합이 작게 다시 잡음. "
                "도로·대중교통 실측 경로는 아님—대략적인 동선 압축이라고 보면 됨."
            ),
            "budget_check": f"예산 티어 '{budget_tier}' 기준 데모 체크—실제 지갑은 본인 책임 ㅋㅋ",
            "alternatives": [
                "비 오면: 실내 전시·박물관 비중 올려서 우산 싸움 회피",
                "걷기 싫으면: 야경·카페 위주로 동선 압축 (다리는 스레드 닫음)",
            ],
        }
        _ensure_itinerary_covers_trip_days(out, trip_days, candidates)
        _coerce_itinerary_item_names_to_candidates(out, candidates)
        _dedupe_itinerary_items_across_trip_days(out, candidates)
        finalize_itinerary_payload(out, profile, city=city)
        return out

    # OpenAI에게 "후보군 이름/ID만" 쓰도록 강제
    prompt_candidates = [
        {
            "id": c["id"],
            "name": c["name"],
            "category": c.get("category", ""),
            "area_tag": c.get("area_tag", ""),
            "price_tier": c.get("price_tier", ""),
            "duration_minutes": c.get("duration_minutes"),
            "meal_type": c.get("meal_type"),
            "waiting_level": (
                "높음" if _waiting_score_from_candidate(c) == 2 else "중간" if _waiting_score_from_candidate(c) == 1 else "낮음"
            ),
        }
        for c in candidates
    ]

    system_msg = (
        "You generate a travel itinerary. Use ONLY the provided candidates. "
        "Do not invent places. Output MUST be valid JSON only. "
        "All user-facing narrative fields (summary, profile_basis, each item's why and intro, "
        "food_plan, transport_notes, budget_check, alternatives) MUST be written in Korean.\n\n"
        "STYLE for those Korean fields: write like casual Korean internet board posts (디시인사이드/갤 톤). "
        "Short, punchy lines; 반말·낮춤 OK; light wit, irony, or harmless meme energy allowed "
        "(e.g. occasional ㅋㅋ, 인정?, 현피는 아니고 현타만, 노돈·노잼 방지 같은 표현). "
        "Do NOT use slurs, hate, harassment, or insults toward real groups. Stay playful, not hostile. "
        "Jokes must not replace facts: still tie picks to profile/budget/candidates and keep intros grounded in candidate fields."
    )

    user_msg = {
        "profile": profile,
        "city": city,
        "trip_days": trip_days,
        "budget_tier": budget_tier,
        "candidates": prompt_candidates,
        "rules": [
            "Use only candidate 'name' values for 'name'.",
            f"Itineraries MUST be a JSON array of exactly {trip_days} day objects (same as trip_days). "
            "Each day needs date_label and items. Do NOT return fewer days than trip_days; do NOT merge multiple days into one.",
            "For each day output 3~5 items.",
            "Waiting preference (profile.waiting_preference) 고려: '선호'면 waiting_level='높음'을 우선, '무관'은 무시, '비선호/극혐'이면 waiting_level='낮음/중간'을 우선. 식사/카페/야시장 후보 선택에 특히 반영.",
            "Within each day, order items so consecutive stops are geographically close (minimize backtracking). "
            "The app post-process may reorder stops using catalog coordinates to shorten the open-path distance.",
            "Include at least one meal in each day when candidates include meal_type=점심/저녁.",
            "Include at least one cafe/relax style item (카페/휴식 or category contains '카페' or '휴식') across the full trip.",
            "Estimated cost should be one of candidate.price_tier (저/중/고) or a close match.",
            "Time slots can be approximate but must be in 'HH:MM-HH:MM' format.",
            "EVERY item MUST include 'why' (추천 이유): 1~3 short sentences in Korean, 디시식 위트 허용, 반드시 프로필·취향·예산·동행 맥락·동선 흐름을 근거로 묶을 것.",
            "EVERY item MUST include 'intro' (간단 소개): 1~2 short sentences in Korean, 같은 톤 유지; 후보 필드(category, area_tag, price_tier, duration)만 근거로 쓰고 주소·역사·수상 실적 등 환각 금지.",
            "summary / food_plan / transport_notes / budget_check / alternatives 도 같은 말투로 짧고 읽히게.",
            "Set 'profile_basis' to an empty string \"\" (the app replaces it with a detailed rule-based rationale).",
        ],
        "output_schema": {
            "summary": "string",
            "profile_basis": "string",
            "itineraries": [
                {
                    "date_label": "Day 1..",
                    "items": [
                        {
                            "time_slot": "string",
                            "type": "string",
                            "name": "string (must match candidate.name)",
                            "area": "string",
                            "why": "string (Korean, 추천 이유)",
                            "intro": "string (Korean, 간단 소개)",
                            "estimated_cost_range": "string",
                            "duration": "number"
                        }
                    ],
                }
            ],
            "food_plan": "string",
            "transport_notes": "string",
            "budget_check": "string",
            "alternatives": ["string", "string"]
        },
    }

    # SDK 사용: JSON 파싱 가능한 응답을 기대. (환경에 따라 모델/옵션은 달라질 수 있어 예외 처리)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(user_msg, ensure_ascii=False)},
        ],
        temperature=0.82,
    )

    content = resp.choices[0].message.content or ""
    try:
        data = json.loads(content)
        _ensure_itinerary_covers_trip_days(data, trip_days, candidates)
        _coerce_itinerary_item_names_to_candidates(data, candidates)
        _dedupe_itinerary_items_across_trip_days(data, candidates)
        finalize_itinerary_payload(data, profile, city=city)
        return data
    except Exception:
        # JSON code fence 제거 시도
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1] if "```" in cleaned else cleaned
        data = json.loads(cleaned)
        _ensure_itinerary_covers_trip_days(data, trip_days, candidates)
        _coerce_itinerary_item_names_to_candidates(data, candidates)
        _dedupe_itinerary_items_across_trip_days(data, candidates)
        finalize_itinerary_payload(data, profile, city=city)
        return data


def _normalize_itinerary_narratives(data: Dict[str, Any]) -> None:
    """items에 why/intro가 비어 있으면 한국어 기본 문구로 보강 (표/지도 일관성)."""
    for day in data.get("itineraries", []) or []:
        for item in day.get("items", []) or []:
            name = (item.get("name") or "").strip() or "이 코스"
            if not (item.get("why") or "").strip():
                item["why"] = (
                    f"{name}—오늘 동선·예산 보면 여기 넣는 게 덜 억울해서 넣음. "
                    "(별다른 음모 없음)"
                )
            if not (item.get("intro") or "").strip():
                cat = (item.get("type") or "").strip()
                ar = (item.get("area") or "").strip()
                tail = []
                if cat:
                    tail.append(cat)
                if ar:
                    tail.append(ar)
                suffix = ", ".join(tail) if tail else "도시 여행 코스"
                item["intro"] = f"{name}: 대충 {suffix} 쪽 방문지. 후보 데이터 기준임."


def itinerary_to_rows(itinerary_data: Dict[str, Any], city: str) -> List[Dict[str, Any]]:
    catalog_places = CITY_CATALOG.get(city, {}).get("places", [])
    photo_by_place_name = {
        p["name"]: (p.get("image_url") or "").strip() for p in catalog_places if p.get("name")
    }

    def _normalize_type(t: str) -> str:
        s = (t or "").strip()
        sl = s.lower()
        mapping = [
            (["tour", "sight", "sightseeing", "tourism"], "관광"),
            (["food", "lunch", "dinner", "breakfast"], "식사"),
            (["cafe", "coffee", "dessert"], "카페/휴식"),
            (["museum", "exhibit", "gallery"], "전시/박물관"),
            (["night", "nightview", "yank"], "야경"),
            (["shopping"], "쇼핑"),
            (["activity", "experience"], "액티비티"),
            (["rest", "relax"], "카페/휴식"),
        ]
        for keys, out in mapping:
            if any(k in sl for k in keys):
                return out
        return s

    def _normalize_cost(cost: Any) -> str:
        s = ("" if cost is None else str(cost)).strip()
        sl = s.lower()
        if sl in ["low", "저", "budget-low"]:
            return "저"
        if sl in ["medium", "mid", "중", "budget-mid"]:
            return "중"
        if sl in ["high", "고", "budget-high"]:
            return "고"
        # "저/중/고" 형태가 아니라면 그대로 둠
        return s

    rows: List[Dict[str, Any]] = []
    for day in itinerary_data.get("itineraries", []):
        date_label = _normalize_itinerary_day_label(day.get("date_label", ""))
        for item in day.get("items", []):
            why_txt = (item.get("why") or item.get("reason") or "").strip()
            intro_txt = (
                item.get("intro")
                or item.get("introduction")
                or item.get("brief")
                or ""
            ).strip()
            pname = item.get("name", "") or ""
            pic = photo_by_place_name.get(pname, "").strip()
            rows.append(
                {
                    "일자": date_label,
                    "시간대": item.get("time_slot", ""),
                    "구분": _normalize_type(item.get("type", "")),
                    "장소": pname,
                    "대표 사진": pic if pic else None,
                    "권역": item.get("area", ""),
                    "비용(추정)": _normalize_cost(item.get("estimated_cost_range", "")),
                    "소요(분)": item.get("duration", ""),
                    "추천 이유": why_txt,
                    "간단 소개": intro_txt,
                }
            )
    return rows


def build_map_layers(
    city: str,
    itinerary_data: Dict[str, Any],
) -> Optional[pdk.Deck]:
    catalog_places = CITY_CATALOG.get(city, {}).get("places", [])
    by_name = {p["name"]: p for p in catalog_places}

    # 밝은 베이스맵(무료 Carto Positron 스타일)
    _light_map_style = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

    rows: List[Dict[str, Any]] = []
    path_data: List[Dict[str, Any]] = []

    for day_idx, day in enumerate(itinerary_data.get("itineraries", []) or []):
        date_label = _normalize_itinerary_day_label(day.get("date_label", "")) or f"{day_idx + 1}일차"
        rgb = _DAY_MARKER_RGB[day_idx % len(_DAY_MARKER_RGB)]
        fill_rgba = [rgb[0], rgb[1], rgb[2], 240]
        path_lonlat: List[List[float]] = []

        for seq, item in enumerate(day.get("items", []) or [], start=1):
            name = item.get("name")
            if not name or name not in by_name:
                continue
            p = by_name[name]
            lon_f = float(p["lon"])
            lat_f = float(p["lat"])
            lon_v, lat_v = _jitter_lonlat_for_visibility(lon_f, lat_f, day_idx, seq)
            path_lonlat.append([lon_v, lat_v])
            head = f"[{date_label}] {seq}번째 | {p['name']}"
            area = str(p.get("area_tag", "") or "")
            cost = str(p.get("price_tier", "") or "")
            tooltip = (
                f"{html.escape(head)}<br>"
                f"{html.escape(area)}<br>"
                f"{html.escape(f'비용:{cost}')}"
            )
            rows.append(
                {
                    "lon": lon_v,
                    "lat": lat_v,
                    "fill_color": fill_rgba,
                    "seq_label": str(seq),
                    "place_label": _map_place_label(p["name"]),
                    "tooltip": tooltip,
                }
            )

        if len(path_lonlat) >= 2:
            path_data.append(
                {
                    "path": path_lonlat,
                    "color": [rgb[0], rgb[1], rgb[2], 100],
                }
            )

    if not rows:
        return None

    layers_list: List[pdk.Layer] = []

    if path_data:
        layers_list.append(
            pdk.Layer(
                "PathLayer",
                data=path_data,
                get_path="path",
                get_color="color",
                width_min_pixels=2,
                width_max_pixels=4,
                cap_rounded=True,
                joint_rounded=True,
                pickable=False,
            )
        )

    layers_list.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=rows,
            get_position="[lon, lat]",
            get_fill_color="fill_color",
            radius_min_pixels=8,
            radius_max_pixels=11,
            pickable=True,
            stroked=True,
            get_line_color=[255, 255, 255, 230],
            line_width_min_pixels=1,
        )
    )

    # 방문 순번(마커 안쪽·약간 위)
    layers_list.append(
        pdk.Layer(
            "TextLayer",
            data=rows,
            get_position="[lon, lat]",
            get_text="seq_label",
            get_size=6,
            get_color=[255, 255, 255, 255],
            get_text_anchor="middle",
            get_alignment_baseline="center",
            outline_color=[35, 35, 35, 230],
            outline_width=2,
            get_pixel_offset=[0, -2],
            background=False,
            size_units="pixels",
            billboard=True,
            pickable=False,
            font_family="Arial",
        )
    )

    # 여행지 이름(마커 아래). 한글은 characterSet 없으면 아틀라스에 글리프가 없어 안 보임.
    place_label_charset = _deck_text_character_set_for_place_labels(rows)
    layers_list.append(
        pdk.Layer(
            "TextLayer",
            data=rows,
            get_position="[lon, lat]",
            get_text="place_label",
            character_set=place_label_charset,
            get_size=8,
            get_color=[42, 42, 42, 255],
            get_text_anchor="middle",
            get_alignment_baseline="top",
            outline_color=[255, 255, 255, 235],
            outline_width=2,
            get_pixel_offset=[0, 12],
            background=False,
            size_units="pixels",
            billboard=True,
            pickable=False,
            font_family="Malgun Gothic, Apple SD Gothic Neo, Noto Sans CJK KR, sans-serif",
        )
    )

    view_state = pdk.ViewState(
        latitude=rows[0]["lat"],
        longitude=rows[0]["lon"],
        zoom=11,
        pitch=0,
    )

    return pdk.Deck(
        map_style=_light_map_style,
        layers=layers_list,
        initial_view_state=view_state,
        tooltip={"html": "{tooltip}"},
    )


def _render_app_top_bar() -> None:
    org = html.escape(APP_BRAND_ORG)
    st.markdown(
        f"""
        <div class="app-brand-bar-bleed">
          <div class="app-brand-inner">
            <div class="app-brand-left">
              <div class="app-brand-logo-icon">{_TRAVEL_LOGO_SVG}</div>
              <div class="app-brand-titles">
                <p class="app-brand-title">{html.escape(APP_BRAND_TITLE)}</p>
                <p class="app-brand-sub">{html.escape(APP_BRAND_SUBTITLE)}</p>
              </div>
            </div>
            <div class="app-brand-org-wrap">
              <span class="app-brand-org">{org}</span>
            </div>
          </div>
        </div>
        <div class="app-brand-flow-spacer"></div>
        """,
        unsafe_allow_html=True,
    )


def _pj_loading_overlay_html() -> str:
    """
    로딩 중 'P'가 위에서부터 그라데이션으로 'J'로 바뀌는 애니메이션.
    """
    return """
    <style>
      .pj-loading-wrap{
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 999999;
        pointer-events: none;
      }
      .pj-word{
        position: relative;
        width: 200px;
        height: 120px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        font-size: 104px;
        letter-spacing: -0.06em;
        font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        line-height: 1;
      }
      .pj-word .p{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(40,10,25,0.80);
        /* 위에서 아래로 사라지기: 보이는 영역을 아래쪽으로 점점 좁힘 */
        clip-path: inset(0% 0% 0% 0%);
        animation: pjPDisappear 1.1s ease-in-out infinite;
      }
      .pj-word .j{
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(40,10,25,0.95);
        /* 위에서 아래로 나타나기: 보이는 영역을 위쪽에서부터 넓힘 */
        clip-path: inset(100% 0% 0% 0%);
        animation: pjJAppear 1.1s ease-in-out infinite;
      }
      @keyframes pjPDisappear{
        0%{ clip-path: inset(0% 0% 0% 0%); }
        100%{ clip-path: inset(100% 0% 0% 0%); }
      }
      @keyframes pjJAppear{
        0%{ clip-path: inset(100% 0% 0% 0%); }
        100%{ clip-path: inset(0% 0% 0% 0%); }
      }
    </style>
    <div class="pj-loading-wrap" aria-label="loading">
      <div class="pj-word">
        <div class="p">P</div>
        <div class="j">J</div>
      </div>
    </div>
    """


def main() -> None:
    _render_app_top_bar()

    if "itinerary" not in st.session_state:
        st.session_state.itinerary = None
    if "last_request" not in st.session_state:
        st.session_state.last_request = None

    # ---- 사이드바: 전체 입력(실제 st.sidebar 사용) ----
    with st.sidebar:
        with st.container(border=True):
            st.markdown("# 사용자 정보입력")
            st.divider()
            st.markdown("## 성별")
            gender = st.selectbox(
            "성별",
            ["선택안함", "여", "남", "기타"],
            label_visibility="collapsed",
            key="sidebar_gender",
        )

            st.divider()
            st.markdown("## 성격/선호")
            st.markdown("### 성격")
            personality = st.selectbox(
            "성격",
            ["선택안함", "외향적", "내향적", "차분함", "활동적", "감성적"],
            label_visibility="collapsed",
            key="sidebar_personality",
        )
            st.markdown("### MBTI")
            mbti = st.text_input(
            "MBTI",
            placeholder="예: ENFP",
            label_visibility="collapsed",
            key="sidebar_mbti",
        )
            st.markdown("### 나이")
            age = st.number_input(
            "나이",
            min_value=0,
            max_value=120,
            value=0,
            step=1,
            label_visibility="collapsed",
            key="sidebar_age",
        )

            st.divider()
            st.markdown("## 취향")
            st.markdown("### 관심분야")
            preference_list = [
            "자연",
            "산책/드라이브",
            "공원/정원",
            "해변",
            "카페",
            "브런치",
            "디저트",
            "야시장/마켓",
            "쇼핑",
            "명품/구제(빈티지)",
            "기념품",
            "전시",
            "박물관",
            "야경",
            "액티비티",
            "미술",
            "클래식 공연",
            "테마파크",
            "로컬맛집",
            "전통시장",
            "온천/스파",
            "사진스팟",
            "유적지/역사",
            "테크/게임(체험형)",
            "수상레저",
            ]
            preferences = st.multiselect(
            "관심분야",
            preference_list,
            default=["로컬맛집"],
            label_visibility="collapsed",
            key="sidebar_preferences",
        )

            st.markdown("### 웨이팅")
            waiting_preference = st.selectbox(
            "웨이팅",
            ["선호", "무관", "비선호", "극혐"],
            index=1,
            label_visibility="collapsed",
            key="sidebar_waiting",
        )

            st.divider()
            st.markdown("## 예산/여행조건")
            st.markdown("### 경비(예산등급)")
            budget_tier = st.selectbox(
            "경비(예산등급)",
            ["저", "중", "고"],
            label_visibility="collapsed",
            key="sidebar_budget",
        )
            st.markdown("### 여행기간")
            trip_days = st.selectbox(
            "여행기간",
            [f"{n}박{n+1}일" for n in range(1, 10)],
            label_visibility="collapsed",
            key="sidebar_trip_days",
        )
            trip_nights = int(str(trip_days).split("박", 1)[0])
            trip_days_n = trip_nights + 1

            st.divider()
            st.markdown("## 동행인")
            st.markdown("### 동행하는 사람")
            companion_options = [
            "선택안함",
            "혼자",
            "배우자",
            "연인",
            "친구",
            "부모",
            "자녀",
            "직장동료",
            "처음봄",
            ]
            companion_presence = st.selectbox(
            "동행하는 사람",
            companion_options,
            label_visibility="collapsed",
            key="sidebar_companion",
        )
            st.markdown("### 친밀도")
            relationship_degree_selected = st.selectbox(
            "친밀도",
            ["뜨거움", "절친함", "적당히 친함", "서먹서먹함", "불편함"],
            index=2,
            key="relationship_degree_select",
            label_visibility="collapsed",
        )
            relationship_degree = (
                relationship_degree_selected
                if companion_presence not in ("선택안함", "혼자")
                else None
            )
            st.caption(
                "혼자·선택안함이면 친밀도는 그냥 UI 장식이고 일정엔 안 끼어듦. (착각 금지)"
            )

        country_map = TRAVEL_TOP10_COUNTRY_CITIES

        with st.container(border=True):
            st.markdown("# 목표국가/도시")
            st.caption(
                "국가·도시는 국제 관광 수요 상위권에서 자주 거론되는 지역을 바탕으로 구성(대략적 선별)."
            )
            st.divider()
            st.markdown("## 국가")
            country = st.selectbox(
                "국가",
                list(country_map.keys()),
                label_visibility="collapsed",
                key="sidebar_country",
            )
            st.divider()
            st.markdown("## 주요도시")
            city = st.selectbox(
                "주요도시",
                country_map[country],
                label_visibility="collapsed",
                key="sidebar_city",
                format_func=lambda c: f"{CITY_DISPLAY_KR.get(c, c)} ({c})",
            )

        generate_btn = st.button("여행계획 생성", type="primary")

        profile = {
            "gender": None if gender == "선택안함" else gender,
            "personality": None if personality == "선택안함" else personality,
            "mbti": mbti.strip() or None,
            "age": None if age == 0 else age,
            "budget": budget_tier,
            "preferences": preferences,
            "waiting_preference": waiting_preference,
            "companion_presence": None if companion_presence == "선택안함" else companion_presence,
            "relationship_degree": relationship_degree,
        }

        if generate_btn:
            st.session_state.last_request = {
                "profile": profile,
                "city": city,
                "trip_days": trip_days_n,
                "budget_tier": budget_tier,
            }
            candidates = CITY_CATALOG.get(city, {}).get("places", [])
            itinerary_data = generate_itinerary_openai(
                profile=profile,
                city=city,
                trip_days=trip_days_n,
                budget_tier=budget_tier,
                candidates=candidates,
            )
            st.session_state.itinerary = itinerary_data

    # ---- 메인: 여행계획 + 지도 ----
    st.subheader("여행계획표")

    itinerary_data = st.session_state.get("itinerary")
    if not itinerary_data:
        st.info(
            "왼쪽 **사이드바**에서 입력 넣고 `여행계획 생성` 눌러봐. "
            "표랑 지도에 마커 뜸. 안 누르면 영원히 빈 화면임."
        )
        return

    _basis = (itinerary_data.get("profile_basis") or "").strip()
    _summary = (itinerary_data.get("summary") or "").strip()
    _bc = (itinerary_data.get("budget_check") or "").strip()

    st.markdown(
        f'<div class="plan-strip">'
        f'<p class="plan-strip-label">도시</p>'
        f'<p class="plan-strip-body plan-strip-mono">'
        f"{html.escape(CITY_DISPLAY_KR.get(city, city))} ({html.escape(city)})"
        f"</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if _summary:
        st.markdown(
            f'<div class="plan-strip">'
            f'<p class="plan-strip-label">요약</p>'
            f'<p class="plan-strip-body">{html.escape(_summary)}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="plan-strip">'
            '<p class="plan-strip-label">요약</p>'
            '<p class="plan-strip-body" style="opacity:0.72;">요약 없음</p>'
            "</div>",
            unsafe_allow_html=True,
        )

    if _basis:
        intro_md, basis_items = _parse_profile_basis_sections(_basis)
        basis_chunks: List[str] = [
            '<div class="plan-strip">',
            '<p class="plan-strip-label">반영 근거</p>',
        ]
        if intro_md:
            basis_chunks.append(
                f'<div class="plan-basis-intro">{_simple_markdown_bold_to_html(intro_md)}</div>'
            )
        if basis_items:
            boxes = []
            for bt, bb in basis_items:
                boxes.append(
                    '<div class="plan-basis-box">'
                    f'<p class="plan-basis-box-title">{html.escape(bt)}</p>'
                    f'<p class="plan-basis-box-body">{html.escape(bb)}</p>'
                    "</div>"
                )
            basis_chunks.append('<div class="plan-basis-inner">' + "".join(boxes) + "</div>")
        elif not intro_md:
            basis_chunks.append(f'<p class="plan-strip-body">{html.escape(_basis)}</p>')
        basis_chunks.append("</div>")
        st.markdown("".join(basis_chunks), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="plan-strip">'
            '<p class="plan-strip-label">반영 근거</p>'
            '<p class="plan-strip-body" style="opacity:0.72;">'
            "(반영 근거 텅텅—입력이 없거나 덮어쓰기 실패한 듯)"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    if _bc:
        st.markdown(
            f'<div class="plan-strip">'
            f'<p class="plan-strip-label">예산 체크</p>'
            f'<p class="plan-strip-body">{html.escape(_bc)}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="plan-strip">'
            '<p class="plan-strip-label">예산 체크</p>'
            '<p class="plan-strip-body" style="opacity:0.72;">—</p>'
            "</div>",
            unsafe_allow_html=True,
        )

    rows = itinerary_to_rows(itinerary_data, city)
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning(
            "일정표에 뿌릴 행이 없음. 후보 장소랑 API가 준 이름이 안 맞거나 데이터가 비었을 수 있음—한번만 더 확인 ㄱ."
        )
    else:
        disp_cols = [
            "일자",
            "시간대",
            "구분",
            "장소",
            "대표 사진",
            "권역",
            "비용(추정)",
            "소요(분)",
            "추천 이유",
            "간단 소개",
        ]
        for c in disp_cols:
            if c not in df.columns:
                df[c] = pd.NA if c == "대표 사진" else ""
        st.dataframe(
            df[disp_cols].sort_values(["일자", "시간대"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "대표 사진": st.column_config.ImageColumn(
                    "대표 사진",
                    width="medium",
                    help="후보 장소별 현장 사진(위키미디어 커먼스, 저작권은 각 파일 설명 참고)",
                ),
            },
        )

    st.divider()
    st.subheader("도시 지도 (상부 계획 장소 마커)")
    deck = build_map_layers(city=city, itinerary_data=itinerary_data)
    if deck is None:
        st.warning(
            "지도 마커 못 찾음. 후보 카탈로그 `name`이랑 일정 `name`이 **글자 하나까지** 같아야 함. "
            "틀리면 지도는 공허."
        )
    else:
        leg = itinerary_day_legend_entries(itinerary_data)
        if leg:
            col_map, col_leg = st.columns([4.6, 1.15], gap="small")
            with col_map:
                st.pydeck_chart(
                    deck,
                    use_container_width=True,
                    height=520,
                    key="travel_plan_map_v2",
                )
                st.caption(
                    "같은 **일차**는 색이 같음(원이랑 선). 숫자는 그날 **방문 순서**고, 선은 표 순서대로 이은 거임. "
                    "순서는 카탈로그 좌표 기준 **직선거리 합이 짧게** 맞춰짐(도로 최단은 아님)."
                )
            with col_leg:
                rows_html = []
                for label, r, g, b in leg:
                    safe_lbl = html.escape(str(label))
                    rows_html.append(
                        '<div style="display:flex;align-items:center;margin-bottom:7px;">'
                        '<span style="display:inline-block;width:12px;height:12px;min-width:12px;border-radius:50%;'
                        f"background:rgb({r},{g},{b});margin-right:8px;"
                        'box-shadow:0 0 0 1px rgba(0,0,0,0.18);"></span>'
                        f'<span style="font-size:0.84rem;line-height:1.2;">{safe_lbl}</span>'
                        "</div>"
                    )
                st.markdown(
                    '<div style="position:sticky;top:12px;z-index:6;'
                    "background:rgba(255,255,255,0.97);padding:10px 8px 10px 10px;border-radius:8px;"
                    'border:1px solid #d8d8d8;box-shadow:0 2px 6px rgba(0,0,0,0.07);">'
                    '<div style="font-weight:600;font-size:0.88rem;margin-bottom:9px;padding-bottom:7px;'
                    'border-bottom:1px solid #e8e8e8;color:#222;">일자별 색상</div>'
                    + "".join(rows_html)
                    + "</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.pydeck_chart(
                deck,
                use_container_width=True,
                height=520,
                key="travel_plan_map_v2",
            )
            st.caption(
                "같은 **일차**는 색이 같음(원이랑 선). 숫자는 **방문 순서**, 선은 표 순서 연결. "
                "직선거리 기준으로 순서는 짧게 잡혀 있음(실제 차·지하철 경로 최적은 아님)."
            )

    st.markdown("---")
    st.markdown(f"**이동 동선 팁:** {itinerary_data.get('transport_notes','')}")
    st.markdown("**식사 계획:** " + str(itinerary_data.get("food_plan", "")))

    alts = itinerary_data.get("alternatives", []) or []
    if alts:
        st.markdown("**대안 플랜**")
        for a in alts[:3]:
            st.write(f"- {a}")


if __name__ == "__main__":
    main()

