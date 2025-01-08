import os
import tempfile
import openai
from supabase import create_client, Client
from moviepy import VideoFileClip
from openai import OpenAI

import streamlit as st

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.warning("Supabase URL e/ou Anon Key não foram definidas. Ajuste as variáveis de ambiente.")
else:
    st.session_state.setdefault("supabase_client", create_client(SUPABASE_URL, SUPABASE_ANON_KEY))

if not os.getenv("OPENAI_API_KEY"):
    st.warning("OPENAI_API_KEY não foi definida. Defina via variável de ambiente ou diretamente no código.")
else:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def create_task(description: str):
    """
    Cria uma nova task no Supabase, inserindo `description`.
    """
    supabase: Client = st.session_state["supabase_client"]
    resp = supabase.table("tasks").insert({"description": description}).execute()
    return resp


def list_tasks():
    """
    Retorna todas as tasks da tabela 'tasks'.
    """
    supabase: Client = st.session_state["supabase_client"]
    resp = supabase.table("tasks").select("*").execute()
    return resp


def update_task(task_id: int, new_description: str):
    """
    Atualiza a descrição de uma task pelo ID.
    """
    supabase: Client = st.session_state["supabase_client"]
    resp = supabase.table("tasks") \
        .update({"description": new_description}) \
        .eq("id", task_id) \
        .execute()
    return resp


def delete_task(task_id: int):
    """
    Deleta uma task pelo ID.
    """
    supabase: Client = st.session_state["supabase_client"]
    resp = supabase.table("tasks") \
        .delete() \
        .eq("id", task_id) \
        .execute()
    return resp


def transcribe_video(video_bytes: bytes) -> str:
    """
    Recebe os bytes de um arquivo .mp4, extrai o áudio e usa Whisper
    para transcrever via OpenAI.
    Retorna o texto transcrito.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
        tmp_video_name = tmp_video.name
        tmp_video.write(video_bytes)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_audio:
        tmp_audio_name = tmp_audio.name

    try:
        clip = VideoFileClip(tmp_video_name)
        clip.audio.write_audiofile(tmp_audio_name)
        clip.close()
    finally:
        os.remove(tmp_video_name)

    try:
        with open(tmp_audio_name, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
    finally:
        os.remove(tmp_audio_name)

    return transcription.text


def generate_tasks_from_transcript(transcript: str):
    """
    Usa ChatCompletion (GPT-3.5 ou GPT-4) para transformar um texto (transcript)
    em uma lista de tarefas (strings).
    """
    prompt = f"""
    Abaixo está a transcrição de uma conversa (oriunda de um vídeo MP4).
    Identifique as tarefas ou próximos passos mencionados, retorne uma lista
    clara e objetiva:

    Transcrição:
    {transcript}

    Responda apenas com as tarefas identificadas.
    """

    response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Gera uma lista de tarefas a partir de uma transcrição de uma conversa."
                },
                {"role": "user", "content": prompt}
            ]
        )
    tasks_text = response.choices[0].message.content.strip()
    lines = tasks_text.split("\n")
    tasks = []
    for line in lines:
        clean_line = line.strip("-• ").strip()
        if clean_line:
            tasks.append(clean_line)
    return tasks
