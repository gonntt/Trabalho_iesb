import asyncio
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.schema import PrimaryKeyConstraint

Base = declarative_base()

# SQLAlchemy models
class Vertice(Base):
    __tablename__ = 'vertices'

    id = Column(Integer, nullable=False)  # ID for the vertex within a specific labyrinth/graph
    labirinto_id = Column(Integer, ForeignKey('labirintos.id'), nullable=False)  # Reference to the labyrinth/graph
    adjacentes = Column(String)  # Assuming adjacent vertices are stored as a comma-separated string
    tipo = Column(Integer)  # Defining behavior of the vertex | 0 = Normal, 1 = Entrada, 2 = Saida

    # Relationships
    labirinto = relationship("Labirinto", back_populates="vertices")

    # Composite Primary Key (id, labirinto_id)
    __table_args__ = (PrimaryKeyConstraint('id', 'labirinto_id', name='pk_vertice'),)

    def __repr__(self):
        return f"<Vertice(id={self.id}, labirinto_id={self.labirinto_id})>"


class Labirinto(Base):
    __tablename__ = 'labirintos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vertices = relationship("Vertice", back_populates="labirinto")
    entrada = Column(Integer)
    dificuldade = Column(String)

    def __repr__(self):
        return f"<Labirinto(id={self.id}, entrada={self.entrada}, dificuldade={self.dificuldade})>"


class Grupo(Base):
    __tablename__ = 'grupos'
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True)
    nome = Column(String)
    labirintos_concluidos = Column(String)  # Assuming labirintos_concluidos is stored as a comma-separated string


class SessaoWebSocket(Base):
    __tablename__ = 'sessoes_websocket'
    
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    grupo_id = Column(String, ForeignKey('grupos.id'))  # Use String type for UUID
    conexao = Column(String)


# Pydantic models
class VerticeModel(BaseModel):
    id: int
    labirintoId: int
    adjacentes: List[int]
    tipo: int


class LabirintoModel(BaseModel):
    vertices: List[VerticeModel]
    entrada: int
    dificuldade: str  


class GrupoModel(BaseModel):
    nome: str
    labirintos_concluidos : Optional[List[int]] = None


# DTOs
class VerticeDto(BaseModel):
    id: int
    adjacentes: List[int]
    tipo: int


class LabirintoDto(BaseModel):
    LabirintoId: int
    Dificuldade: str
    Completo: bool
    Passos: int
    Exploracao: float


class GrupoDto(BaseModel):
    id: UUID
    nome: str
    labirintos_concluidos: Optional[List[int]]


# Create the database and tables
engine = create_engine('sqlite:///./db.sqlite3', echo=True)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)

# Função para obter uma sessão de banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Inicializando a aplicação FastAPI
app = FastAPI()

# Gerenciar conexões WebSocket ativas
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{grupo_id}/{labirinto_id}")
async def websocket_endpoint(websocket: WebSocket, grupo_id: UUID, labirinto_id: int):
    await manager.connect(websocket)  # Aceita a conexão WebSocket
    db = next(get_db())  # Obtém a conexão com o banco de dados

    try:
        # Obtém o labirinto e seu vértice de entrada
        labirinto = db.query(Labirinto).filter(Labirinto.id == labirinto_id).first()
        if not labirinto:
            await websocket.send_text("Labirinto não encontrado.")
            manager.disconnect(websocket)
            return

        # Obtém o vértice de entrada
        vertice_atual = db.query(Vertice).filter(Vertice.labirinto_id == labirinto_id, Vertice.id == labirinto.entrada).first()

        if not vertice_atual:
            await manager.send_message("Vértice de entrada não encontrado.", websocket)
            manager.disconnect(websocket)
            return

        # Envia o vértice de entrada para o cliente
        await manager.send_message(f"Vértice atual: {vertice_atual.id}, Adjacentes: {vertice_atual.adjacentes.split(',')}", websocket)

        # Loop para interações do cliente
        while True:
            try:
                # Espera por uma mensagem do cliente com timeout de 60 segundos
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                if data.startswith("ir:"):
                    # Extrai o id do vértice desejado
                    try:
                        vertice_desejado_id = int(data.split(":")[1].strip())
                    except ValueError:
                        await manager.send_message("Comando inválido. Use 'ir: id_do_vertice'", websocket)
                        continue

                    # Verifica se o vértice desejado está nos adjacentes do vértice atual
                    adjacentes = list(map(int, vertice_atual.adjacentes.split(","))) if vertice_atual else []
                    if vertice_desejado_id not in adjacentes:
                        await manager.send_message("Vértice inválido.", websocket)
                        continue

                    # Move para o vértice desejado
                    vertice_atual = db.query(Vertice).filter(Vertice.labirinto_id == labirinto_id, Vertice.id == vertice_desejado_id).first()

                    if not vertice_atual:
                        await manager.send_message("Erro ao acessar o vértice desejado.", websocket)
                        continue

                    # Envia as informações do novo vértice ao cliente
                    await manager.send_message(f"Vértice atual: {vertice_atual.id}, Adjacentes: {vertice_atual.adjacentes.split(',')}", websocket)
                else:
                    await manager.send_message("Comando não reconhecido. Use 'ir: id_do_vertice' para se mover.", websocket)
            
            except asyncio.TimeoutError:
                # Timeout de 60 segundos sem mensagem, desconecta o WebSocket
                await manager.send_message("Conexão encerrada por inatividade.", websocket)
                manager.disconnect(websocket)
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Grupo {grupo_id} desconectado.")


# Endpoints REST (mantidos como na versão anterior)
@app.post("/grupo")
async def registrar_grupo(grupo: GrupoModel):
    db = next(get_db())
    grupo_db = Grupo(id=uuid.uuid4(), nome=grupo.nome)
    db.add(grupo_db)
    db.commit()
    grupo_dto = GrupoDto(id=grupo_db.id, nome=grupo_db.nome, labirintos_concluidos=[])
    return {"GrupoId": grupo_dto.id}


@app.post("/labirinto")
async def criar_labirinto(labirinto: LabirintoModel):
    db = next(get_db())

    # Cria o labirinto e o adiciona à sessão
    labirinto_db = Labirinto(entrada=labirinto.entrada, dificuldade=labirinto.dificuldade)
    db.add(labirinto_db)

    for vertice in labirinto.vertices:
        # Verifica se o vértice já existe antes de inseri-lo
        existing_vertice = db.query(Vertice).filter_by(id=vertice.id, labirinto_id=labirinto_db.id).first()
        if existing_vertice:
            raise HTTPException(status_code=400, detail=f"Vértice com id {vertice.id} já existe para o labirinto {labirinto_db.id}")

        vertice_db = Vertice(
            id=vertice.id,
            labirinto_id=labirinto_db.id,
            adjacentes=','.join(map(str, vertice.adjacentes)),
            tipo=vertice.tipo
        )
        db.add(vertice_db)

    # Comita todas as alterações de uma vez
    db.commit()

    return {"LabirintoId": labirinto_db.id}


class WebSocketRequest(BaseModel):
    grupo_id: UUID
    labirinto_id: int

@app.post("/generate-websocket/")
async def generate_websocket_link(payload: WebSocketRequest):
    grupo_id = payload.grupo_id
    labirinto_id = payload.labirinto_id

    db = next(get_db())
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
    labirinto = db.query(Labirinto).filter(Labirinto.id == labirinto_id).first()

    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    if not labirinto:
        raise HTTPException(status_code=404, detail="Labirinto não encontrado")

    ws_url = f"ws://localhost:8000/ws/{grupo_id}/{labirinto_id}"

    # Save WebSocket session in the database
    sessao_ws = SessaoWebSocket(grupo_id=str(grupo_id), conexao=ws_url)
    db.add(sessao_ws)
    db.commit()

    return {"websocket_url": ws_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
