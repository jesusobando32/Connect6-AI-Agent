import os
import time
import math
import random
import queue
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv2D, Flatten
import grpc

import connect6_pb2
import connect6_pb2_grpc

# ==========================================
# 1. LÓGICA DEL TABLERO Y HEURÍSTICAS
# ==========================================
class EstadoTablero:
    def __init__(self, cuadricula=None):
        if cuadricula is None:
            self.cuadricula = np.zeros((19, 19), dtype=int)
        else:
            self.cuadricula = np.copy(cuadricula)

    def obtener_jugadas_validas(self):
        vacios = np.where(self.cuadricula == 0)
        return list(zip(vacios[0], vacios[1]))

    def clonar_y_jugar(self, jugadas, jugador_id):
        nuevo_estado = EstadoTablero(self.cuadricula)
        for j in jugadas:
            nuevo_estado.cuadricula[j[0], j[1]] = jugador_id
        return nuevo_estado

    def hay_ganador(self, jugador):
        c = self.cuadricula
        # Verificación horizontal y vertical
        for i in range(19):
            for j in range(14):
                if np.all(c[i, j:j+6] == jugador): return True
                if np.all(c[j:j+6, i] == jugador): return True
        # Verificación diagonal
        for i in range(14):
            for j in range(14):
                if np.all([c[i+k, j+k] == jugador for k in range(6)]): return True
                if np.all([c[i+5-k, j+k] == jugador for k in range(6)]): return True
        return False

# ==========================================
# 2. RED NEURONAL PROFUNDA (PLAYOUT POLICY)
# ==========================================
class PoliticaNeuronal:
    def __init__(self):
        self.modelo = Sequential([
            Conv2D(32, (3, 3), padding='same', activation='relu', input_shape=(19, 19, 1)),
            Conv2D(64, (3, 3), padding='same', activation='relu'),
            Flatten(),
            Dense(128, activation='relu'),
            Dense(19 * 19, activation='softmax')
        ])
        self.modelo.compile(optimizer='adam', loss='categorical_crossentropy')

    def predecir_mejores_jugadas(self, estado, num_jugadas):
        entrada = estado.cuadricula.reshape(1, 19, 19, 1).astype('float32')
        prediccion = self.modelo.predict(entrada, verbose=0)[0]
        
        jugadas_validas = estado.obtener_jugadas_validas()
        if not jugadas_validas:
            return []
            
        indices_validos = [f * 19 + c for f, c in jugadas_validas]
        probabilidades = np.zeros_like(prediccion)
        probabilidades[indices_validos] = prediccion[indices_validos]
        
        suma = np.sum(probabilidades)
        if suma == 0:
            return random.sample(jugadas_validas, min(num_jugadas, len(jugadas_validas)))
            
        probabilidades /= suma
        indices_escogidos = np.random.choice(361, size=min(num_jugadas, len(jugadas_validas)), p=probabilidades, replace=False)
        return [(idx // 19, idx % 19) for idx in indices_escogidos]

# ==========================================
# 3. MCTS CON POLÍTICA UCT (UCB1)
# ==========================================
class NodoMCTS:
    def __init__(self, estado, jugador_turno, padre=None, jugada_previa=None):
        self.estado = estado
        self.jugador_turno = jugador_turno
        self.padre = padre
        self.jugada_previa = jugada_previa
        self.hijos = []
        self.visitas = 0
        self.victorias = 0.0

    def ucb1(self, c_param=1.414):
        if self.visitas == 0:
            return float('inf')
        return (self.victorias / self.visitas) + c_param * math.sqrt(math.log(self.padre.visitas) / self.visitas)

class AgenteInteligente:
    def __init__(self, mi_color):
        self.mi_color = mi_color
        self.red_neuronal = PoliticaNeuronal()
        
    def buscar_jugada(self, estado_inicial, stones_required):
        raiz = NodoMCTS(estado_inicial, self.mi_color)
        tiempo_inicio = time.time()
        
        # Margen de seguridad estricto para no superar los 10 segundos del servidor
        while time.time() - tiempo_inicio < 9.5:
            nodo = self._seleccionar(raiz, stones_required)
            ganador = self._simulacion_con_red(nodo.estado, nodo.jugador_turno)
            self._retropropagacion(nodo, ganador)
            
        if not raiz.hijos:
            return random.sample(estado_inicial.obtener_jugadas_validas(), stones_required)
            
        mejor_hijo = max(raiz.hijos, key=lambda n: n.visitas)
        return mejor_hijo.jugada_previa

    def _seleccionar(self, nodo, stones_required):
        if nodo.visitas > 0 and not nodo.estado.hay_ganador(1) and not nodo.estado.hay_ganador(2):
            jugadas = nodo.estado.obtener_jugadas_validas()
            if jugadas:
                jugada = random.sample(jugadas, min(stones_required, len(jugadas)))
                nuevo_estado = nodo.estado.clonar_y_jugar(jugada, nodo.jugador_turno)
                siguiente_turno = 2 if nodo.jugador_turno == 1 else 1
                nuevo_nodo = NodoMCTS(nuevo_estado, siguiente_turno, padre=nodo, jugada_previa=jugada)
                nodo.hijos.append(nuevo_nodo)
                return nuevo_nodo
        return nodo

    def _simulacion_con_red(self, estado, jugador_turno):
        estado_sim = EstadoTablero(estado.cuadricula)
        turno_actual = jugador_turno
        
        for _ in range(20):
            if estado_sim.hay_ganador(self.mi_color): return 1
            if estado_sim.hay_ganador(3 - self.mi_color): return -1
            
            jugadas_validas = estado_sim.obtener_jugadas_validas()
            if not jugadas_validas: return 0
            
            mejores_jugadas = self.red_neuronal.predecir_mejores_jugadas(estado_sim, min(2, len(jugadas_validas)))
            estado_sim = estado_sim.clonar_y_jugar(mejores_jugadas, turno_actual)
            turno_actual = 2 if turno_actual == 1 else 1
            
        return 0

    def _retropropagacion(self, nodo, resultado):
        while nodo is not None:
            nodo.visitas += 1
            nodo.victorias += resultado
            nodo = nodo.padre
            resultado = -resultado

# ==========================================
# 4. CONEXIÓN gRPC CON EL SERVIDOR (STREAM)
# ==========================================
def iniciar_cliente():
    server_addr = os.getenv('SERVER_ADDR', 'localhost:50051')
    team_name = os.getenv('TEAM_NAME', 'Equipo_Obando_Llambi')
    
    canal = grpc.insecure_channel(server_addr)
    stub = connect6_pb2_grpc.GameServerStub(canal)
    
    print(f"Conectando a {server_addr} como {team_name}...")
    
    while True:
        try:
            action_queue = queue.Queue()
            action_queue.put(connect6_pb2.PlayerAction(register_team=team_name))
            
            def generar_acciones():
                while True:
                    try:
                        accion = action_queue.get(timeout=0.5)
                        if accion is None:
                            break
                        yield accion
                    except queue.Empty:
                        continue

            agente = None
            responses = stub.Play(generar_acciones())
            
            for game_state in responses:
                if game_state.status == connect6_pb2.GameState.PLAYING and game_state.is_my_turn:
                    
                    if agente is None:
                        agente = AgenteInteligente(game_state.my_color)
                        
                    matriz_tablero = np.zeros((19, 19), dtype=int)
                    for r_idx, row in enumerate(game_state.board):
                        for c_idx, cell in enumerate(row.cells):
                            matriz_tablero[r_idx, c_idx] = int(cell)
                            
                    estado_actual = EstadoTablero(matriz_tablero)
                    fichas_a_jugar = game_state.stones_required 
                    
                    jugadas = agente.buscar_jugada(estado_actual, fichas_a_jugar)
                    
                    move = connect6_pb2.Move()
                    for f, c in jugadas:
                        if estado_actual.cuadricula[f, c] == 0:
                            point = move.stones.add()
                            point.x = c
                            point.y = f
                    
                    action_queue.put(connect6_pb2.PlayerAction(move=move))
                    
        except grpc.RpcError as e:
            print(f"Error de conexión ({e.code()}). Reconectando en 3 segundos...")
            time.sleep(3)

if __name__ == '__main__':
    iniciar_cliente()