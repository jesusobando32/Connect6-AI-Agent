# 🧠 Agente Inteligente para Connect6 (MCTS + Deep Learning)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.14-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-Ready-green.svg)

Este repositorio contiene la implementación de un agente de Inteligencia Artificial desarrollado en Python para jugar **Connect6**. El agente se conecta a un servidor de juego mediante **gRPC** y toma decisiones óptimas en tiempo real utilizando el algoritmo **Monte Carlo Tree Search (MCTS)** guiado por una **Red Neuronal Convolucional (CNN)** que evalúa el tablero y predice las mejores jugadas.

---

## 📑 Tabla de Contenidos
1. [Tecnologías Utilizadas](#-tecnologías-utilizadas)
2. [Estructura del Proyecto](#-estructura-del-proyecto)
3. [Requisitos Previos](#-requisitos-previos)
4. [Instalación y Configuración](#-instalación-y-configuración)
5. [Ejecución del Entorno](#-ejecución-del-entorno)
6. [Arquitectura de la Inteligencia Artificial](#-arquitectura-de-la-inteligencia-artificial)
7. [Solución de Problemas Frecuentes (Troubleshooting)](#-solución-de-problemas-frecuentes)
8. [Autores](#-autores)

---

## 🚀 Tecnologías Utilizadas
* **Lenguaje Principal:** Python 3.10+
* **Inteligencia Artificial:** TensorFlow / Keras (CNN) + Numpy
* **Algoritmos de Búsqueda:** Monte Carlo Tree Search (MCTS) con política UCB1.
* **Comunicación de Red:** gRPC (Streaming bidireccional) y Protobuf.
* **Despliegue y Virtualización:** Docker y Docker Compose.

---

## 📂 Estructura del Proyecto
```text
📁 ProyectoIA/
│
├── 📁 proto/                             # Carpeta con el contrato gRPC original
│   └── 📄 connect6.proto                 # Archivo de definición del servidor (No modificar)
│
├── 📄 agente_connect6.py                 # Lógica principal del Agente (MCTS + Red Neuronal)
├── 📄 requirements.txt                   # Dependencias de Python (TensorFlow, grpcio, numpy)
├── 📄 Dockerfile                         # Instrucciones de construcción del contenedor de la IA
├── 📄 docker-compose.yml                 # Orquestación del servidor visual y el agente local
└── 📄 README.md                          # Documentación del proyecto
```

## 🛠️ Requisitos Previos
Para clonar y ejecutar este proyecto de forma local, asegúrate de tener instalado:

* **Docker Desktop:** Asegúrate de tener la virtualización (Intel VT-x / AMD-V) activada en la BIOS de tu sistema operativo.
* **Python 3.10 o superior:** Para compilar los archivos locales si deseas hacer pruebas fuera de Docker.
* **Git:** Para clonar el repositorio.

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio
Descarga el código fuente a tu máquina local:

```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
```

### 2. Compilar los archivos de conexión gRPC (Obligatorio)
Para que el agente en Python pueda comunicarse con el servidor, debes compilar el contrato `.proto`. Abre tu terminal en la raíz del proyecto y ejecuta los siguientes comandos:

```bash
# Instalar las herramientas de compilación
pip install grpcio grpcio-tools

# Generar los archivos connect6_pb2.py y connect6_pb2_grpc.py
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/connect6.proto
```
*Nota: Si utilizas Docker, el Dockerfile puede estar configurado para ejecutar este paso de forma automática durante el build.*

## ▶️ Ejecución del Entorno
Una vez que tengas los archivos compilados y las dependencias listas, levantar todo el sistema (Servidor de juego + Interfaz Web + Agente Inteligente) es muy sencillo gracias a Docker Compose:

1. Abre la terminal en la carpeta raíz del proyecto.
2. Construye las imágenes y levanta los contenedores:
```bash
docker compose up --build
```
3. Espera a que la terminal muestre que el agente se ha conectado con éxito:
   `📥 Jugador conectado: Equipo_Obando_Llambi (bot=false)`
4. Abre tu navegador web y entra a la arena visual para ver la partida en tiempo real:
   👉 http://localhost:8080 (o http://127.0.0.1:8080)

Para detener los contenedores de forma segura, presiona `Ctrl+C` en la terminal o ejecuta:
```bash
docker compose down
```

## 🧠 Arquitectura de la Inteligencia Artificial
El agente `agente_connect6.py` funciona mediante un enfoque híbrido, combinando algoritmos clásicos de búsqueda con aprendizaje profundo:

* **Detección Rápida y Heurísticas:** El sistema escanea la matriz bidimensional de 19x19 en cada turno para detectar victorias inminentes (líneas de 6 fichas) o bloqueos obligatorios (líneas de 5 fichas del oponente), actuando de inmediato sin gastar tiempo de cómputo en búsquedas innecesarias.
* **Playout Policy (Red Neuronal Convolucional):** En un MCTS estándar, las simulaciones hasta el final del juego se hacen de forma aleatoria. En este agente, una CNN evalúa el estado actual del tablero y devuelve una distribución de probabilidad que guía la simulación hacia las casillas tácticamente más prometedoras, emulando estrategias de alto nivel.
* **MCTS + Ecuación UCB1:** El núcleo del sistema construye un árbol de decisiones iterativo simulando posibles futuros. Utiliza la fórmula matemática UCB1 para mantener un equilibrio perfecto entre la exploración de nuevas ramas estratégicas y la explotación de los movimientos con mayor tasa de victoria comprobada.

## 🔧 Solución de Problemas Frecuentes
* **Error: `no matching manifest for linux/amd64` (o viceversa) al ejecutar Docker Compose**
  Esto ocurre por diferencias de arquitectura entre tu procesador (Intel/AMD vs Apple Silicon/ARM). Para solucionarlo, abre el archivo `docker-compose.yml` y ajusta o agrega la etiqueta `platform` debajo de la imagen del servidor:
  * Para PC tradicional (Intel/AMD Windows/Linux): `platform: linux/amd64` o `platform: linux/arm64` (para forzar emulación).
  * Para Mac (M1/M2/M3): `platform: linux/arm64`.
* **Error: `ERR_CONNECTION_REFUSED` en el navegador web**
  Significa que el contenedor del servidor se detuvo. Ejecuta `docker ps` para ver si el contenedor sigue activo. Si no lo está, revisa los logs con `docker logs proyectoia-servidor-1` para identificar la falla exacta o intenta acceder mediante la IP explícita `http://127.0.0.1:8080`.
* **Error: `AttributeError: 'GameServerStub' object has no attribute 'RegisterTeam'`**
  Este error de gRPC ocurre si intentas llamar funciones que no existen en el `.proto`. El código de este repositorio ya está adaptado para usar el streaming bidireccional correcto (`stub.Play()`) enviando objetos `PlayerAction`, por lo que este error no debería aparecer si utilizas el `agente_connect6.py` provisto aquí.

## 👨‍💻 Autores
Este proyecto fue desarrollado como parte de las evaluaciones académicas de Inteligencia Artificial.

* **Equipo:** Equipo_Obando_Llambi
* **Desarrolladores:** Jesús Obando, Sebastian Llambi
