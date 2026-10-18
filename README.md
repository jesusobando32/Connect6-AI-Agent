# 🧠 NeuroHex: Connect6 AI Agent (MCTS + Deep Learning)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.14-orange.svg?style=flat-square&logo=tensorflow)
![gRPC](https://img.shields.io/badge/gRPC-Ready-green.svg?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED.svg?style=flat-square&logo=docker)

Un agente de Inteligencia Artificial para el juego **Connect6**, desarrollado en Python. Este proyecto combina la exploración profunda de algoritmos de búsqueda con la intuición de redes neuronales, logrando una toma de decisiones estratégica en tiempo real. 

El agente opera bajo una arquitectura cliente-servidor mediante **gRPC**, lo que le permite integrarse a múltiples entornos de simulación y plataformas (Docker/Python nativo).

---

## 🎓 Información Académica
* **Universidad:** Universidad Católica Andrés Bello (UCAB)
* **Materia:** Inteligencia Artificial: Aprendizaje Automático
* **Semestre:** Marzo - Julio 2026
* **Equipo:** Equipo_Obando_Llambi
* **Autores:** Jesús Obando, Sebastian Llambi

---

## ✨ Características Principales

* **🧠 Arquitectura de IA Híbrida**: Utiliza una combinación de **Monte Carlo Tree Search (MCTS)** con selección de política **UCB1** para la búsqueda de jugadas óptimas, guiado por una **Red Neuronal (Deep Learning)** pre-entrenada (*playout policy*) que evalúa las posiciones más prometedoras del tablero.
* **⚔️ Motor Táctico Heurístico**: Subsistema especializado en la detección inmediata de amenazas críticas. Escanea el tablero en 4 direcciones (horizontal, vertical, diagonales) para ejecutar victorias instantáneas (*Win-in-1*) o bloqueos obligatorios (*Block-in-1*), ahorrando inmenso poder de cómputo del árbol MCTS.
* **🌐 Launcher Web Integrado**: Interfaz gráfica nativa (sin dependencias externas complejas) para orquestar la IA, iniciar servidores de juego, y supervisar enfrentamientos (IA vs Humano, IA vs IA) desde tu navegador.
* **🔄 Entrenable mediante Self-Play**: Incluye scripts de entrenamiento local para que la Red Neuronal mejore iterativamente jugando contra sí misma sin intervención humana.
* **🔌 Comunicación Robusta (gRPC)**: El agente se conecta a servidores externos ("Connect6 Arena") mediante protocolos gRPC y Protobuf.

---

## 🏗️ Stack Tecnológico

| Componente | Tecnología Utilizada | Descripción |
| :--- | :--- | :--- |
| **Agente Core** | `Python 3.10+`, `NumPy` | Lógica central, evaluación de reglas y MCTS. |
| **Deep Learning** | `TensorFlow/Keras` | Predicción de movimientos (*policy network*). |
| **Comunicación** | `gRPC`, `Protobuf` | Pipeline cliente-servidor de baja latencia. |
| **Despliegue** | `Docker`, `Docker Compose` | Entorno de simulación estandarizado. |
| **Interfaz Web** | `http.server` (Nativo) | Orquestador de procesos y dashboard visual. |

---

## 🚀 Instalación y Uso (Desarrollo Local)

### 1. Requisitos Previos
* **Python 3.10** o superior instalado en tu sistema.
* (Opcional pero recomendado) Docker Desktop si deseas usar el servidor oficial del "Connect6 Arena".

### 2. Clonar y Preparar el Entorno
```bash
git clone https://github.com/jesusobando32/Connect6-AI-Agent.git
cd Connect6-AI-Agent

# Crear y activar entorno virtual (Evita conflictos con TensorFlow)
python -m venv venv

# En Windows:
venv\Scripts\activate
# En Mac/Linux:
# source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Compilación de gRPC
Es necesario compilar los *protobufs* para generar los archivos de comunicación si deseas correr el proyecto fuera de Docker.
```bash
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/connect6.proto
```

### 4. Iniciar el Launcher Web
```bash
python launcher_web.py
```
👉 Se abrirá automáticamente tu navegador en `http://localhost:5000`. Desde este panel podrás:
- **Iniciar una partida local** (Servidor Web Local 100% Python).
- **Iniciar el servidor Docker** (Connect6 Arena Original).
- **Ejecutar el pipeline de entrenamiento** (Self-Play).

*(Nota: La IA se ejecutará automáticamente en segundo plano cuando inicies una partida desde el Launcher).*

---

## ⚠️ Servidor Oficial (Arena) en Docker

Si decides levantar el servidor en Docker desde el menú web para jugar en la interfaz original (`http://localhost:8080`), ten en cuenta este **defecto del ejecutable original en Go**:
1. Al entrar a la configuración de la partida, **SIEMPRE debes seleccionar "Humano vs Humano"**.
2. No selecciones "Humano vs IA", ya que la interfaz web colapsará (bug del software original).
3. Al seleccionar "Humano vs Humano", nuestra IA desarrollada en Python se conectará de todas formas en segundo plano como el jugador negro y podrás competir contra ella con normalidad.

---

## 🆘 Servidores de Respaldo

En caso de fallos con Docker, el proyecto incluye **dos servidores de respaldo** accesibles desde el menú "Otras Opciones" en el Launcher:
1. **Servidor Web Local:** Interfaz web programada internamente para jugar contra la IA o IA vs IA.
2. **Servidor de Consola:** Entorno puro en terminal, útil para auditar la lógica del agente o en caso de fallo gráfico.

---
> Proyecto desarrollado con pasión y mucha recursividad heurística 💻✨
