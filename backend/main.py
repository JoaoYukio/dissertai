import os
import tempfile
import subprocess
from typing import Optional, List
from fastapi import FastAPI, File, UploadFile, Body, Query, HTTPException
import uvicorn
import openai
from openai import OpenAI
from moviepy import VideoFileClip

from database import SessionLocal, Tarefa, init_db

app = FastAPI()

if not os.getenv("OPENAI_API_KEY"):
    raise HTTPException(status_code=401, detail="Chave de API de OpenAI não fornecida")

openai.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def on_startup():
    init_db()


@app.post("/transcrever-audio")
async def transcrever_e_gerar_tarefas(file: UploadFile = File(...)):
    """
    Recebe um arquivo MP4, extrai apenas o áudio usando MoviePy,
    e então transcreve via OpenAI Whisper. Depois, gera uma lista
    de tarefas a partir do texto transcrito.
    """
    # 1) Ler o conteúdo do arquivo de vídeo
    video_bytes = await file.read()

    # 2) Cria um arquivo temporário para salvar o vídeo (MP4)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
        tmp_in_name = tmp_in.name
        tmp_in.write(video_bytes)

    # 3) Cria um arquivo temporário para salvar o áudio extraído (MP3)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
        tmp_out_name = tmp_out.name

    # 4) Extrair áudio do MP4 usando MoviePy
    try:
        clip = VideoFileClip(tmp_in_name)
        clip.audio.write_audiofile(tmp_out_name)  # Salva como MP3
        clip.close()
    finally:
        # Após extrair o áudio, removemos o arquivo de vídeo
        os.remove(tmp_in_name)

    # 5) Chamar a API Whisper para transcrever o áudio
    try:
        with open(tmp_out_name, "rb") as audio_file:
            transcription_response = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            print(transcription_response)
    finally:
        # Remove o arquivo de áudio temporário
        os.remove(tmp_out_name)

    # 6) Obter o texto transcrito
    transcript = transcription_response.text

    # 7) Gerar lista de tarefas via ChatCompletion (usando, por exemplo, gpt-4o-mini)
    prompt_para_tarefas = f"""
    Abaixo está a transcrição de uma conversa (oriunda de um vídeo MP4).
    Identifique as tarefas ou próximos passos mencionados, retorne uma lista
    clara e objetiva:

    Transcrição:
    {transcript}

    Responda apenas com as tarefas identificadas.
    """
    try:
        completion_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Gera uma lista de tarefas a partir de uma transcrição de uma conversa."
                },
                {"role": "user", "content": prompt_para_tarefas}
            ]
        )
        print(completion_response)
        tarefas_texto = completion_response.choices[0].message.content
    except Exception as e:
        raise e

    return {
        "transcricao": transcript,
        "tarefas": tarefas_texto
    }
@app.post("/tarefas")
def adicionar_tarefas(
    tarefas: List[str] = Body(...),
    usuario_id: Optional[int] = Query(None, description="ID opcional do usuário")
):
    """
    Recebe uma lista de tarefas em JSON e (opcionalmente) um usuario_id via query param.
    Exemplo:
    POST /tarefas?usuario_id=10
    body: ["Tarefa A", "Tarefa B"]
    """
    db = SessionLocal()
    try:
        for tarefa_desc in tarefas:
            nova_tarefa = Tarefa(descricao=tarefa_desc)
            if usuario_id is not None:
                nova_tarefa.usuario_id = usuario_id
            db.add(nova_tarefa)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return {"status": "ok", "tarefas_inseridas": len(tarefas)}

@app.get("/tarefas")
def listar_tarefas(usuario_id: Optional[int] = Query(None)):
    """
    Se usuario_id for informado, retorna tarefas só daquele usuário.
    Caso contrário, retorna todas.
    GET /tarefas?usuario_id=10
    """
    db = SessionLocal()
    try:
        query = db.query(Tarefa)
        if usuario_id is not None:
            query = query.filter(Tarefa.usuario_id == usuario_id)
        resultado = query.all()
        # Converter para uma lista de dicts
        tarefas = []
        for item in resultado:
            tarefas.append({
                "id": item.id,
                "descricao": item.descricao,
                "usuario_id": item.usuario_id
            })
        return tarefas
    finally:
        db.close()

@app.get("/tarefas/{tarefa_id}")
def obter_tarefa(tarefa_id: int):
    db = SessionLocal()
    try:
        tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
        if not tarefa:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return {
            "id": tarefa.id,
            "descricao": tarefa.descricao,
            "usuario_id": tarefa.usuario_id
        }
    finally:
        db.close()


@app.put("/tarefas/{tarefa_id}")
def atualizar_tarefa(
    tarefa_id: int,
    descricao: Optional[str] = Body(None),
    usuario_id: Optional[int] = Body(None)
):
    """
    Atualiza descrição e/ou usuario_id de uma tarefa.
    Exemplo de body:
    {
      "descricao": "Novo texto da tarefa",
      "usuario_id": 20
    }
    """
    db = SessionLocal()
    try:
        tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
        if not tarefa:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        if descricao is not None:
            tarefa.descricao = descricao
        if usuario_id is not None:
            tarefa.usuario_id = usuario_id
        db.commit()
        db.refresh(tarefa)
        return {
            "id": tarefa.id,
            "descricao": tarefa.descricao,
            "usuario_id": tarefa.usuario_id
        }
    finally:
        db.close()

@app.delete("/tarefas/{tarefa_id}")
def deletar_tarefa(tarefa_id: int):
    db = SessionLocal()
    try:
        tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
        if not tarefa:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        db.delete(tarefa)
        db.commit()
        return {"status": "ok", "mensagem": "Tarefa removida com sucesso."}
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)