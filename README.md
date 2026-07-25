# 🧠 Agente Inteligente para Connect6 (MCTS + UCB1 + Deep Learning)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.14-orange.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-Ready-green.svg)

Este repositorio contiene la implementación de un agente de Inteligencia Artificial desarrollado en Python para jugar **Connect6**. El agente se conecta a un servidor de juego mediante **gRPC** y toma decisiones en tiempo real utilizando una arquitectura híbrida: **Monte Carlo Tree Search (MCTS)** con selección de política **UCB1**, una **Red Neuronal Convolucional (CNN)** para la política de simulación (*playout policy*), **Libro de Aperturas** y **Detección Táctica de Amenazas**.

---

## 📑 Tabla de Contenidos
1. [Tecnologías Utilizadas](#-tecnologías-utilizadas)
2. [Estructura del Proyecto](#-estructura-del-proyecto)
3. [Requisitos Previos](#-requisitos-previos)
4. [Instalación y Configuración](#-instalación-y-configuración)
5. [Ejecución del Entorno](#-ejecución-del-entorno)
6. [Arquitectura de la Inteligencia Artificial](#-arquitectura-de-la-inteligencia-artificial)
7. [Autores](#-autores)

---

## 🚀 Tecnologías Utilizadas
* **Lenguaje Principal:** Python 3.10+
* **Inteligencia Artificial:** TensorFlow / Keras (CNN) + NumPy
* **Algoritmos de Búsqueda:** Monte Carlo Tree Search (MCTS) con ecuación UCB1 (UCT).
* **Heurísticas y Estrategia:** Opening Book + Win-in-1 / Block-in-1 Tactical Threat Engine.
* **Comunicación de Red:** gRPC (Streaming bidireccional) y Protobuf.
* **Virtualización:** Docker y Docker Compose.

---

## 📂 Estructura del Proyecto
```text
📁 ProyectoIA/
│
├── 📁 proto/                             # Definición de gRPC Protobuf
│   └── 📄 connect6.proto                 # Contrato del servidor Connect6 Arena
│
├── 📄 agente_connect6.py                 # Código principal de la IA (MCTS + CNN + UCB1 + Tácticas)
├── 📄 requirements.txt                   # Dependencias de Python
├── 📄 Dockerfile                         # Instrucciones de construcción del contenedor
├── 📄 docker-compose.yml                 # Orquestación del servidor visual y el agente
├── 📄 Leeme.txt                          # Guía rápida de ejecución (Exigido en pautas)
└── 📄 README.md                          # Documentación del proyecto
```

---

## 🛠️ Requisitos Previos
* **Python 3.10+** (Para ejecución local)
* **Docker Desktop** (Opcional, para ejecución en contenedor)

---

## ⚙️ Instalación y Configuración

### 1. Compilación gRPC (Obligatorio para ejecución sin Docker)
```bash
pip install -r requirements.txt
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/connect6.proto
```

---

## ▶️ Ejecución del Entorno

### Con Docker Compose:
```bash
docker compose up --build
```
Abre en tu navegador web: 👉 **http://localhost:8080**

### Directo con Python:
```bash
python agente_connect6.py
```

---

## 🧠 Arquitectura de la Inteligencia Artificial

1. **Libro de Aperturas (Opening Book):** Ejecuta movimientos iniciales predefinidos para optimizar el control del centro en las primeras jugadas.
2. **Motor Táctico (Detección de Situaciones Borde):** Escanea el tablero en búsqueda de victorias inminentes (Win-in-1) o bloqueos defensivos obligatorios (Block-in-1) contra líneas de 4 o 5 fichas del oponente.
3. **MCTS con Selección UCB1:** Construye un árbol de decisiones simulando estados futuros. Utiliza la ecuación UCB1 para balancear la exploración de nuevas ramas y la explotación de líneas ganadoras.
4. **Red Neuronal Convolucional (Playout Policy):** Guiada por TensorFlow, evalúa tableros durante la fase de simulación de MCTS acotando la selección a casillas estratégicamente prometedoras.

---

## 👨‍💻 Autores
* **Equipo:** Equipo_Obando_Llambi
* **Integrantes:** Jesús Obando, Sebastian Llambi
* **Universidad Católica Andrés Bello (UCAB) - 2026**
