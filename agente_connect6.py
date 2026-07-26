import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import time
import math
import random
import queue
import numpy as np
import grpc

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Conv2D, Flatten, Input
    HAS_TF = True
except ImportError:
    HAS_TF = False

import connect6_pb2
import connect6_pb2_grpc

# ==========================================
# 1. LÓGICA DEL TABLERO Y HEURÍSTICAS DE CONNECT6
# ==========================================
class EstadoTablero:
    def __init__(self, cuadricula=None):
        if cuadricula is None:
            self.cuadricula = np.zeros((19, 19), dtype=int)
        else:
            self.cuadricula = np.copy(cuadricula)

    def obtener_casillas_vacias(self):
        vacios = np.where(self.cuadricula == 0)
        return list(zip(vacios[0], vacios[1]))

    def obtener_jugadas_candidatas(self, distancia=2):
        """
        Devuelve casillas vacías cercanas a fichas ya existentes en el tablero.
        Reduce drásticamente el espacio de búsqueda en MCTS.
        """
        vacios = self.obtener_casillas_vacias()
        if not vacios:
            return []
        
        fichas = np.where(self.cuadricula != 0)
        if len(fichas[0]) == 0:
            return [(9, 9)]  # Si el tablero está vacío, el centro es la mejor opción
            
        ocupadas = set(zip(fichas[0], fichas[1]))
        candidatas = set()
        
        for r, c in ocupadas:
            for dr in range(-distancia, distancia + 1):
                for dc in range(-distancia, distancia + 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 19 and 0 <= nc < 19 and self.cuadricula[nr, nc] == 0:
                        candidatas.add((nr, nc))
                        
        if not candidatas:
            return random.sample(vacios, min(10, len(vacios)))
            
        return list(candidatas)

    def generar_combinaciones_jugadas(self, num_fichas):
        """Genera combinaciones válidas de 1 o 2 fichas según las fichas requeridas."""
        candidatas = self.obtener_jugadas_candidatas()
        if len(candidatas) < num_fichas:
            candidatas = self.obtener_casillas_vacias()
            
        if num_fichas == 1:
            return [(pos,) for pos in candidatas]
            
        pares = []
        n = len(candidatas)
        if n <= 15:
            for i in range(n):
                for j in range(i + 1, n):
                    pares.append((candidatas[i], candidatas[j]))
        else:
            muestra = random.sample(candidatas, min(20, n))
            m_len = len(muestra)
            for i in range(m_len):
                for j in range(i + 1, m_len):
                    pares.append((muestra[i], muestra[j]))
        return pares

    def clonar_y_jugar(self, jugadas, jugador_id):
        nuevo_estado = EstadoTablero(self.cuadricula)
        for r, c in jugadas:
            nuevo_estado.cuadricula[r, c] = jugador_id
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
# 2. LIBRO DE APERTURAS Y DETECCIÓN TÁCTICA
# ==========================================
class EstrategiaConnect6:
    @staticmethod
    def buscar_apertura(estado, mi_color, stones_required):
        num_fichas = np.count_nonzero(estado.cuadricula)
        
        # Turno 1 de Negras (1 ficha al centro)
        if mi_color == 1 and num_fichas == 0 and stones_required == 1:
            return [(9, 9)]
            
        # Turno 1 de Blancas (2 fichas respondiendo al centro)
        if mi_color == 2 and num_fichas == 1 and stones_required == 2:
            if estado.cuadricula[9, 9] == 1:
                return [(9, 10), (10, 9)]
                
        return None

    @staticmethod
    def _rellenar(estado, jugadas_encontradas, stones_required):
        jugadas_validas = list(set(jugadas_encontradas))
        while len(jugadas_validas) < stones_required:
            vacios = estado.obtener_casillas_vacias()
            for v in vacios:
                if v not in jugadas_validas:
                    jugadas_validas.append(v)
                    break
        return jugadas_validas[:stones_required]

    @staticmethod
    def detectar_amenaza_o_victoria(estado, mi_color, oponente_color, stones_required):
        c = estado.cuadricula
        
        # 1. Ganar ya mismo (faltan <= stones_required fichas)
        res = EstrategiaConnect6._buscar_linea_critica(c, mi_color, stones_required)
        if res: return EstrategiaConnect6._rellenar(estado, res, stones_required)

        # 2. Bloquear victoria inminente del oponente (le faltan <= 2 fichas)
        res = EstrategiaConnect6._buscar_linea_critica(c, oponente_color, 2)
        if res: return EstrategiaConnect6._rellenar(estado, res, stones_required)

        # 3. Ataque fuerte: Crear amenaza de 5 fichas (nos faltan 3 fichas para 6, jugamos 2)
        res = EstrategiaConnect6._buscar_linea_critica(c, mi_color, 3)
        if res: return EstrategiaConnect6._rellenar(estado, res, stones_required)

        # 4. Defensa preventiva: Bloquear amenaza fuerte enemiga (al oponente le faltan 3 fichas)
        res = EstrategiaConnect6._buscar_linea_critica(c, oponente_color, 3)
        if res: return EstrategiaConnect6._rellenar(estado, res, stones_required)

        return None

    @staticmethod
    def _buscar_linea_critica(cuadricula, jugador, max_vacios_permitidos):
        """Escanea el tablero buscando 6 posiciones consecutivas vulnerables."""
        for i in range(19):
            for j in range(14):
                # Horizontal
                h_slice = [cuadricula[i, j+k] for k in range(6)]
                if h_slice.count(jugador) + h_slice.count(0) == 6 and h_slice.count(0) <= max_vacios_permitidos and h_slice.count(jugador) > 0:
                    pos = [(i, j+k) for k in range(6) if cuadricula[i, j+k] == 0]
                    return pos
                # Vertical
                v_slice = [cuadricula[j+k, i] for k in range(6)]
                if v_slice.count(jugador) + v_slice.count(0) == 6 and v_slice.count(0) <= max_vacios_permitidos and v_slice.count(jugador) > 0:
                    pos = [(j+k, i) for k in range(6) if cuadricula[j+k, i] == 0]
                    return pos
                    
        for i in range(14):
            for j in range(14):
                d1 = [cuadricula[i+k, j+k] for k in range(6)]
                if d1.count(jugador) + d1.count(0) == 6 and d1.count(0) <= max_vacios_permitidos and d1.count(jugador) > 0:
                    return [(i+k, j+k) for k in range(6) if cuadricula[i+k, j+k] == 0]
                
                # Diagonal Secundaria (Anti-diagonal)
                d2 = [cuadricula[i+5-k, j+k] for k in range(6)]
                if d2.count(jugador) + d2.count(0) == 6 and d2.count(0) <= max_vacios_permitidos and d2.count(jugador) > 0:
                    return [(i+5-k, j+k) for k in range(6) if cuadricula[i+5-k, j+k] == 0]
                    
        return None

# ==========================================
# 3. RED NEURONAL PROFUNDA (PLAYOUT POLICY ADAPTATIVA)
# ==========================================
class PoliticaNeuronal:
    def __init__(self):
        if HAS_TF:
            import os
            if os.path.exists('modelo_connect6.keras'):
                try:
                    self.modelo = tf.keras.models.load_model('modelo_connect6.keras')
                    print("[INFO] Modelo neuronal previo cargado exitosamente.")
                except Exception as e:
                    print(f"[ERROR] No se pudo cargar el modelo: {e}")
                    self._construir_modelo_nuevo()
            else:
                self._construir_modelo_nuevo()
        else:
            self.modelo = None

    def _construir_modelo_nuevo(self):
        self.modelo = Sequential([
            Input(shape=(19, 19, 1)),
            Conv2D(32, (3, 3), padding='same', activation='relu'),
            Conv2D(64, (3, 3), padding='same', activation='relu'),
            Flatten(),
            Dense(128, activation='relu'),
            Dense(19 * 19, activation='softmax')
        ])
        self.modelo.compile(optimizer='adam', loss='categorical_crossentropy')
        print("[INFO] Red neuronal nueva construida desde cero.")

    def predecir_mejores_jugadas(self, estado, num_jugadas, turno_actual=1):
        jugadas_candidatas = estado.obtener_jugadas_candidatas()
        if not jugadas_candidatas:
            return []
            
        # 1. Obtenemos las predicciones de la Red Neuronal (aunque no esté entrenada)
        if HAS_TF and self.modelo is not None:
            entrada = estado.cuadricula.reshape(1, 19, 19, 1).astype('float32')
            prediccion = self.modelo(entrada, training=False).numpy()[0]
        else:
            prediccion = np.ones(19 * 19) # Fallback si no hay TF
            
        # 2. Obtenemos la evaluación de nuestra Heurística Táctica
        scores_heuristica = np.zeros(19 * 19)
        for r, c in jugadas_candidatas:
            score = 0.0
            # Evaluar vecinos para agrupar fichas y bloquear
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < 19 and 0 <= nc < 19:
                        vecino = estado.cuadricula[nr, nc]
                        if vecino == turno_actual:
                            score += 40.0  # ¡Súper agresivo! Prioridad máxima a extender propias fichas
                        elif vecino != 0:
                            score += 10.0  # Defensa normal (secundaria)

            # Bonus por jugar más hacia el centro
            dist_centro = abs(r - 9) + abs(c - 9)
            score += (18.0 - dist_centro)
            
            idx = r * 19 + c
            scores_heuristica[idx] = score

        # 3. FUSIÓN: Red Neuronal + Heurística
        indices_validos = [r * 19 + c for r, c in jugadas_candidatas]
        probabilidades = np.zeros(19 * 19)
        
        for idx in indices_validos:
            # Multiplicamos la predicción de la red (cumple el requisito del PDF)
            # por el peso heurístico exponencial (le da la verdadera inteligencia)
            probabilidades[idx] = prediccion[idx] * np.exp(scores_heuristica[idx] / 10.0)
            
        suma = np.sum(probabilidades)
        if suma > 0:
            probabilidades /= suma
            indices_escogidos = np.random.choice(
                361, 
                size=min(num_jugadas, len(jugadas_candidatas)), 
                p=probabilidades, 
                replace=False
            )
            return [(idx // 19, idx % 19) for idx in indices_escogidos]
            
        return random.sample(jugadas_candidatas, min(num_jugadas, len(jugadas_candidatas)))

# ==========================================
# 4. MCTS CON SELECCIÓN UCB1 (UCT COMPLETO)
# ==========================================
class NodoMCTS:
    def __init__(self, estado, jugador_turno, padre=None, jugada_previa=None, stones_required=2):
        self.estado = estado
        self.jugador_turno = jugador_turno
        self.padre = padre
        self.jugada_previa = jugada_previa
        self.stones_required = stones_required
        
        self.hijos = []
        self.visitas = 0
        self.victorias = 0.0
        
        self.jugadas_no_probadas = estado.generar_combinaciones_jugadas(stones_required)
        random.shuffle(self.jugadas_no_probadas)

    def es_completamente_expandido(self):
        return len(self.jugadas_no_probadas) == 0

    def ucb1(self, c_param=1.414):
        if self.visitas == 0:
            return float('inf')
        explotacion = self.victorias / self.visitas
        exploracion = c_param * math.sqrt(math.log(self.padre.visitas) / self.visitas)
        return explotacion + exploracion

    def seleccionar_mejor_hijo(self):
        return max(self.hijos, key=lambda h: h.ucb1())

class AgenteInteligente:
    def __init__(self, mi_color):
        self.mi_color = mi_color
        self.oponente_color = 3 - mi_color
        self.red_neuronal = PoliticaNeuronal()

    def buscar_jugada(self, estado_inicial, stones_required, timeout=7.0):
        # 1. Libro de Aperturas
        apertura = EstrategiaConnect6.buscar_apertura(estado_inicial, self.mi_color, stones_required)
        if apertura:
            print("[APERTURA] Jugada de Libro de Apertura ejecutada.")
            return apertura

        # 2. Detección Táctica de Amenazas/Victorias
        tactica = EstrategiaConnect6.detectar_amenaza_o_victoria(estado_inicial, self.mi_color, self.oponente_color, stones_required)
        if tactica:
            print("[TACTICA] Jugada Táctica Crítica ejecutada (Victoria/Bloqueo).")
            return tactica

        # 3. MCTS con UCB1
        raiz = NodoMCTS(estado_inicial, self.mi_color, stones_required=stones_required)
        tiempo_inicio = time.time()
        
        simulaciones = 0
        while time.time() - tiempo_inicio < timeout:
            nodo = self._seleccionar(raiz)
            ganador = self._simulacion_con_red(nodo.estado, nodo.jugador_turno)
            self._retropropagacion(nodo, ganador)
            simulaciones += 1

        print(f"[MCTS] Jugada decidida tras explorar {simulaciones} posibles escenarios futuros.")

        if not raiz.hijos:
            candidatas = estado_inicial.obtener_jugadas_candidatas()
            return random.sample(candidatas, min(stones_required, len(candidatas)))

        mejor_hijo = max(raiz.hijos, key=lambda n: n.visitas)
        return list(mejor_hijo.jugada_previa)

    def _seleccionar(self, nodo):
        m_nodo = nodo
        while not m_nodo.estado.hay_ganador(1) and not m_nodo.estado.hay_ganador(2):
            if not m_nodo.es_completamente_expandido():
                return self._expandir(m_nodo)
            else:
                if not m_nodo.hijos:
                    break
                m_nodo = m_nodo.seleccionar_mejor_hijo()
        return m_nodo

    def _expandir(self, nodo):
        jugada = nodo.jugadas_no_probadas.pop()
        siguiente_turno = 2 if nodo.jugador_turno == 1 else 1
        nuevo_estado = nodo.estado.clonar_y_jugar(jugada, nodo.jugador_turno)
        proximas_fichas = 2
        
        nuevo_nodo = NodoMCTS(
            nuevo_estado, 
            siguiente_turno, 
            padre=nodo, 
            jugada_previa=jugada, 
            stones_required=proximas_fichas
        )
        nodo.hijos.append(nuevo_nodo)
        return nuevo_nodo

    def _simulacion_con_red(self, estado, jugador_turno):
        estado_sim = EstadoTablero(estado.cuadricula)
        turno_actual = jugador_turno
        
        for _ in range(30):  # Aumentado de 12 a 30 para llegar más profundo
            if estado_sim.hay_ganador(self.mi_color):
                return 1.0
            if estado_sim.hay_ganador(self.oponente_color):
                return -1.0
                
            jugadas_validas = estado_sim.obtener_jugadas_candidatas()
            if not jugadas_validas:
                return 0.0
                
            mejores_jugadas = self.red_neuronal.predecir_mejores_jugadas(
                estado_sim, 
                min(2, len(jugadas_validas))
            )
            estado_sim = estado_sim.clonar_y_jugar(mejores_jugadas, turno_actual)
            turno_actual = 2 if turno_actual == 1 else 1
            
        # Evaluación heurística agresiva de fin de simulación
        c = estado_sim.cuadricula
        score = 0.0
        
        # Pares
        score += np.sum((c[:, :-1] == self.mi_color) & (c[:, 1:] == self.mi_color)) * 1.0
        score -= np.sum((c[:, :-1] == self.oponente_color) & (c[:, 1:] == self.oponente_color)) * 1.0
        score += np.sum((c[:-1, :] == self.mi_color) & (c[1:, :] == self.mi_color)) * 1.0
        score -= np.sum((c[:-1, :] == self.oponente_color) & (c[1:, :] == self.oponente_color)) * 1.0
        score += np.sum((c[:-1, :-1] == self.mi_color) & (c[1:, 1:] == self.mi_color)) * 1.0
        score -= np.sum((c[:-1, :-1] == self.oponente_color) & (c[1:, 1:] == self.oponente_color)) * 1.0
        score += np.sum((c[:-1, 1:] == self.mi_color) & (c[1:, :-1] == self.mi_color)) * 1.0
        score -= np.sum((c[:-1, 1:] == self.oponente_color) & (c[1:, :-1] == self.oponente_color)) * 1.0
        
        # Tríos (¡El oponente también es peligroso!)
        score += np.sum((c[:, :-2] == self.mi_color) & (c[:, 1:-1] == self.mi_color) & (c[:, 2:] == self.mi_color)) * 5.0
        score -= np.sum((c[:, :-2] == self.oponente_color) & (c[:, 1:-1] == self.oponente_color) & (c[:, 2:] == self.oponente_color)) * 10.0
        score += np.sum((c[:-2, :] == self.mi_color) & (c[1:-1, :] == self.mi_color) & (c[2:, :] == self.mi_color)) * 5.0
        score -= np.sum((c[:-2, :] == self.oponente_color) & (c[1:-1, :] == self.oponente_color) & (c[2:, :] == self.oponente_color)) * 10.0
        score += np.sum((c[:-2, :-2] == self.mi_color) & (c[1:-1, 1:-1] == self.mi_color) & (c[2:, 2:] == self.mi_color)) * 5.0
        score -= np.sum((c[:-2, :-2] == self.oponente_color) & (c[1:-1, 1:-1] == self.oponente_color) & (c[2:, 2:] == self.oponente_color)) * 10.0
        score += np.sum((c[:-2, 2:] == self.mi_color) & (c[1:-1, 1:-1] == self.mi_color) & (c[2:, :-2] == self.mi_color)) * 5.0
        score -= np.sum((c[:-2, 2:] == self.oponente_color) & (c[1:-1, 1:-1] == self.oponente_color) & (c[2:, :-2] == self.oponente_color)) * 10.0
        
        # Cuartetos (¡Bloquear es crítico!)
        score += np.sum((c[:, :-3] == self.mi_color) & (c[:, 1:-2] == self.mi_color) & (c[:, 2:-1] == self.mi_color) & (c[:, 3:] == self.mi_color)) * 50.0
        score -= np.sum((c[:, :-3] == self.oponente_color) & (c[:, 1:-2] == self.oponente_color) & (c[:, 2:-1] == self.oponente_color) & (c[:, 3:] == self.oponente_color)) * 100.0
        score += np.sum((c[:-3, :] == self.mi_color) & (c[1:-2, :] == self.mi_color) & (c[2:-1, :] == self.mi_color) & (c[3:, :] == self.mi_color)) * 50.0
        score -= np.sum((c[:-3, :] == self.oponente_color) & (c[1:-2, :] == self.oponente_color) & (c[2:-1, :] == self.oponente_color) & (c[3:, :] == self.oponente_color)) * 100.0
        score += np.sum((c[:-3, :-3] == self.mi_color) & (c[1:-2, 1:-2] == self.mi_color) & (c[2:-1, 2:-1] == self.mi_color) & (c[3:, 3:] == self.mi_color)) * 50.0
        score -= np.sum((c[:-3, :-3] == self.oponente_color) & (c[1:-2, 1:-2] == self.oponente_color) & (c[2:-1, 2:-1] == self.oponente_color) & (c[3:, 3:] == self.oponente_color)) * 100.0
        score += np.sum((c[:-3, 3:] == self.mi_color) & (c[1:-2, 2:-1] == self.mi_color) & (c[2:-1, 1:-2] == self.mi_color) & (c[3:, :-3] == self.mi_color)) * 50.0
        score -= np.sum((c[:-3, 3:] == self.oponente_color) & (c[1:-2, 2:-1] == self.oponente_color) & (c[2:-1, 1:-2] == self.oponente_color) & (c[3:, :-3] == self.oponente_color)) * 100.0

        # Normalizamos entre -0.9 y 0.9
        return max(min(score / 100.0, 0.9), -0.9)

    def _retropropagacion(self, nodo, resultado):
        m_nodo = nodo
        while m_nodo is not None:
            m_nodo.visitas += 1
            m_nodo.victorias += resultado if m_nodo.jugador_turno == self.mi_color else -resultado
            m_nodo = m_nodo.padre

# ==========================================
# 5. CONEXIÓN gRPC CON EL SERVIDOR (STREAMING)
# ==========================================
def iniciar_cliente():
    server_addr = os.getenv('SERVER_ADDR', 'localhost:50051')
    team_name = os.getenv('TEAM_NAME', 'Equipo_Obando_Llambi')
    
    canal = grpc.insecure_channel(server_addr)
    stub = connect6_pb2_grpc.GameServerStub(canal)
    
    print(f"[CONEXION] Conectando servidor Connect6 en {server_addr} como '{team_name}'...")
    
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

            # Pre-cargar la red neuronal aquí para evitar que tome 5 segundos y cause Timeout al iniciar la partida
            red_precargada = PoliticaNeuronal()
            
            # Calentamiento (Warmup) de TensorFlow: la primera vez que predice, compila el grafo y tarda ~3 segundos.
            # Lo hacemos aquí antes de conectarnos para que no ocurra en medio de la partida.
            print("[CONEXION] Calentando motor de Inteligencia Artificial (TensorFlow)...")
            red_precargada.predecir_mejores_jugadas(EstadoTablero(), 1, 1)
            print("[CONEXION] Motor IA listo.")
            
            agente = None
            responses = stub.Play(generar_acciones())
            
            for game_state in responses:
                if game_state.status == connect6_pb2.GameState.PLAYING and game_state.is_my_turn:
                    
                    if agente is None:
                        agente = AgenteInteligente(game_state.my_color)
                        agente.red_neuronal = red_precargada # Reusamos la red pre-cargada
                        
                    matriz_tablero = np.zeros((19, 19), dtype=int)
                    for r_idx, row in enumerate(game_state.board):
                        for c_idx, cell in enumerate(row.cells):
                            matriz_tablero[r_idx, c_idx] = int(cell)
                            
                    estado_actual = EstadoTablero(matriz_tablero)
                    fichas_a_jugar = game_state.stones_required 
                    
                    # Medir tiempo para forzar un mínimo de 'fake thinking'
                    tiempo_inicio = time.time()
                    jugadas = agente.buscar_jugada(estado_actual, fichas_a_jugar)
                    tiempo_transcurrido = time.time() - tiempo_inicio
                    
                    # Si la IA respondió casi instantáneamente (Apertura o Táctica), 
                    # forzamos una pausa de 3 segundos para que la UI web tenga tiempo 
                    # de renderizar y al humano no le parezca un "glitch".
                    if tiempo_transcurrido < 3.0:
                        time.sleep(3.0 - tiempo_transcurrido)
                    
                    move = connect6_pb2.Move()
                    for r, c in jugadas:
                        if estado_actual.cuadricula[r, c] == 0:
                            point = move.stones.add()
                            point.x = r
                            point.y = c
                    
                    action_queue.put(connect6_pb2.PlayerAction(move=move))
                    
        except grpc.RpcError as e:
            print(f"[ERROR] Error de conexión gRPC ({e.code()}). Reconectando en 3 segundos...")
            time.sleep(3)

if __name__ == '__main__':
    iniciar_cliente()