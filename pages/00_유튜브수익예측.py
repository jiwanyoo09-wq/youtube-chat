import streamlit as st
import pandas as pd
from googleapiclient.discovery import build

# -----------------------------
# 설정
# -----------------------------
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=YOUTUBE_API_KEY
)

# -----------------------------
# 채널 검색
# -----------------------------
from googleapiclient.errors import HttpError

def search_channel(channel_name):
    try:
        request = youtube.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            maxResults=1
        )

        response = request.execute()

        if len(response["items"]) == 0:
            return None

        return response["items"][0]["snippet"]["channelId"]

    except HttpError as e:
        st.error(f"HTTP Error: {e.status_code}")
        st.code(str(e))
        raise


# -----------------------------
# 채널 정보 조회
# -----------------------------
def get_channel_info(channel_id):

    request = youtube.channels().list(
        part="snippet,statistics",
        id=channel_id
    )

    response = request.execute()

    item = response["items"][0]

    return {
        "title": item["snippet"]["title"],
        "subscribers": int(
            item["statistics"].get(
                "subscriberCount", 0
            )
        ),
        "views": int(
            item["statistics"].get(
                "viewCount", 0
            )
        ),
        "videos": int(
            item["statistics"].get(
                "videoCount", 0
            )
        )
    }


# -----------------------------
# 최근 영상 가져오기
# -----------------------------
def get_recent_videos(channel_id):

    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=20
    )

    response = request.execute()

    video_ids = [
        item["id"]["videoId"]
        for item in response["items"]
    ]

    stats_request = youtube.videos().list(
        part="statistics",
        id=",".join(video_ids)
    )

    stats_response = stats_request.execute()

    views = []

    for item in stats_response["items"]:
        views.append(
            int(
                item["statistics"].get(
                    "viewCount", 0
                )
            )
        )

    return views


# -----------------------------
# 수익 계산
# -----------------------------
def estimate_revenue(monthly_views):

    # CPM 가정
    low_cpm = 1.0
    avg_cpm = 3.5
    high_cpm = 8.0

    low = (monthly_views / 1000) * low_cpm
    avg = (monthly_views / 1000) * avg_cpm
    high = (monthly_views / 1000) * high_cpm

    return low, avg, high


# -----------------------------
# UI
# -----------------------------
st.title("📺 YouTube 수익 분석기")

channel_name = st.text_input(
    "채널명을 입력하세요"
)

if st.button("분석 시작"):

    with st.spinner("채널 분석 중..."):

        channel_id = search_channel(
            channel_name
        )

        if not channel_id:
            st.error("채널을 찾을 수 없습니다.")
            st.stop()

        info = get_channel_info(
            channel_id
        )

        views = get_recent_videos(
            channel_id
        )

        avg_views = (
            sum(views) / len(views)
            if views else 0
        )

        estimated_monthly_views = (
            avg_views * 8
        )

        low, avg, high = estimate_revenue(
            estimated_monthly_views
        )

    st.subheader(info["title"])

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "구독자",
        f"{info['subscribers']:,}"
    )

    col2.metric(
        "총 조회수",
        f"{info['views']:,}"
    )

    col3.metric(
        "영상 수",
        f"{info['videos']:,}"
    )

    st.divider()

    st.write(
        f"최근 영상 평균 조회수 : "
        f"{avg_views:,.0f}"
    )

    st.write(
        f"예상 월 조회수 : "
        f"{estimated_monthly_views:,.0f}"
    )

    st.subheader("💰 예상 월 광고 수익")

    st.success(
        f"낮음 : ${low:,.0f}"
    )

    st.info(
        f"평균 : ${avg:,.0f}"
    )

    st.warning(
        f"높음 : ${high:,.0f}"
    )

    st.subheader("📈 예상 연 수익")

    st.write(
        f"${avg * 12:,.0f}"
    )

    df = pd.DataFrame({
        "구간": ["낮음", "평균", "높음"],
        "월수익($)": [low, avg, high]
    })

    st.bar_chart(
        df.set_index("구간")
    )
