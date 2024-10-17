# Documentação de como usar a API para participar do desafio

#### > Atenção: caso apareceça um erro de UNIQUE ID da tabela, recomendo excluir a atual e gerar uma nova, guardando e reaproveitando os dados GrupoId e LabirintoId para gerar o websocket.


## Endpoints

### POST "/grupo"
#### Endpoint para cadastrar o grupo.
#### Body:
  ```JSON
  {
        "Nome" : "[Nome do Grupo]"
  }
  ```
#### Response:
  ```JSON
  {
        "Id" : "3F4365C5-77F1-405E-A6F2-66BE20521A40"
  }
  ```

### Create a new Labirinto
POST http://localhost:8000/labirinto
Content-Type: application/json
  ```JSON
  {
  "vertices": [
      {
          "id": 0,
          "labirintoId": 0,
          "adjacentes": [2, 3],
          "tipo": 1
      },
      {
          "id": 1,
          "labirintoId": 0,
          "adjacentes": [4],
          "tipo": 2
      },
      {
          "id": 2,
          "labirintoId": 0,
          "adjacentes": [0],
          "tipo": 0
      },
      {
          "id": 3,
          "labirintoId": 0,
          "adjacentes": [0, 4],
          "tipo": 0
      },
      {
          "id": 4,
          "labirintoId": 0,
          "adjacentes": [1, 3],
          "tipo": 0
      }
  ],
  "entrada": 0,
  "dificuldade": "Basiquinho e pequeno"
  }
  ```
#### Response:
  ```JSON
  {
      "labirinto_id" : 1
  }
  ```
### POST "/generate-websocket/"
#### Endpoint para começar o desafio para percorrer o labirinto.
#### Body:
  ```JSON
    {
      "grupo_id": "3F4365C5-77F1-405E-A6F2-66BE20521A40", 
      "labirinto_id": 1
    }
  ```
#### Response:
  ```JSON
    {
      "Conexao" : "ws://link.pro.handshake.inicial/"
    }
  ```

---

## Comportamento WebSocket
### Ao se conectar ao WebSocket, uma resposta será enviada pelo servidor com as informações do labirinto.
### Formato:
```
  Vértice atual: 0,
  Adjacentes: ['2', '3']
}
```
### O campo "Vertice atual" é o Id do vértice de entrada do labirinto.

## Comandos Linux
### Para executar enquanto a main está rodando o websocket:

``` bash
$ python3 teste_websocke.py
```

## Comandos do WebSocket
### "ir:[Id do vértice]"
#### Comando para se mover para um vértice vizinho.

#### Response:
```
  Vértice atual: 2,
  Adjacentes: ['0']
```
#### O campo "adjacentes" é um array com os Ids dos vértices vizinhos.
#### O campo "Vértice atual" é o Id do vértice atual.
