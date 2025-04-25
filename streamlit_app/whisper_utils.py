from openai import OpenAI
import streamlit as st
from moviepy.editor import VideoFileClip
import tempfile

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def extract_audio_from_video(video_path: str) -> str:
    """Convertit la vidéo en audio WAV"""
    video = VideoFileClip(video_path)
    audio_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    video.audio.write_audiofile(audio_path, codec='pcm_s16le')
    return audio_path

def transcribe_audio(file_path: str) -> str:
    """Transcription robuste avec conversion vidéo -> audio"""
    try:
        # Si c'est une vidéo, extraire l'audio
        if file_path.endswith((".mp4", ".mov", ".mpeg4")):
            file_path = extract_audio_from_video(file_path)
        
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="fr"
            )
        return transcript
    except Exception as e:
        st.error(f"""
        **Échec de la transcription :**  
        {str(e)}  
        Formats supportés : MP3, WAV, MP4 (avec audio standard)
        """)
        raise
