"""
Servidor Web Local Connect6 Arena (100% Python - SIN DOCKER)
===========================================================
Este script levanta:
1. Un Servidor Web en http://localhost:8080 con la interfaz gráfica completa del tablero (HTML5 + Canvas/CSS).
2. Un Servidor gRPC en localhost:50051 al que se conecta tu agente_connect6.py.

Permite jugar Humano vs IA (haciendo clic en la página web) e IA vs IA directamente desde tu navegador sin instalar Docker.
"""

import sys
import time
import json
import random
import threading
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from concurrent import futures
import grpc

import connect6_pb2
import connect6_pb2_grpc

# Estado Global del Juego
class EstadoJuegoGlobal:
    def __init__(self):
        self.tablero = np.zeros((19, 19), dtype=int)
        self.modo = "humano_vs_ia" # "humano_vs_ia" o "ia_vs_ia"
        self.turno_actual = 1  # 1: Negras (IA), 2: Blancas (Humano/IA2)
        self.fichas_pendientes = 1
        self.historial_fichas_turno = []
        self.ganador = 0
        self.mensaje = "Esperando conexión de tu Agente IA en localhost:50051..."
        self.equipo_ia = "Buscando Agente..."
        self.agent_connected = False
        self.lock = threading.Lock()

    def reiniciar(self, modo="humano_vs_ia"):
        with self.lock:
            self.tablero = np.zeros((19, 19), dtype=int)
            self.modo = modo
            self.turno_actual = 1
            self.fichas_pendientes = 1
            self.historial_fichas_turno = []
            self.ganador = 0
            self.mensaje = f"Nueva partida iniciada ({modo}). Turno de Negras (1 ficha)."

    def verificar_ganador(self, jugador):
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

JUEGO = EstadoJuegoGlobal()

# ==========================================
# 1. SERVIDOR gRPC PARA CONECTAR agente_connect6.py
# ==========================================
class ServidorGRPC(connect6_pb2_grpc.GameServerServicer):
    def Play(self, request_iterator, context):
        primer_mensaje = next(request_iterator)
        if primer_mensaje.HasField("register_team"):
            JUEGO.equipo_ia = primer_mensaje.register_team
            JUEGO.agent_connected = True
            JUEGO.mensaje = f"¡Agente '{JUEGO.equipo_ia}' conectado exitosamente!"
            print(f"[gRPC] Agente registrado: {JUEGO.equipo_ia}")

        color_agente = connect6_pb2.BLACK

        while True:
            # Esperar a que sea el turno de la IA
            while JUEGO.turno_actual != 1 and JUEGO.ganador == 0:
                time.sleep(0.1)

            if JUEGO.ganador != 0:
                yield self._construir_estado_final()
                break

            # Solicitud de movimiento a la IA
            stones_req = JUEGO.fichas_pendientes
            JUEGO.mensaje = f"IA ({JUEGO.equipo_ia}) pensando jugada ({stones_req} ficha/s)..."
            yield self._construir_estado(es_mi_turno=True, color=color_agente, stones_required=stones_req)

            try:
                accion = next(request_iterator)
                if accion.HasField("move"):
                    with JUEGO.lock:
                        for pt in accion.move.stones:
                            if 0 <= pt.x < 19 and 0 <= pt.y < 19 and JUEGO.tablero[pt.y, pt.x] == 0:
                                JUEGO.tablero[pt.y, pt.x] = 1

                        if JUEGO.verificar_ganador(1):
                            JUEGO.ganador = 1
                            JUEGO.mensaje = f"🏆 ¡¡GANÓ LA IA ({JUEGO.equipo_ia}) con 6 en línea!!"
                        else:
                            # Cambiar turno al Humano / Oponente (2 fichas)
                            JUEGO.turno_actual = 2
                            JUEGO.fichas_pendientes = 2
                            JUEGO.historial_fichas_turno = []
                            JUEGO.mensaje = "Turno del Jugador Blanco. Haz clic en el tablero para colocar 2 fichas."

                            # Si el modo es IA vs IA, jugar respuesta automatica del rival
                            if JUEGO.modo == "ia_vs_ia":
                                self._jugar_rival_ia()
            except StopIteration:
                break

    def _jugar_rival_ia(self):
        time.sleep(0.5)
        vacio = np.where(JUEGO.tablero == 0)
        if len(vacio[0]) >= 2:
            indices = random.sample(range(len(vacio[0])), 2)
            for idx in indices:
                r, c = vacio[0][idx], vacio[1][idx]
                JUEGO.tablero[r, c] = 2

            if JUEGO.verificar_ganador(2):
                JUEGO.ganador = 2
                JUEGO.mensaje = "❌ ¡Ganó el Agente Rival (Blancas)!"
            else:
                JUEGO.turno_actual = 1
                JUEGO.fichas_pendientes = 2

    def _construir_estado(self, es_mi_turno, color, stones_required):
        pb_board = []
        for r in range(19):
            row = connect6_pb2.Row()
            for c in range(19):
                val = int(JUEGO.tablero[r, c])
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

    def _construir_estado_final(self):
        res = connect6_pb2.BLACK_WIN if JUEGO.ganador == 1 else connect6_pb2.WHITE_WIN
        return connect6_pb2.GameState(
            status=connect6_pb2.GameState.FINISHED,
            is_my_turn=False,
            result=res
        )

# ==========================================
# 2. SERVIDOR WEB HTML5/JS (http://localhost:8080)
# ==========================================
HTML_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect6 Arena - Interfaz Web Local</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); color: #fff; text-align: center; margin: 0; padding: 20px; min-height: 100vh; }
        h1 { margin-top: 0; font-size: 2.5em; background: -webkit-linear-gradient(#4facfe, #00f2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #ccc; font-size: 16px; margin-bottom: 20px; }
        .controls { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px); padding: 15px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1); display: inline-block; margin-bottom: 15px; }
        button { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: white; padding: 10px 20px; font-size: 16px; border-radius: 10px; cursor: pointer; margin: 5px; transition: all 0.3s ease; }
        button:hover { background: rgba(255, 255, 255, 0.2); transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        #status { font-size: 18px; font-weight: bold; background: rgba(0, 0, 0, 0.3); padding: 12px; border-radius: 10px; max-width: 600px; margin: 15px auto; color: #4facfe; border: 1px solid rgba(255, 255, 255, 0.1); }
        #board-container { display: inline-block; background: #dcb35c; padding: 20px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.5); margin-top: 10px; border: 3px solid #8b5a2b; }
        canvas { cursor: pointer; display: block; }
    </style>
</head>
<body>
    <h1>🎮 Connect6 Arena</h1>
    <div class="subtitle">Plataforma Web Local (Servidor sin Docker)</div>
    
    <div class="controls">
        <button style="background: #2c3e50; margin-bottom: 10px;" onclick="volverAlMenu()">⬅️ Volver al Menú Principal</button><br>
        <button onclick="reiniciarPartida('humano_vs_ia')">👤 Humano vs IA</button>
        <button onclick="reiniciarPartida('ia_vs_ia')">🤖 IA vs IA (Simulación)</button>
    </div>

    <div id="status">Cargando estado...</div>

    <div id="board-container">
        <canvas id="boardCanvas" width="570" height="570"></canvas>
    </div>

    <script>
        const canvas = document.getElementById('boardCanvas');
        const ctx = canvas.getContext('2d');
        const GRID_SIZE = 19;
        const CELL_SIZE = 30;
        const PADDING = 15;

        let gameState = { tablero: [], turno_actual: 1, mensaje: "", ganador: 0 };

        async function volverAlMenu() {
            try {
                await fetch('/api/shutdown', { method: 'POST', body: '{}' });
            } catch(e) {}
            window.location.href = 'http://localhost:5000';
        }

        function drawBoard() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Dibujar Líneas de la Cuadrícula
            ctx.strokeStyle = '#333';
            ctx.lineWidth = 1.5;
            for (let i = 0; i < GRID_SIZE; i++) {
                // Horizontales
                ctx.beginPath();
                ctx.moveTo(PADDING, PADDING + i * CELL_SIZE);
                ctx.lineTo(PADDING + (GRID_SIZE - 1) * CELL_SIZE, PADDING + i * CELL_SIZE);
                ctx.stroke();

                // Verticales
                ctx.beginPath();
                ctx.moveTo(PADDING + i * CELL_SIZE, PADDING);
                ctx.lineTo(PADDING + i * CELL_SIZE, PADDING + (GRID_SIZE - 1) * CELL_SIZE);
                ctx.stroke();
            }

            // Dibujar Puntos Estelares (Star Points)
            const starPoints = [3, 9, 15];
            ctx.fillStyle = '#000';
            for (let r of starPoints) {
                for (let c of starPoints) {
                    ctx.beginPath();
                    ctx.arc(PADDING + c * CELL_SIZE, PADDING + r * CELL_SIZE, 4, 0, 2 * Math.PI);
                    ctx.fill();
                }
            }

            // Dibujar Fichas
            if (gameState.tablero && gameState.tablero.length > 0) {
                for (let r = 0; r < GRID_SIZE; r++) {
                    for (let c = 0; c < GRID_SIZE; c++) {
                        let val = gameState.tablero[r][c];
                        if (val !== 0) {
                            let x = PADDING + c * CELL_SIZE;
                            let y = PADDING + r * CELL_SIZE;

                            ctx.beginPath();
                            ctx.arc(x, y, 13, 0, 2 * Math.PI);
                            if (val === 1) {
                                // Ficha Negra (IA)
                                ctx.fillStyle = '#111';
                                ctx.fill();
                                ctx.strokeStyle = '#555';
                                ctx.lineWidth = 1;
                                ctx.stroke();
                            } else if (val === 2) {
                                // Ficha Blanca (Humano)
                                ctx.fillStyle = '#fff';
                                ctx.fill();
                                ctx.strokeStyle = '#aaa';
                                ctx.lineWidth = 1;
                                ctx.stroke();
                            }
                        }
                    }
                }
            }
        }

        async function fetchState() {
            try {
                let res = await fetch('/api/state');
                gameState = await res.json();
                document.getElementById('status').innerText = gameState.mensaje;
                drawBoard();
            } catch (e) {
                console.error(e);
            }
        }

        canvas.addEventListener('click', async (e) => {
            if (gameState.turno_actual !== 2 || gameState.ganador !== 0) return;

            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const col = Math.round((x - PADDING) / CELL_SIZE);
            const row = Math.round((y - PADDING) / CELL_SIZE);

            if (col >= 0 && col < GRID_SIZE && row >= 0 && row < GRID_SIZE) {
                let res = await fetch('/api/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ r: row, c: col })
                });
                let data = await res.json();
                if (data.status === 'ok') {
                    fetchState();
                } else {
                    alert(data.message);
                }
            }
        });

        async function reiniciarPartida(modo) {
            await fetch('/api/reset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ modo: modo })
            });
            fetchState();
        }

        setInterval(fetchState, 600);
        drawBoard();
    </script>
</body>
</html>
"""

class WebRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Silenciar logs HTTP ruidosos

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            # Forzar no-cache para evitar que el navegador guarde la UI del profe
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif parsed.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with JUEGO.lock:
                data = {
                    "tablero": JUEGO.tablero.tolist(),
                    "turno_actual": JUEGO.turno_actual,
                    "fichas_pendientes": JUEGO.fichas_pendientes,
                    "mensaje": JUEGO.mensaje,
                    "ganador": JUEGO.ganador,
                    "equipo_ia": JUEGO.equipo_ia
                }
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        req_data = json.loads(body.decode('utf-8'))

        if parsed.path == '/api/move':
            r, c = req_data.get('r'), req_data.get('c')
            with JUEGO.lock:
                if JUEGO.turno_actual == 2 and JUEGO.tablero[r, c] == 0:
                    JUEGO.tablero[r, c] = 2
                    JUEGO.historial_fichas_turno.append((r, c))
                    JUEGO.fichas_pendientes -= 1

                    if JUEGO.verificar_ganador(2):
                        JUEGO.ganador = 2
                        JUEGO.mensaje = "🎉 ¡¡FELICIDADES! ¡HAS GANADO AL AGENTE IA!!"
                    elif JUEGO.fichas_pendientes == 0:
                        JUEGO.turno_actual = 1
                        JUEGO.fichas_pendientes = 2
                        JUEGO.mensaje = f"IA ({JUEGO.equipo_ia}) pensando su jugada..."
                    else:
                        JUEGO.mensaje = f"Ficha colocada. Te falta colocar 1 ficha más."

                    res = {"status": "ok"}
                else:
                    res = {"status": "error", "message": "Casilla ocupada o no es tu turno"}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif parsed.path == '/api/reset':
            modo = req_data.get('modo', 'humano_vs_ia')
            JUEGO.reiniciar(modo)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))

        elif parsed.path == '/api/shutdown':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            import threading
            threading.Thread(target=self.server.shutdown).start()

def iniciar_servidores():
    import subprocess
    import sys
    
    # 0. Levantar la IA en segundo plano
    print("[IA] Levantando agente inteligente en segundo plano...")
    agente_process = subprocess.Popen([sys.executable, "agente_connect6.py"])

    # 1. Iniciar gRPC Server
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    connect6_pb2_grpc.add_GameServerServicer_to_server(ServidorGRPC(), grpc_server)
    grpc_server.add_insecure_port('0.0.0.0:50051')
    grpc_server.start()

    # 2. Iniciar Web HTTP Server
    web_server = HTTPServer(('0.0.0.0', 8080), WebRequestHandler)
    
    print("========================================================================")
    print("🌐 SERVIDOR WEB LOCAL CONNECT6 ARENA (100% PYTHON - SIN DOCKER)")
    print("========================================================================")
    print("👉 Abre tu navegador en: http://localhost:8080")
    print("========================================================================")

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Apagando servidores...")
    finally:
        web_server.server_close()
        grpc_server.stop(0)
        agente_process.terminate()

if __name__ == '__main__':
    iniciar_servidores()
