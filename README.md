# 🧠 Agente Inteligente para Connect6 (MCTS + Deep Learning)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.14-orange.svg)
![gRPC](https://img.shields.io/badge/gRPC-Ready-green.svg)

---

## 🎓 Información Académica
* **Universidad:** Universidad Católica Andrés Bello (UCAB)
* **Materia:** Inteligencia Artificial: Aprendizaje Automático
* **Semestre:** Marzo - Julio 2026
* **Equipo:** Equipo_Obando_Llambi
* **Autores:** Jesús Obando, Sebastian Llambi

---

Este repositorio contiene la implementación de un agente de Inteligencia Artificial desarrollado en Python para jugar **Connect6**. El agente se conecta a un servidor de juego mediante **gRPC** y toma decisiones en tiempo real utilizando una arquitectura híbrida: **Monte Carlo Tree Search (MCTS)** con selección de política **UCB1**, una **Red Neuronal (Deep Learning)** para predecir movimientos (*playout policy*), y un **Motor Táctico de Detección de Amenazas**.

---

## 🚀 Instalación Rápida

1. Asegúrate de tener Python 3.10 o superior instalado.
2. (Opcional pero recomendado) Crea un entorno virtual.
3. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
4. Compila el contrato gRPC (si no lo has hecho):
   ```bash
   python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/connect6.proto
   ```

---

## ▶️ ¿Cómo Correr el Proyecto? (Launcher Web)

Hemos desarrollado un **Launcher Web Moderno** para controlar todo el proyecto de forma visual sin necesidad de tocar la consola.

Simplemente ejecuta en tu terminal:
```bash
python launcher_web.py
```
👉 Se abrirá automáticamente un menú en tu navegador en `http://localhost:5000`. 
Desde allí podrás **entrenar a la IA**, arrancar el servidor oficial de la profesora Laura Parilli en Docker, o acceder a las opciones de emergencia.

### ⚠️ AVISO IMPORTANTE: Servidor Oficial de la Profesora Laura Parilli (Docker)
Si decides levantar el servidor de la profesora Laura Parilli ("Connect6 Arena" original) desde el menú, ten en cuenta el siguiente **defecto de su interfaz web**:
* Al entrar a la configuración de la partida en `http://localhost:8080`, **SIEMPRE debes seleccionar la opción "Humano vs Humano"**. 
* Aunque vayas a jugar tú contra la Inteligencia Artificial, si seleccionas "Humano vs IA" en su interfaz, el sistema se colgará (es un bug del archivo ejecutable original en Go). 
* Selecciona "Humano vs Humano", la IA se conectará solita en segundo plano como el jugador negro y podrás jugar con normalidad.

---

## 🆘 Opciones de Emergencia (Sin Docker)

En caso de que el Docker de la profesora Laura falle durante la evaluación, o no tengas internet, el proyecto viene equipado con **dos servidores de respaldo 100% en Python**.

Puedes acceder a ellos desde el menú **"Otras Opciones"** en el Launcher Web:

1. **Servidor Web Local (Recomendado):** Levanta un servidor web muy parecido al de la profesora Laura, pero programado internamente. Te permitirá ver el tablero gráficamente, jugar contra la IA o poner a competir IA vs IA. ¡Lo mejor es que la IA se lanza sola!
2. **Servidor de Consola (Texto):** Un entorno crudo en la consola. Verás el tablero impreso con caracteres (X y O) e ingresarás coordenadas con tu teclado. Excelente para auditar la lógica o si todo el sistema gráfico colapsa.

*(Nota: Al abrir cualquiera de estas dos opciones, el script se encarga de levantar y cerrar automáticamente el proceso de `agente_connect6.py` en segundo plano, por lo que no debes preocuparte de hacerlo manual).*

---

## 🧠 Arquitectura de la Inteligencia Artificial

1. **Motor Táctico (Detección de Amenazas):** Escanea el tablero en las 4 direcciones (horizontal, vertical y ambas diagonales) en búsqueda de victorias inminentes (Win-in-1) o bloqueos defensivos obligatorios (Block-in-1) contra líneas de 4 o 5 fichas del oponente.
2. **MCTS con Selección UCB1:** Construye un árbol de decisiones simulando estados futuros. Utiliza la ecuación UCB1 para balancear la exploración de nuevas ramas y la explotación de líneas ganadoras.
3. **Red Neuronal (Playout Policy):** Entrenada localmente mediante **Self-Play** (IA jugando contra IA). En lugar de hacer simulaciones aleatorias hasta el final del juego, la red evalúa qué movimientos son los más prometedores, ahorrando un inmenso poder de cómputo.

---

## 👨‍💻 Autores
* **Equipo:** Equipo_Obando_Llambi
* **Integrantes:** Jesús Obando, Sebastian Llambi
* **Universidad Católica Andrés Bello (UCAB) - 2026**
