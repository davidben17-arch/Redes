"""
REDES UCR · II-1122 Modelos de Optimización Industrial
=======================================================
App Streamlit — Modelos de Redes (Clase 12)
Prof. David Benavides · UCR Sede Alajuela · I-2026

VERSIÓN AUTOCONTENIDA: los modelos y datos AMPL están
embebidos en este mismo archivo. No requiere carpeta
ejercicios/ ni archivos .mod/.dat externos.
"""

import streamlit as st
from amplpy import AMPL
import tempfile
import os

# ─── CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="Redes UCR — II-1122", page_icon="🕸️", layout="wide")

# ═══════════════════════════════════════════════════════════
#  MODELOS Y DATOS EMBEBIDOS
# ═══════════════════════════════════════════════════════════

MODELO_RUTA = """
set NODOS;
set ARCOS within {NODOS, NODOS};
param tiempo {ARCOS} >= 0;
param origen symbolic in NODOS;
param destino symbolic in NODOS;
var x {(i,j) in ARCOS} >= 0, <= 1;
minimize Tiempo_total:
    sum {(i,j) in ARCOS} tiempo[i,j] * x[i,j];
subject to Balance {k in NODOS}:
    sum {(k,j) in ARCOS} x[k,j] - sum {(i,k) in ARCOS} x[i,k]
    = (if k = origen then 1 else if k = destino then -1 else 0);
"""

MODELO_CPM = """
set EVENTOS;
set PRECEDENCIAS within {EVENTOS, EVENTOS};
param duracion {PRECEDENCIAS} >= 0;
param inicio symbolic in EVENTOS;
param fin    symbolic in EVENTOS;
var t {EVENTOS} >= 0;
minimize Duracion_proyecto: t[fin];
subject to Precedencia {(i,j) in PRECEDENCIAS}:
    t[j] >= t[i] + duracion[i,j];
subject to Inicio_cero: t[inicio] = 0;
"""

DATOS_WALMART = """
set NODOS :=
    Coyol SanJose Cartago CerroMuerte SanIsidro
    Orotina Jaco Parrita Quepos Dominical
    PerezZ Atenas Esparza ;
param origen  := Coyol;
param destino := PerezZ;
param: ARCOS: tiempo :=
    Coyol         SanJose         35
    SanJose       Cartago         40
    Cartago       CerroMuerte     90
    CerroMuerte   SanIsidro       70
    SanIsidro     PerezZ          25
    Coyol         Atenas          20
    Atenas        Orotina         25
    Orotina       Jaco            35
    Jaco          Parrita         40
    Parrita       Quepos          25
    Quepos        Dominical       45
    Dominical     PerezZ          40
    Coyol         Esparza         50
    Esparza       Orotina         30
    Cartago       SanIsidro       155 ;
"""

DATOS_DOSPINOS = """
set NODOS :=
    Coyol Atenas Esparza Puntarenas Caldera
    Miramar Canas Bagaces Tilaran Nicoya Liberia ;
param origen  := Coyol;
param destino := Liberia;
param: ARCOS: tiempo :=
    Coyol         Atenas          15
    Atenas        Esparza         30
    Esparza       Miramar         20
    Miramar       Canas           45
    Canas         Bagaces         20
    Bagaces       Liberia         25
    Esparza       Puntarenas      15
    Puntarenas    Caldera         15
    Caldera       Miramar         25
    Canas         Tilaran         30
    Tilaran       Liberia         55
    Canas         Nicoya          50
    Nicoya        Liberia         60
    Esparza       Canas           80 ;
"""

DATOS_CPM = """
set EVENTOS :=
    Inicio finA finB finC finD finE finF finG Fin ;
param inicio := Inicio;
param fin    := Fin;
param: PRECEDENCIAS: duracion :=
    Inicio    finA      5
    Inicio    finB      3
    finA      finC      8
    finB      finD      6
    finC      finE      4
    finC      finF      7
    finD      finF      7
    finE      finG      3
    finF      Fin       4
    finG      Fin       4 ;
"""

# ─── CATÁLOGO ──────────────────────────────────────────────
EJERCICIOS = {
    "— Selecciona un ejercicio —": None,
    "Ejercicio 1 · Walmart CR — Ruta más corta": {
        "modelo": MODELO_RUTA, "datos": DATOS_WALMART,
        "tipo": "Ruta más corta", "objetivo": "Tiempo_total",
        "descripcion": (
            "**Walmart Costa Rica — Distribución desde CEDI Coyol.**\n\n"
            "Encontrar el camino de menor tiempo desde el Centro de Distribución "
            "de Walmart en Coyol (Alajuela) hasta el MaxiPalí de Pérez Zeledón.\n\n"
            "Red de **13 nodos** y **15 arcos**, con dos rutas paralelas: "
            "GAM/Cerro de la Muerte vs. Pacífico/Costanera."
        ),
        "esperado": "Z* = 230 min (ruta Pacífico/Costanera)",
    },
    "Ejercicio 2 · Dos Pinos — Ruta más corta": {
        "modelo": MODELO_RUTA, "datos": DATOS_DOSPINOS,
        "tipo": "Ruta más corta", "objetivo": "Tiempo_total",
        "descripcion": (
            "**Dos Pinos — Despacho a Liberia.**\n\n"
            "Despachar un cargamento refrigerado desde la planta de Dos Pinos en "
            "Coyol al AutoMercado de Liberia minimizando el tiempo de viaje.\n\n"
            "Red de **11 nodos** del Pacífico Norte con **14 arcos**."
        ),
        "esperado": "Z* = 155 min (Interamericana Norte directa)",
    },
    "Ejercicio 3 · CPM Proyecto — Camino crítico": {
        "modelo": MODELO_CPM, "datos": DATOS_CPM,
        "tipo": "Ruta más larga (CPM)", "objetivo": "Duracion_proyecto",
        "descripcion": (
            "**Camino Crítico — Proyecto Industrial.**\n\n"
            "Calcular la duración mínima de un proyecto con **8 actividades (A-H)** "
            "y sus precedencias. El modelo encuentra el camino más largo en la red "
            "de precedencias — las actividades de ese camino no pueden atrasarse sin "
            "retrasar el proyecto completo."
        ),
        "esperado": "Duración mínima = 24 días (A→C→F→H)",
    },
}

# ─── ESTILO ────────────────────────────────────────────────
st.markdown("""
<style>
.main-header { background: linear-gradient(135deg,#003366 0%,#0066a2 100%);
    padding:1.3rem 1.8rem; border-radius:10px; margin-bottom:1.2rem; color:white; }
.main-header h1 { margin:0; font-size:1.55rem; }
.main-header p  { margin:0.3rem 0 0; opacity:0.9; font-size:0.88rem; }
.tipo-badge { display:inline-block; background:#003366; color:white;
    padding:0.2rem 0.6rem; border-radius:12px; font-size:0.78rem;
    font-weight:600; margin-bottom:0.5rem; }
[data-testid="stSidebar"] { background-color:#f5f8fc; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🕸️ Modelos de Redes — Optimización</h1>
    <p>II-1122 Modelos de Optimización Industrial · Clase 12 · Prof. David Benavides · UCR Sede Alajuela · I-2026</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Ejercicios disponibles")
    seleccion = st.selectbox("Elegí un ejercicio:", list(EJERCICIOS.keys()),
                             label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### ⚙️ Solver")
    solver_choice = st.radio("Motor:", ["highs", "cbc"], index=0)
    st.markdown("---")
    st.caption("💡 Cada ejercicio se resuelve directo en la app.")

# ─── FUNCIÓN RESOLVER ──────────────────────────────────────
def resolver(modelo_txt, datos_txt, objetivo, solver):
    """Escribe modelo y datos a archivos temporales y resuelve con AMPL."""
    with tempfile.TemporaryDirectory() as d:
        mod_p = os.path.join(d, "modelo.mod")
        dat_p = os.path.join(d, "datos.dat")
        with open(mod_p, "w") as f: f.write(modelo_txt)
        with open(dat_p, "w") as f: f.write(datos_txt)
        ampl = AMPL()
        ampl.read(mod_p)
        ampl.read_data(dat_p)
        ampl.option["solver"] = solver
        ampl.solve()
        obj = ampl.get_objective(objetivo).value()
        activas = []
        for vname, vobj in ampl.get_variables():
            df = vobj.get_values().to_pandas()
            if not df.empty:
                col = df.columns[-1]
                act = df[df[col].abs() > 1e-6]
                if not act.empty:
                    activas.append((vname, act))
        return obj, activas

# ─── CUERPO ────────────────────────────────────────────────
ej = EJERCICIOS[seleccion]

if ej is None:
    st.info("👈 **Seleccioná un ejercicio** desde la barra lateral.")
else:
    st.markdown(f'<div class="tipo-badge">{ej["tipo"]}</div>', unsafe_allow_html=True)
    st.markdown(f"## {seleccion.split('· ', 1)[1]}")
    st.markdown(ej["descripcion"])

    c1, c2 = st.columns(2)
    with c1:
        with st.expander("📄 Modelo AMPL"):
            st.code(ej["modelo"], language="text")
    with c2:
        with st.expander("📊 Datos AMPL"):
            st.code(ej["datos"], language="text")

    st.markdown(f"**Resultado esperado:** `{ej['esperado']}`")
    st.markdown("---")

    if st.button("🚀 Resolver ejercicio", type="primary", use_container_width=True):
        try:
            with st.spinner(f"Resolviendo con {solver_choice.upper()}..."):
                obj, activas = resolver(ej["modelo"], ej["datos"],
                                        ej["objetivo"], solver_choice)
            st.success("### ✅ Solución óptima encontrada")
            st.metric(f"Valor objetivo Z* ({ej['objetivo']})", f"{obj:.2f}")
            st.markdown("### 📌 Variables activas")
            for vname, df in activas:
                st.markdown(f"**Variable `{vname}`**")
                st.dataframe(df, use_container_width=True)
            st.markdown("### 💡 Interpretación")
            if "corta" in ej["tipo"].lower():
                st.info(f"Los arcos con `x = 1` forman la **ruta óptima**. "
                        f"Tiempo mínimo: **{obj:.0f} minutos**.")
            else:
                st.info(f"**Duración mínima del proyecto: {obj:.0f} días.** "
                        f"Las actividades del camino crítico no pueden atrasarse.")
        except Exception as e:
            st.error(f"Error al resolver: {e}")

st.markdown("---")
st.caption("II-1122 · Prof. David Benavides · UCR Sede Alajuela · I-2026 · "
           "[GitHub](https://github.com/davidben17-arch/Redes)")
