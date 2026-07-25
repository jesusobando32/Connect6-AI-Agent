# Informe del Proyecto: Agente de Juego Inteligente para Connect6

**Universidad Católica Andrés Bello**  
**Escuela de Informática**  
**Inteligencia Artificial: Aprendizaje Automático**  
**Semestre:** Marzo - Julio 2026  

---

## 1. Información de los Autores

* **Jesús Obando**
* **Sebastian Llambi**
* **Nombre de Equipo Registrado:** `Equipo_Obando_Llambi`

---

## 2. Descripción del Sistema

### 2.1 Resumen General
El sistema desarrollado consiste en un agente inteligente capaz de competir autónomamente en el juego de estrategia combinatoria **Connect6** mediante una arquitectura híbrida de Inteligencia Artificial. El agente combina **Búsqueda en Árboles de Monte Carlo (Monte Carlo Tree Search - MCTS)** guiada por la fórmula de selección **UCB1**, una **Red Neuronal Convolucional Profunda (CNN)** para la política de simulación (*playout policy*), y un **Motor de Reglas Tácticas y Aperturas** diseñado específicamente para reducir la complejidad computacional del tablero de $19 \times 19$.

La comunicación entre el agente cliente y la plataforma de evaluación **Connect6 Arena** se realiza mediante streaming bidireccional sobre el protocolo **gRPC**.

---

### 2.2 Algoritmo Principal: Monte Carlo Tree Search (MCTS)

El comportamiento de toma de decisiones del agente se basa en el ciclo iterativo de cuatro fases de MCTS:

1. **Selección (Selection):** Navega recursivamente por el árbol de búsqueda comenzando desde el estado actual (raíz). En cada nodo completamente expandido, la selección del nodo hijo se rige por la política **UCB1** (*Upper Confidence Bound applied to Trees*), balanceando la explotación de victorias pasadas y la exploración de ramas poco visitadas:
   $$\text{UCB1}(c) = \frac{W_c}{N_c} + C \cdot \sqrt{\frac{\ln N_{\text{padre}}}{N_c}}$$
   donde $W_c$ es el número de victorias acumuladas por el hijo $c$, $N_c$ es el número de visitas al hijo $c$, $N_{\text{padre}}$ son las visitas al nodo padre y $C = \sqrt{2} \approx 1.414$ es la constante de exploración.

2. **Expansión (Expansion):** Si el nodo seleccionado no es terminal y posee combinaciones de jugadas aún no probadas, se genera un nuevo nodo hijo aplicando un par de fichas válidas en el tablero y alternando el turno del jugador.

3. **Simulación (Playout / Rollout):** Desde el nuevo estado expandido, el agente simula una partida hasta una profundidad fija o estado terminal. A diferencia del MCTS estándar donde las jugadas de simulación son 100% aleatorias, nuestro agente utiliza la recomendación de la **Red Neuronal Convolucional Profunda** (*Playout Policy*) para elegir movimientos tácticamente superiores.

4. **Retropropagación (Backpropagation):** El resultado de la simulación ($+1.0$ por victoria, $-1.0$ por derrota, $0.0$ por empate) se propaga en reversa hacia el nodo raíz, actualizando los contadores de visitas $N$ y victorias acumuladas $W$.

---

### 2.3 Red Neuronal Profunda y Aprendizaje por Refuerzo (Playout Policy)

Para elevar la calidad de las simulaciones MCTS, el sistema incorpora una Red Neuronal Convolucional (CNN) implementada en **TensorFlow / Keras**.

* **Entrada del Modelo:** Tensor tridimensional de dimensiones $(19, 19, 1)$, que representa el estado del tablero con codificación de casillas (0: Vacío, 1: Fichas Negras, 2: Fichas Blancas).
* **Arquitectura de la Red:**
  * **Capa Convolucional 1:** 32 filtros de $(3 \times 3)$, activación ReLU y *same padding* para extraer patrones locales de líneas y diagonales.
  * **Capa Convolucional 2:** 64 filtros de $(3 \times 3)$, activación ReLU y *same padding* para reconocer combinaciones tácticas complejas.
  * **Capa Flatten:** Aplanado de características bidimensionales.
  * **Capa Densa Oculta:** 128 neuronas con activación ReLU.
  * **Capa de Salida:** 361 neuronas ($19 \times 19$) con activación Softmax, que produce una distribución de probabilidad sobre todas las posiciones del tablero.
* **Integración en Playout:** Durante el playout, la red evalúa el estado del tablero y asigna probabilidades a las casillas vacías candidatas. El agente muestrea jugadas según esta distribución de probabilidad, simulando contrincantes más inteligentes que un jugador aleatorio.

---

### 2.4 Heurísticas y Estrategias del Juego Connect6

El tablero de Connect6 en una cuadricula de $19 \times 19$ líneas genera una cantidad de jugadas posibles por turno del orden de $\binom{361}{2} = 64,980$ pares de fichas. Para asegurar respuestas en menos de 10 segundos, el agente utiliza tres estrategias dominio-específicas:

1. **Libro de Aperturas (Opening Book):**
   * Si el agente juega con Negras (primer jugador, 1 ficha necesaria), coloca la primera ficha automáticamente en la posición central $(9,9)$ para maximizar el control espacial.
   * Si el agente juega con Blancas respondiendo al centro, coloca un par de fichas estelares continuas $(9,10)$ y $(10,9)$ para neutralizar la expansión del primer jugador.

2. **Detección Táctica de Situaciones Borde (Engine de Amenazas Inmediatas):**
   * **Win-in-1 (Victoria Inmediata):** Antes de iniciar la búsqueda MCTS, el agente escanea el tablero. Si puede completar 6 fichas consecutivas (horizontales, verticales o diagonales) en el turno actual, ejecuta la jugada ganadora inmediatamente.
   * **Block-in-1 (Bloqueo Obligatorio):** Si el oponente posee una línea de 4 o 5 fichas abiertas que le permitirían ganar en su siguiente turno, el agente interrumpe el MCTS y bloquea de inmediato las casillas críticas.

3. **Poda de Espacio de Búsqueda por Proximidad (Candidate Filter):**
   * En lugar de considerar las 361 casillas en cada paso del MCTS, el motor filtra únicamente aquellas casillas vacías ubicadas a una distancia Chebyshev $d \le 2$ de las fichas ya colocadas. Esto reduce los candidatos a 20-40 casillas relevantes, acelerando el MCTS en más de 100x.

---

## 3. Referencias Bibliográficas

1. Stuart Russell and Peter Norvig. *Artificial Intelligence: A Modern Approach*. Pearson, 4th edition, 2022. (Capítulo 6: Adversarial Search and Games - MCTS & UCB1).
2. David Silver, Aja Huang, Chris J. Maddison, Arthur Guez, Laurent Sifre, George Van Den Driessche, Julian Schrittwieser, Ioannis Antonoglou, Veda Panneershelvam, Marc Lanctot, et al. *Mastering the game of Go with deep neural networks and tree search*. Nature, 529(7587):484–489, 2016.
3. Wikipedia contributors. *Connect6 — Wikipedia, the free encyclopedia*, 2022. [En línea; visitado 10-Nov-2022].
4. Laura Parilli y Miguel Salomon. *Connect6 Arena Starter Kit*, 2026. [En línea].
