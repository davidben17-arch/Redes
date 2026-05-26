
# =========================================================
# Walmart CR — Ruta más corta
# CEDI Coyol → MaxiPalí Pérez Zeledón
# II-1122 · Clase 12 · UCR Sede Alajuela
# =========================================================

set NODOS;
set ARCOS within {NODOS, NODOS};

param tiempo {ARCOS} >= 0;
param origen symbolic in NODOS;
param destino symbolic in NODOS;

var x {(i,j) in ARCOS} >= 0, <= 1;

minimize Tiempo_total:
    sum {(i,j) in ARCOS} tiempo[i,j] * x[i,j];

subject to Balance {k in NODOS}:
    sum {(k,j) in ARCOS} x[k,j]
  - sum {(i,k) in ARCOS} x[i,k]
    =
    (if k = origen then 1
     else if k = destino then -1
     else 0);
