# database.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./tarefas.db"  # Exemplo com SQLite local

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False)
    usuario_id = Column(Integer, index=True)  # Simples: armazenamos ID do usuário

def init_db():
    Base.metadata.create_all(bind=engine)
