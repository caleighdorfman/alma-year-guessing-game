import random
import re
from pathlib import Path

import streamlit as st


CLIP_SECONDS = [10, 20, 30, 40, 50, 60]
AUDIO_FORMATS = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}
APP_DIR = Path(__file__).resolve().parent
DEPLOYED_AUDIO_DIR = APP_DIR / "Recordings"
LOCAL_AUDIO_DIR = Path.home() / "Downloads" / "Recordings"
AUDIO_EXTENSIONS = set(AUDIO_FORMATS)
APP_HAS_AUDIO = any(
    path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    for path in APP_DIR.iterdir()
)
AUDIO_DIR = (
    DEPLOYED_AUDIO_DIR
    if DEPLOYED_AUDIO_DIR.is_dir()
    else APP_DIR
    if APP_HAS_AUDIO
    else LOCAL_AUDIO_DIR
)

st.set_page_config(
    page_title="Alma: Guess the Year",
    page_icon="🎵",
    layout="centered",
)


@st.cache_data
def load_songs(audio_dir):
    songs = []
    unsupported_files = []

    for path in sorted(audio_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_FORMATS:
            continue

        year_match = re.search(r"(?<!\d)(?:19|20)\d{2}(?!\d)", path.stem)
        if year_match:
            year = int(year_match.group())
        elif path.stem.lower() == "vi11age alma mater":
            year = 2011
        else:
            short_year_match = re.search(
                r"^v(?:illage)?[ _-]?(\d{2})(?!\d)",
                path.stem,
                re.IGNORECASE,
            )
            if short_year_match is None:
                unsupported_files.append(path.name)
                continue

            short_year = int(short_year_match.group(1))
            if short_year <= 26:
                year = 2000 + short_year
            elif short_year >= 85:
                year = 1900 + short_year
            else:
                unsupported_files.append(path.name)
                continue

        songs.append(
            {
                "path": path,
                "title": path.stem,
                "year": year,
            }
        )

    return songs, unsupported_files


def shuffled_song_order(songs):
    remaining = list(range(len(songs)))
    order = []

    while remaining:
        weights = [
            3 if 2013 <= songs[index]["year"] <= 2026 else 1
            for index in remaining
        ]
        selected = random.choices(remaining, weights=weights, k=1)[0]
        order.append(selected)
        remaining.remove(selected)

    return order


st.markdown(
    """<style>
.stApp {background-color:#10131b;color:#f6f7fb}
.block-container {max-width:690px;padding-top:3rem}
h1 {text-align:center}
</style>""",
    unsafe_allow_html=True,
)

songs = []
unsupported_files = []
if not AUDIO_DIR.is_dir():
    st.error(f"Could not find your song folder: {AUDIO_DIR}")
    st.info("Put the audio files in a folder named 'Recordings' inside Downloads.")
    st.stop()

songs, unsupported_files = load_songs(AUDIO_DIR)
if unsupported_files:
    st.warning(
        "Skipped files without a four-digit year in the filename: "
        + ", ".join(unsupported_files)
    )
if not songs:
    st.error("No playable audio files with a year in the filename were found.")
    st.stop()

song_signature = tuple((song["path"].name, song["year"]) for song in songs)
if st.session_state.get("song_signature") != song_signature:
    st.session_state.song_signature = song_signature
    st.session_state.order = shuffled_song_order(songs)
    st.session_state.round = 0
    st.session_state.guesses = []
    st.session_state.finished = False
    st.session_state.wins = 0
    st.session_state.game_started = False

if not st.session_state.game_started:
    st.title("🎵 ALMA: Guess the Year")
    st.caption("Listen to each recording and guess the year it is from.")
    st.write(
        "Each round is one song. You get six guesses, starting with a "
        "10-second clip; another 10 seconds unlocks after each guess."
    )
    st.write(f"Ready to play with **{len(songs)} songs**?")
    if st.button("▶️ Play", use_container_width=True):
        st.session_state.game_started = True
        st.rerun()
    st.stop()

if st.session_state.round >= len(st.session_state.order):
    st.title("🎵 ALMA: Guess the Year")
    st.success(f"You played all {len(songs)} songs!")
    st.write(f"You guessed **{st.session_state.wins}** correctly.")
    if st.button("Play again", use_container_width=True):
        st.session_state.order = shuffled_song_order(songs)
        st.session_state.round = 0
        st.session_state.guesses = []
        st.session_state.finished = False
        st.session_state.wins = 0
        st.rerun()
    st.stop()

song = songs[st.session_state.order[st.session_state.round]]
year = song["year"]
guesses = st.session_state.guesses

st.title("🎵 ALMA: Guess the Year")
st.write(f"**{len(CLIP_SECONDS) - len(guesses)} guesses remaining**")

seconds = (
    None
    if st.session_state.finished
    else CLIP_SECONDS[min(len(guesses), len(CLIP_SECONDS) - 1)]
)
st.subheader("🔊 Mystery recording")
st.audio(
    str(song["path"]),
    format=AUDIO_FORMATS[song["path"].suffix.lower()],
    end_time=seconds,
)
st.caption(
    "Full recording unlocked!"
    if seconds is None
    else f"Clip unlocked: first {seconds} second{'s' if seconds != 1 else ''}"
)

for number, guess in enumerate(guesses, start=1):
    if guess == year:
        st.success(f"Guess {number}: {guess} — Correct!")
    elif guess < year:
        st.info(f"Guess {number}: {guess} — Too early ⬆️")
    else:
        st.info(f"Guess {number}: {guess} — Too late ⬇️")

if not st.session_state.finished:
    with st.form("guess", clear_on_submit=True):
        guess_text = st.text_input(
            "What year was it?",
            placeholder="Enter a 4-digit year",
            max_chars=4,
        )
        submit = st.form_submit_button("Submit guess", use_container_width=True)

    if submit:
        if (
            len(guess_text) != 4
            or not guess_text.isascii()
            or not guess_text.isdigit()
        ):
            st.warning("Please enter a 4-digit year.")
        else:
            guess = int(guess_text)
            st.session_state.guesses.append(guess)
            if guess == year or len(st.session_state.guesses) == len(CLIP_SECONDS):
                st.session_state.finished = True
            if guess == year:
                st.session_state.wins += 1
            st.rerun()
else:
    if guesses[-1] == year:
        st.balloons()
        st.success("🎉 You got it!")
    else:
        st.error("No guesses left!")

    st.markdown(f"### The answer was **{year}**")
    st.write(f"🎶 {song['title']}")
    if st.session_state.round + 1 < len(st.session_state.order):
        if st.button("Play again →", use_container_width=True):
            st.session_state.round += 1
            st.session_state.guesses = []
            st.session_state.finished = False
            st.rerun()
    elif st.button("Play again", use_container_width=True):
        st.session_state.order = shuffled_song_order(songs)
        st.session_state.round = 0
        st.session_state.guesses = []
        st.session_state.finished = False
        st.session_state.wins = 0
        st.rerun()
