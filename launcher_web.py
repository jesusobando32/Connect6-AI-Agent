import http.server
import socketserver
import subprocess
import sys
import json
import os

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect6 Arena - Launcher</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: #fff;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            margin-top: 0;
            font-size: 2.5em;
            background: -webkit-linear-gradient(#4facfe, #00f2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            color: #ccc;
            margin-bottom: 30px;
        }
        .mode-btn {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 25px;
            margin: 10px 0;
            border-radius: 10px;
            font-size: 1.2em;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s ease;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .mode-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .btn-train {
            background: linear-gradient(90deg, #ff9966, #ff5e62);
            border: none;
            font-weight: bold;
            margin-top: 20px;
        }
        .btn-train:hover {
            background: linear-gradient(90deg, #ff5e62, #ff9966);
        }
        #loading {
            display: none;
            margin-top: 20px;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.1);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border-left-color: #09f;
            animation: spin 1s linear infinite;
            margin: 0 auto;
            margin-bottom: 15px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>Connect6 Arena</h1>
        <p class="subtitle">Selecciona el modo de juego para iniciar los servidores</p>
        
        <div id="menu-buttons">
            <button class="mode-btn" onclick="launch(1)">🤖 IA vs IA (Clon)</button>
            <button class="mode-btn" onclick="launch(2)">🤖 IA vs Bot Aleatorio</button>
            <button class="mode-btn" onclick="launch(3)">👤 Humano vs IA</button>
            <button class="mode-btn btn-train" onclick="launch(4)">🧠 Entrenar IA (Self-Play)</button>

            <details style="margin-top: 30px; text-align: left; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 10px;">
                <summary style="cursor: pointer; color: #aaa; font-size: 0.9em; font-weight: bold; outline: none;">Otras Opciones (Antiguas / Respaldo)</summary>
                <div style="margin-top: 15px; display: flex; flex-direction: column; gap: 10px;">
                    <button class="mode-btn" style="font-size: 0.9em; padding: 10px; background: rgba(255,255,255,0.05);" onclick="launch(5)">🖥️ Servidor Consola Local (Texto)</button>
                    <button class="mode-btn" style="font-size: 0.9em; padding: 10px; background: rgba(255,255,255,0.05);" onclick="launch(6)">🌐 Servidor Web Local (Python)</button>
                </div>
            </details>
        </div>

        <div id="loading">
            <div class="spinner"></div>
            <p id="loading-text">Iniciando contenedores Docker... Por favor espera.</p>
        </div>
    </div>

    <script>
        function launch(mode) {
            if (mode === 4) {
                let games = prompt("¿Cuántas partidas deseas jugar para entrenar a la IA? (Recomendado: 10 a 50)\\nNota: Cada partida tarda unos ~2 segundos.", "10");
                if (games === null) {
                    return; // Cancelado
                }
                mode = mode + "&games=" + games;
            }

            document.getElementById('menu-buttons').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            
            if (mode.toString().startsWith("4")) {
                document.getElementById('loading-text').innerText = "Entrenando IA... Revisa la consola de PowerShell para ver el progreso. Esto tomará unos segundos.";
            } else if (mode.toString() === "5") {
                document.getElementById('loading-text').innerText = "Iniciando Servidor Local de Texto en una nueva consola... Revisa la ventana de comandos.";
            } else if (mode.toString() === "6") {
                document.getElementById('loading-text').innerText = "Iniciando Servidor Web Local (Python)...";
            } else {
                document.getElementById('loading-text').innerText = "Iniciando servidores Docker... Por favor espera.";
            }

            fetch('/launch?mode=' + mode)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        if (mode.toString() === "5") {
                            document.getElementById('loading-text').innerText = "¡Listo! La consola debería haber aparecido.";
                            setTimeout(() => { location.reload(); }, 3000);
                        } else if (mode.toString() === "6") {
                            document.getElementById('loading-text').innerText = "¡Listo! Redirigiendo a localhost:8080...";
                            setTimeout(() => { window.location.href = 'http://localhost:8080'; }, 1000);
                        } else if (!mode.toString().startsWith("4")) {
                            document.getElementById('loading-text').innerText = "¡Listo! Redirigiendo a la Arena...";
                            setTimeout(() => {
                                window.location.href = '/play';
                            }, 1000);
                        } else {
                            document.getElementById('loading-text').innerText = "¡Entrenamiento completado con éxito! El cerebro se ha guardado.";
                            setTimeout(() => {
                                document.getElementById('loading').style.display = 'none';
                                document.getElementById('menu-buttons').style.display = 'block';
                            }, 3000);
                        }
                    } else {
                        alert("Hubo un error al iniciar.");
                        window.location.reload();
                    }
                })
                .catch(err => {
                    alert("Error de conexión con el Launcher.");
                    window.location.reload();
                });
        }
    </script>
</body>
</html>
"""

PLAY_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connect6 Arena - Partida</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; overflow: hidden; }
        iframe { width: 100%; height: 100%; border: none; }
        .back-btn {
            position: absolute;
            top: 20px;
            left: 20px;
            background: linear-gradient(135deg, #0f2027, #203a43);
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-family: 'Segoe UI', sans-serif;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.2s, background 0.2s;
            z-index: 9999;
        }
        .back-btn:hover {
            transform: scale(1.05);
            background: linear-gradient(135deg, #203a43, #2c5364);
        }
    </style>
</head>
<body>
    <a href="/" class="back-btn">⬅ Volver al Menú Principal</a>
    <iframe src="http://localhost:8080"></iframe>
</body>
</html>
"""

class LauncherHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif self.path == '/play':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(PLAY_HTML.encode('utf-8'))
        elif self.path.startswith('/launch'):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            mode = qs.get('mode', ['1'])[0]
            games = qs.get('games', ['10'])[0]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                if mode == '1':
                    print("[Launcher] Deteniendo contenedores antiguos...")
                    subprocess.run(["docker", "compose", "down"], check=False)
                    print("[Launcher] Levantando Modo IA vs IA en segundo plano...")
                    subprocess.run(["docker", "compose", "up", "--build", "-d", "servidor", "mi-ia", "mi-ia-rival"], check=False)
                    subprocess.Popen(["docker", "compose", "logs", "-f"])
                elif mode == '2':
                    print("[Launcher] Deteniendo contenedores antiguos...")
                    subprocess.run(["docker", "compose", "down"], check=False)
                    print("[Launcher] Levantando Modo IA vs Bot Aleatorio en segundo plano...")
                    subprocess.run(["docker", "compose", "up", "--build", "-d", "servidor", "mi-ia", "ia-random"], check=False)
                    subprocess.Popen(["docker", "compose", "logs", "-f"])
                elif mode == '3':
                    print("[Launcher] Deteniendo contenedores antiguos...")
                    subprocess.run(["docker", "compose", "down"], check=False)
                    print("[Launcher] Levantando Modo IA vs Humano en segundo plano...")
                    subprocess.run(["docker", "compose", "up", "--build", "-d", "servidor", "mi-ia"], check=False)
                    subprocess.Popen(["docker", "compose", "logs", "-f"])
                elif mode == '4':
                    print(f"[Launcher] Entrenando IA ({games} partidas)...")
                    subprocess.run([sys.executable, "entrenar_ia.py", games], check=False)
                elif mode == '5':
                    print("[Launcher] Deteniendo contenedores para liberar recursos...")
                    subprocess.run(["docker", "compose", "down"], check=False)
                    print("[Launcher] Lanzando Servidor Local de Consola (Texto)...")
                    subprocess.Popen(["start", "cmd", "/c", sys.executable, "servidor_local.py"], shell=True)
                elif mode == '6':
                    print("[Launcher] Deteniendo contenedores (liberando puerto 8080)...")
                    subprocess.run(["docker", "compose", "down"], check=False)
                    print("[Launcher] Lanzando Servidor Web Local de Python (Independiente)...")
                    subprocess.Popen(["start", "cmd", "/c", sys.executable, "servidor_web_local.py"], shell=True)

                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    PORT = 5000
    # Permite reutilizar el puerto instantáneamente
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LauncherHandler) as httpd:
        print(f"==================================================")
        print(f"🚀 LAUNCHER WEB ACTIVO EN: http://localhost:{PORT}")
        print(f"==================================================")
        print(f"Abre el enlace de arriba en tu navegador (Chrome, Edge, etc.)")
        print(f"Presiona Ctrl+C en esta consola para cerrar el Launcher.")
        httpd.serve_forever()

if __name__ == '__main__':
    run_server()
