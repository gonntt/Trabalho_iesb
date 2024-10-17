import asyncio
import re

import websockets


# Função para parsear texto em resposta WebSocket
def parse_plain_text_response(response):
    vertex_id_match = re.search(r"Vértice atual: (\d+)", response)
    adjacentes_match = re.search(r"Adjacentes: \[([\'\d,\s]+)\]", response)

    if not vertex_id_match or not adjacentes_match:
        raise ValueError(f"Formato de resposta inválido: {response}")

    vertex_id = int(vertex_id_match.group(1))

    adjacentes_str = adjacentes_match.group(1).replace("'", "")
    adjacencia = [int(x.strip()) for x in adjacentes_str.split(',')]

    return vertex_id, adjacencia

# Função para se comunicar com WebSocket e obter dados de vértice
async def get_vertex_data(websocket, vertex_id):
    command = f"ir:{vertex_id}"
    print(command)
    await websocket.send(command)

    response = await websocket.recv()

    print(f"Resposta para o vértice {vertex_id}: {response}")

    try:
        current_vertex, adjacencia = parse_plain_text_response(response)
    except ValueError as e:
        print(f"Erro: {e}")
        return None, []

    return current_vertex, adjacencia


# Algoritmo DFS que envia comandos e explora o gráfico
async def dfs_websocket(websocket, vertex_id, visited):
    current_vertex, adjacencia = await get_vertex_data(websocket, vertex_id)
    visited.add(current_vertex)

    for neighbor in adjacencia:
        if neighbor not in visited:
            print(f"Indo para o vértice {neighbor}")
            await dfs_websocket(websocket, neighbor, visited)

    print(f"Voltando do vértice {current_vertex}")


async def main():
    start_vertex = 0
    visited = set()

    async with websockets.connect(
            # websocket gerado com o /generate-websocket/
            'ws://localhost:8000/ws/0d617f49-fa3b-40b3-bedd-ad708ca37031/1'
    ) as websocket:
        print("Começando percurso DFS...")
        await dfs_websocket(websocket, start_vertex, visited)
        print("Percurso DFS completo.")


asyncio.run(main())
