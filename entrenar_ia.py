import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import numpy as np
import tensorflow as tf
from agente_connect6 import AgenteInteligente, EstadoTablero

def jugar_partida(agente1, agente2):
    estado = EstadoTablero()
    historial_estados_1 = []
    historial_jugadas_1 = []
    historial_estados_2 = []
    historial_jugadas_2 = []
    
    turno = 1
    fichas_jugadas = 0
    
    while True:
        stones_required = 1 if fichas_jugadas == 0 else 2
        agente_actual = agente1 if turno == 1 else agente2
        historial_estados = historial_estados_1 if turno == 1 else historial_estados_2
        historial_jugadas = historial_jugadas_1 if turno == 1 else historial_jugadas_2
        
        # MCTS rapido de 1 segundo para acelerar el entrenamiento
        jugadas = agente_actual.buscar_jugada(estado, stones_required, timeout=1.0)
        
        # Guardar el estado actual y la decisión tomada
        # Para redes convolucionales, la entrada es 19x19x1
        estado_input = estado.cuadricula.reshape(19, 19, 1).copy()
        
        # Registrar cada piedra individualmente en el historial
        for r, c in jugadas:
            historial_estados.append(estado_input)
            idx = r * 19 + c
            y_target = np.zeros(19 * 19)
            y_target[idx] = 1.0
            historial_jugadas.append(y_target)
            
        estado = estado.clonar_y_jugar(jugadas, turno)
        fichas_jugadas += stones_required
        
        if estado.hay_ganador(1):
            return 1, historial_estados_1, historial_jugadas_1
        if estado.hay_ganador(2):
            return 2, historial_estados_2, historial_jugadas_2
        if len(estado.obtener_casillas_vacias()) == 0:
            return 0, [], [] # Empate
            
        turno = 2 if turno == 1 else 1

def entrenar(num_partidas=5):
    print("==================================================")
    print(" INICIANDO ENTRENAMIENTO POR REFUERZO (SELF-PLAY)")
    print("==================================================")
    
    agente = AgenteInteligente(1)
    
    X_train = []
    Y_train = []
    
    for i in range(num_partidas):
        print(f"\\n[Partida {i+1}/{num_partidas}] Simulando enfrentamiento IA vs IA...")
        ganador, estados, jugadas = jugar_partida(agente, agente)
        
        if ganador != 0:
            print(f" -> ¡Ganó el jugador {ganador}! Registrando sus jugadas maestras.")
            X_train.extend(estados)
            Y_train.extend(jugadas)
        else:
            print(" -> Empate. No se registra.")
            
    if len(X_train) > 0:
        print("\\n[Entrenamiento] Optimizando Red Neuronal Profunda...")
        X_train = np.array(X_train)
        Y_train = np.array(Y_train)
        
        agente.red_neuronal.modelo.fit(X_train, Y_train, epochs=5, batch_size=32)
        
        print("\\n[Guardado] Guardando cerebro entrenado en 'modelo_connect6.keras'...")
        agente.red_neuronal.modelo.save('modelo_connect6.keras')
        print("¡ENTRENAMIENTO COMPLETADO CON ÉXITO!")
    else:
        print("No hubo datos ganadores para entrenar.")

if __name__ == '__main__':
    import sys
    num_partidas = 3
    if len(sys.argv) > 1:
        try:
            num_partidas = int(sys.argv[1])
        except ValueError:
            pass
    entrenar(num_partidas=num_partidas)
