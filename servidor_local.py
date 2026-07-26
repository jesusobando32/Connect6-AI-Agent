"""
Servidor Local Interactivo Connect6 (Soporta Humano vs IA e IA vs IA)
====================================================================
"""

import sys
import time
import random
import numpy as np
from concurrent import futures
import grpc
import subprocess

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
            return self._jugar_humano_vs_ia(equipo, request_iterator)
        else:
            print(f"[SERVIDO] Registrado para torneo IA vs IA: '{equipo}'")
            return self._jugar_ia_vs_ia(equipo, request_iterator)

    def _jugar_humano_vs_ia(self, equipo_ia, request_iterator):
        print("\n========================================================")
        print(f"🎮 PARTIDA: HUMANO (Blancas/Oponente) VS {equipo_ia} (Negras/IA)")
        print("========================================================\n")
        color_ia = connect6_pb2.BLACK
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

    def _jugar_ia_vs_ia(self, equipo_ia, request_iterator):
        print("\n========================================================")
        print(f"🎮 PARTIDA: BOT ALEATORIO (Blancas) VS {equipo_ia} (Negras/IA)")
        print("========================================================\n")
        color_ia = connect6_pb2.BLACK
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

            print(f"\n👉 TURNO {turno} (Bot Aleatorio): Pensando 2 fichas...")
            time.sleep(1) # Simular que piensa
            
            # Movimiento aleatorio
            vacios = np.where(self.tablero == 0)
            if len(vacios[0]) >= 2:
                indices = random.sample(range(len(vacios[0])), 2)
                for idx in indices:
                    fila, col = vacios[0][idx], vacios[1][idx]
                    self.tablero[fila, col] = 2
                    print(f"   [Bot Aleatorio colocó Ficha Blanca en: (Columna={col}, Fila={fila})]")
            
            self._imprimir_tablero()

            if self._verificar_ganador(2):
                print(f"\n🎉 ¡¡GANÓ EL BOT ALEATORIO!! (6 en línea de fichas Blancas)")
                yield self._construir_estado_final(connect6_pb2.WHITE_WIN)
                break

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

def iniciar_servidor():
    print("========================================================")
    print("🖥️ SERVIDOR LOCAL CONNECT6 (CONSOLA DE TEXTO)")
    print("========================================================")
    
    try:
        modo = input("\nSelecciona Modo (1: Humano vs IA, 2: IA vs IA) [1]: ").strip()
        modo_juego = 2 if modo == '2' else 1
        
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        connect6_pb2_grpc.add_GameServerServicer_to_server(ServidorConnect6Interactivo(modo_juego), server)
        server.add_insecure_port('[::]:50051')
        server.start()
        print(f"\n[INFO] Servidor gRPC iniciado en puerto 50051 (Modo: {modo_juego})")
        
        print("[IA] Levantando agente inteligente en segundo plano...")
        agente_process = subprocess.Popen([sys.executable, "agente_connect6.py"])
        
        print("[INFO] Esperando conexiones...")
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n[INFO] Apagando servidor local...")
    finally:
        if 'agente_process' in locals():
            agente_process.terminate()

if __name__ == '__main__':
    iniciar_servidor()
