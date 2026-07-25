"""
Servidor Local Interactivo Connect6 (Soporta Humano vs IA e IA vs IA)
====================================================================
Este servidor local permite probar de manera independiente todas las modalidades 
de juego sin depender de Docker:
1. Humano vs IA (Juegas en la consola ingresando tus coordenadas contra tu Agente IA)
2. IA vs IA (Dos agentes gRPC se conectan y compiten entre sí)
"""

import sys
import time
import random
import numpy as np
from concurrent import futures
import grpc

import connect6_pb2
import connect6_pb2_grpc

class ServidorConnect6Interactivo(connect6_pb2_grpc.GameServerServicer):
    def __init__(self, modo_juego=1):
        self.tablero = np.zeros((19, 19), dtype=int)
        self.modo_juego = modo_juego  # 1: Humano vs IA, 2: IA vs IA
        self.agentes_conectados = []

    def Play(self, request_iterator, context):
        primer_mensaje = next(request_iterator)
        equipo = "Agente_Desconocido"
        if primer_mensaje.HasField("register_team"):
            equipo = primer_mensaje.register_team

        print(f"\n[SERVIDO] AGENTE CONECTADO: '{equipo}'")

        if self.modo_juego == 1:
            # MODO HUMANO VS IA
            return self._jugar_humano_vs_ia(equipo, request_iterator)
        else:
            # MODO IA VS IA
            print(f"[SERVIDO] Registrado para torneo IA vs IA: '{equipo}'")
            return self._jugar_ia_vs_ia(equipo, request_iterator)

    def _jugar_humano_vs_ia(self, equipo_ia, request_iterator):
        print("\n========================================================")
        print(f"🎮 PARTIDA: HUMANO (Blancas/Oponente) VS {equipo_ia} (Negras/IA)")
        print("========================================================\n")
        
        color_ia = connect6_pb2.BLACK
        
        # Turno 1 (IA coloca 1 ficha al centro)
        print(f"-> Turno 1 ({equipo_ia}): Esperando jugada inicial de 1 ficha...")
        yield self._construir_estado(es_mi_turno=True, color=color_ia, stones_required=1)

        accion = next(request_iterator)
        if accion.HasField("move"):
            for pt in accion.move.stones:
                self.tablero[pt.y, pt.x] = 1
                print(f"   [{equipo_ia} colocó Ficha Negra en: (Columna={pt.x}, Fila={pt.y})]")
            self._imprimir_tablero()

        turno = 2
        while True:
            if self._verificar_ganador(1):
                print(f"\n🏆 ¡¡GANÓ LA IA '{equipo_ia}'!! (6 en línea de fichas Negras)")
                yield self._construir_estado_final(connect6_pb2.BLACK_WIN)
                break

            # Turno del Humano (Ingresa 2 fichas por teclado)
            print(f"\n👉 TURNO {turno} (TU TURNO - HUMANO): Ingresa 2 fichas (Columna 0-18, Fila 0-18)")
            fichas_jugadas = 0
            while fichas_jugadas < 2:
                try:
                    linea = input(f"   Ingresa ficha {fichas_jugadas+1} en formato 'columna,fila' (ej: 9,10): ")
                    col, fila = map(int, linea.strip().split(','))
                    if 0 <= col < 19 and 0 <= fila < 19 and self.tablero[fila, col] == 0:
                        self.tablero[fila, col] = 2
                        fichas_jugadas += 1
                    else:
                        print("   ❌ Casilla ocupada o fuera de rango. Intenta de nuevo.")
                except Exception:
                    print("   ❌ Formato inválido. Usa 'columna,fila' (ej: 9,10).")

            self._imprimir_tablero()

            if self._verificar_ganador(2):
                print(f"\n🎉 ¡¡FELICIDADES! ¡HAS GANADO AL AGENTE IA!! (6 en línea de fichas Blancas)")
                yield self._construir_estado_final(connect6_pb2.WHITE_WIN)
                break

            # Turno de la IA (Solicita 2 fichas)
            print(f"-> Turno {turno + 1} ({equipo_ia}): Esperando jugada de 2 fichas...")
            yield self._construir_estado(es_mi_turno=True, color=color_ia, stones_required=2)

            try:
                accion = next(request_iterator)
                if accion.HasField("move"):
                    for pt in accion.move.stones:
                        self.tablero[pt.y, pt.x] = 1
                        print(f"   [{equipo_ia} colocó Ficha Negra en: (Columna={pt.x}, Fila={pt.y})]")
                    self._imprimir_tablero()
            except StopIteration:
                break

            turno += 2

    def _construir_estado(self, es_mi_turno, color, stones_required):
        pb_board = []
        for r in range(19):
            row = connect6_pb2.Row()
            for c in range(19):
                val = int(self.tablero[r, c])
                cell_color = connect6_pb2.UNKNOWN
                if val == 1: cell_color = connect6_pb2.BLACK
                elif val == 2: cell_color = connect6_pb2.WHITE
                row.cells.append(cell_color)
            pb_board.append(row)

        return connect6_pb2.GameState(
            status=connect6_pb2.GameState.PLAYING,
            is_my_turn=es_mi_turno,
            my_color=color,
            stones_required=stones_required,
            board=pb_board,
            result=connect6_pb2.ONGOING
        )

    def _construir_estado_final(self, resultado):
        return connect6_pb2.GameState(
            status=connect6_pb2.GameState.FINISHED,
            is_my_turn=False,
            result=resultado
        )

    def _verificar_ganador(self, jugador):
        c = self.tablero
        for i in range(19):
            for j in range(14):
                if np.all(c[i, j:j+6] == jugador): return True
                if np.all(c[j:j+6, i] == jugador): return True
        for i in range(14):
            for j in range(14):
                if np.all([c[i+k, j+k] == jugador for k in range(6)]): return True
                if np.all([c[i+5-k, j+k] == jugador for k in range(6)]): return True
        return False

    def _imprimir_tablero(self):
        simbolos = {0: '.', 1: 'X', 2: 'O'}
        print("   " + " ".join([f"{i:2d}" for i in range(19)]))
        for r in range(19):
            linea = f"{r:2d} " + "  ".join([simbolos[self.tablero[r, c]] for c in range(19)])
            print(linea)
        print("\n" + "-"*50)

def iniciar_servidor_interactivo():
    print("========================================================")
    print("  🎮 SERVIDOR LOCAL DE PRUEBAS CONNECT6 (SIN DOCKER)")
    print("========================================================")
    print("Selecciona el modo de juego:")
    print(" 1) Humano (Tú desde teclado) vs Agente IA")
    print(" 2) Agente IA vs Simulación de Agente Rival")
    
    try:
        opcion = input("Elige una opción (1 o 2) [Por defecto 1]: ").strip()
        modo = 2 if opcion == '2' else 1
    except Exception:
        modo = 1

    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    connect6_pb2_grpc.add_GameServerServicer_to_server(ServidorConnect6Interactivo(modo_juego=modo), servidor)
    servidor.add_insecure_port('0.0.0.0:50051')
    servidor.start()
    
    print("\n🟢 SERVIDOR ESCUCHANDO EN localhost:50051")
    print("Abre otra terminal y ejecuta: python agente_connect6.py\n")
    try:
        servidor.wait_for_termination()
    except KeyboardInterrupt:
        servidor.stop(0)

if __name__ == '__main__':
    iniciar_servidor_interactivo()
