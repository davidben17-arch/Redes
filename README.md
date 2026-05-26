# 🕸️ Redes UCR — II-1122

App Streamlit con ejercicios de **modelos de redes** (Clase 12) del curso
**II-1122 Modelos de Optimización Industrial** — UCR Sede Alajuela · I-2026.

**Prof. David Benavides**

## 🎯 ¿Qué hace esta app?

Selector interactivo de 3 ejercicios de redes precargados. El estudiante elige
el ejercicio, ve el modelo `.mod` y los datos `.dat`, presiona **"Resolver"** y
obtiene el resultado óptimo con interpretación.

**Cero copy-paste. Cero instalación.**

## 📋 Ejercicios incluidos

| # | Ejercicio | Tipo | Resultado |
|---|-----------|------|-----------|
| 1 | Walmart CR — CEDI Coyol → Pérez Zeledón | Ruta más corta | 230 min |
| 2 | Dos Pinos — Coyol → Liberia | Ruta más corta | 155 min |
| 3 | CPM Proyecto — 8 actividades | Ruta más larga | 24 días |

## 🗂️ Estructura del repo

```
davidben17-arch/Redes/
├── streamlit_app.py       ← App principal
├── requirements.txt       ← Dependencias AMPL + Streamlit
├── README.md              ← Este archivo
└── ejercicios/
    ├── walmart_cr.mod
    ├── walmart_cr.dat
    ├── dos_pinos.mod
    ├── dos_pinos.dat
    ├── cpm_proyecto.mod
    └── cpm_proyecto.dat
```

## 🚀 Desplegar en Streamlit Cloud

1. Subir todos los archivos al repo `davidben17-arch/Redes` en GitHub
2. Ir a [share.streamlit.io](https://share.streamlit.io)
3. **New app** → seleccionar repo `davidben17-arch/Redes`
4. Branch: `main` · Main file: `streamlit_app.py`
5. **Deploy** → URL pública en ~3 minutos

## 🧮 Modelos matemáticos

**Ruta más corta** (Walmart, Dos Pinos):
```
min  Σ tᵢⱼ · xᵢⱼ
s.a. Σⱼ xₖⱼ − Σᵢ xᵢₖ = bₖ   ∀ k ∈ Nodos
     xᵢⱼ ∈ [0,1]
```
con bₖ = +1 (origen), −1 (destino), 0 (tránsito).

**CPM — Camino crítico**:
```
min  t[fin]
s.a. t[j] ≥ t[i] + dᵢⱼ   ∀ (i,j) ∈ Precedencias
     t[inicio] = 0
     t[k] ≥ 0
```

Ambos LP dan solución entera natural por la unimodularidad total de la matriz
de incidencia nodo-arco.

---

*II-1122 · UCR Sede Alajuela · I-2026*
