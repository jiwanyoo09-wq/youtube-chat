import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
from googleapiclient.discovery import build
import re

youtube = build(
    "youtube",
    "v3",
    developerKey=st.secrets["YOUTUBE_API_KEY"]
)

# -------------------------
# 페이지 설정
# -------------------------
st.set_page_config(page_title="YouTube 댓글 분석기", layout="wide")
st.title("📺 YouTube 댓글 분석 대시보드")
st.write("유튜브 영상 댓글을 수집하고 분석합니다.")

# -------------------------
# 입력 UI
# -------------------------
API_KEY = st.text_input("YouTube API Key", type="password")
video_url = st.text_input("유튜브 영상 URL 입력")

max_comments = st.slider(
    "수집할 댓글 수",
    min_value=20,
    max_value=10000,
    value=500,
    step=20
)

# -------------------------
# video id 추출
# -------------------------
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# -------------------------
# 댓글 수집
# -------------------------
def get_comments(video_id, api_key, max_results):
    youtube = build("youtube", "v3", developerKey=api_key)

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    while request and len(comments) < max_results:
        response = request.execute()

        for item in response["items"]:
            snip = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "comment": snip["textDisplay"],
                "likeCount": snip["likeCount"],
                "publishedAt": snip["publishedAt"]
            })

            if len(comments) >= max_results:
                break

        request = youtube.commentThreads().list_next(request, response)

    return pd.DataFrame(comments)

# -------------------------
# 워드클라우드
# -------------------------
def make_wordcloud(text):
    wc = WordCloud(
        background_color="white",
        width=1200,
        height=600
    ).generate(text)

    return wc

# -------------------------
# 실행 버튼
# -------------------------
if st.button("댓글 분석 시작"):

    if not API_KEY:
        st.error("API Key를 입력하세요.")
        st.stop()

    video_id = extract_video_id(video_url)

    if not video_id:
        st.error("유효한 유튜브 URL이 아닙니다.")
        st.stop()

    with st.spinner("댓글 수집 중..."):
        df = get_comments(video_id, API_KEY, max_comments)

    st.success(f"{len(df)}개 댓글 수집 완료!")

    # -------------------------
    # 데이터 전처리
    # -------------------------
    df["publishedAt"] = pd.to_datetime(df["publishedAt"])
    df["hour"] = df["publishedAt"].dt.hour

    # -------------------------
    # 데이터 출력
    # -------------------------
    st.subheader("📄 데이터 미리보기")
    st.dataframe(df.head(20))

    # -------------------------
    # 시간대별 분석
    # -------------------------
    st.subheader("⏰ 시간대별 댓글 추이")

    hourly = df.groupby("hour").size().reset_index(name="count")

    fig1, ax1 = plt.subplots()
    sns.lineplot(data=hourly, x="hour", y="count", marker="o", ax=ax1)
    ax1.set_title("시간대별 댓글 수")
    st.pyplot(fig1)

    # -------------------------
    # 좋아요 분석
    # -------------------------
    st.subheader("👍 좋아요 수 분석")

    fig2, ax2 = plt.subplots()
    sns.histplot(df["likeCount"], bins=30, kde=True, ax=ax2)
    ax2.set_title("댓글 좋아요 분포")
    st.pyplot(fig2)

    # -------------------------
    # 워드클라우드
    # -------------------------
    st.subheader("☁️ 워드클라우드")

    text = " ".join(df["comment"].astype(str))
    wc = make_wordcloud(text)

    fig3, ax3 = plt.subplots(figsize=(12, 6))
    ax3.imshow(wc)
    ax3.axis("off")
    st.pyplot(fig3)

    # -------------------------
    # TOP 단어
    # -------------------------
    st.subheader("🔤 자주 등장한 단어 TOP 20")

    words = text.split()
    counter = Counter(words)

    top_words = pd.DataFrame(counter.most_common(20), columns=["word", "count"])

    fig4, ax4 = plt.subplots()
    sns.barplot(data=top_words, x="count", y="word", ax=ax4)
    st.pyplot(fig4)

    # -------------------------
    # 다운로드
    # -------------------------
    st.subheader("💾 CSV 다운로드")

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "CSV 다운로드",
        csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )
