"""
REDES UCR · II-1122 Modelos de Optimización Industrial
=======================================================
App Streamlit — Modelos de Redes (Clase 12)
Prof. David Benavides · UCR Sede Alajuela · I-2026

REPO: davidben17-arch/Redes
DEPLOY: redes-ucr.streamlit.app
"""

import streamlit as st
from amplpy import AMPL
from pathlib import Path

# ─── CONFIG ────────────────────────────────────────────────
st.set_page_config(
    page_title="Redes UCR — II-1122",
    page_icon="🕸️",
    layout="wide",
)

EJERCICIOS_DIR = Path(__file__).parent / "ejercicios"

# ─── CATÁLOGO DE EJERCICIOS ────────────────────────────────
EJERCICIOS = {
    "— Selecciona un ejercicio —": None,

    "Ejercicio 1 · Walmart CR — Ruta más corta": {
        "mod": "walmart_cr.mod",
        "dat": "walmart_cr.dat",
        "tipo": "Ruta más corta",
        "descripcion": (
            "**Walmart Costa Rica — Distribución desde CEDI Coyol.**\n\n"
            "Encontrar el camino de menor tiempo desde el Centro de Distribución "
            "de Walmart en Coyol (Alajuela) hasta el MaxiPalí de Pérez Zeledón.\n\n"
            "La red tiene **13 nodos** y **15 arcos**, con dos rutas paralelas:\n"
            "- **Ruta GAM/Cerro de la Muerte** (vía San José - Cartago - Cerro)\n"
            "- **Ruta Pacífico/Costanera** (vía Orotina - Jacó - Quepos - Dominical)"
        ),
        "esperado": "Z* = 230 minutos (ruta Pacífico/Costanera)",
        "objetivo": "Tiempo_total",
    },

    "Ejercicio 2 · Dos Pinos — Ruta más corta Pacífico Norte": {
        "mod": "dos_pinos.mod",
        "dat": "dos_pinos.dat",
        "tipo": "Ruta más corta",
        "descripcion": (
            "**Dos Pinos — Despacho a Liberia.**\n\n"
            "Despachar un cargamento refrigerado desde la planta de Dos Pinos en "
            "Coyol al AutoMercado de Liberia minimizando el tiempo de viaje.\n\n"
            "Red de **11 nodos** del Pacífico Norte con **15 arcos**, incluyendo "
            "rutas alternas por Cañas, Bagaces y la Interamericana Norte."
        ),
        "esperado": "Z* = 155 minutos (Coyol→Atenas→Esparza→Miramar→Cañas→Bagaces→Liberia)",
        "objetivo": "Tiempo_total",
    },

    "Ejercicio 3 · CPM Proyecto — Camino crítico": {
        "mod": "cpm_proyecto.mod",
        "dat": "cpm_proyecto.dat",
        "tipo": "Ruta más larga (CPM)",
        "descripcion": (
            "**Camino Crítico — Proyecto Industrial.**\n\n"
            "Calcular la duración mínima de un proyecto con **8 actividades (A-H)** "
            "y sus precedencias. El modelo encuentra el camino más largo en la red "
            "de precedencias — las actividades en este camino son las que NO pueden "
            "atrasarse sin retrasar el proyecto completo.\n\n"
            "Aplicación clásica de **ruta más larga** en gestión de proyectos."
        ),
        "esperado": "Duración mínima = 24 días (camino A→C→F→H)",
        "objetivo": "Duracion_proyecto",
    },
}

# ─── ESTILO ────────────────────────────────────────────────
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #003366 0%, #0066a2 100%);
    padding: 1.3rem 1.8rem; border-radius: 10px; margin-bottom: 1.2rem; color: white;
}
.main-header h1 { margin: 0; font-size: 1.55rem; }
.main-header p  { margin: 0.3rem 0 0; opacity: 0.9; font-size: 0.88rem; }
.info-card {
    background: #f0f7ff; border-left: 4px solid #0066a2;
    padding: 0.9rem 1.1rem; border-radius: 6px; margin-bottom: 0.8rem;
}
.tipo-badge {
    display: inline-block; background: #003366; color: white;
    padding: 0.2rem 0.6rem; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600; margin-bottom: 0.5rem;
}
[data-testid="stSidebar"] { background-color: #f5f8fc; }
.stMetric { background: #f0f7ff; padding: 0.8rem; border-radius: 8px; }
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
    seleccion = st.selectbox(
        "Elegí un ejercicio:",
        list(EJERCICIOS.keys()),
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### ⚙️ Solver")
    solver_choice = st.radio(
        "Motor de resolución:",
        ["highs", "cbc"],
        index=0,
        help="HiGHS es más rápido para LP. CBC también resuelve MIP.",
    )

    st.markdown("---")
    st.caption(
        "💡 Cada ejercicio se resuelve directo en la app. "
        "No necesitás instalar AMPL ni copiar código."
    )
    st.caption("Repo: `davidben17-arch/Redes`")

# ─── CUERPO PRINCIPAL ──────────────────────────────────────
ej = EJERCICIOS[seleccion]

if ej is None:
    st.info(
        "👈 **Seleccioná un ejercicio** desde la barra lateral para ver su "
        "descripción, modelo AMPL y resolverlo."
    )

    st.markdown("### 🎯 ¿Qué hace esta app?")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="info-card">
        <h4>🛣️ Ruta más corta</h4>
        Encontrar el camino de menor costo/tiempo entre dos nodos.
        Casos: Walmart, Dos Pinos.
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="info-card">
        <h4>📅 CPM — Camino crítico</h4>
        Identificar las actividades que determinan la duración mínima
        de un proyecto.
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="info-card">
        <h4>🔢 Solución entera natural</h4>
        Por la unimodularidad total de la matriz de incidencia,
        el LP da soluciones binarias sin Branch & Bound.
        </div>
        """, unsafe_allow_html=True)

else:
    # ─── DESCRIPCIÓN ───────────────────────────────────────
    st.markdown(f'<div class="tipo-badge">{ej["tipo"]}</div>', unsafe_allow_html=True)
    st.markdown(f"## {seleccion.split('· ', 1)[1]}")
    st.markdown(ej["descripcion"])

    # ─── ARCHIVOS DEL MODELO ──────────────────────────────
    mod_path = EJERCICIOS_DIR / ej["mod"]
    dat_path = EJERCICIOS_DIR / ej["dat"]

    col1, col2 = st.columns(2)
    with col1:
        with st.expander(f"📄 Modelo AMPL ({ej['mod']})", expanded=False):
            try:
                st.code(mod_path.read_text(encoding="utf-8"), language="text")
            except Exception as e:
                st.error(f"No se pudo leer el modelo: {e}")
    with col2:
        with st.expander(f"📊 Datos AMPL ({ej['dat']})", expanded=False):
            try:
                st.code(dat_path.read_text(encoding="utf-8"), language="text")
            except Exception as e:
                st.error(f"No se pudo leer los datos: {e}")

    st.markdown(f"**Resultado esperado:** `{ej['esperado']}`")

    # ─── RESOLVER ──────────────────────────────────────────
    st.markdown("---")
    if st.button("🚀 Resolver ejercicio", type="primary", use_container_width=True):
        try:
            with st.spinner(f"Resolviendo con {solver_choice.upper()}..."):
                ampl = AMPL()
                ampl.read(str(mod_path))
                ampl.read_data(str(dat_path))
                ampl.option["solver"] = solver_choice
                ampl.solve()

                # Resultado
                obj_val = ampl.get_objective(ej["objetivo"]).value()

                st.success("### ✅ Solución óptima encontrada")
                st.metric(
                    f"Valor objetivo  Z*  ({ej['objetivo']})",
                    f"{obj_val:.2f}",
                )

                # Variables con valor positivo
                st.markdown("### 📌 Variables activas (valor ≠ 0)")
                variables_activas = []
                for var_name, var_obj in ampl.get_variables():
                    df = var_obj.get_values().to_pandas()
                    if not df.empty:
                        val_col = df.columns[-1]
                        activas = df[df[val_col].abs() > 1e-6]
                        if not activas.empty:
                            variables_activas.append((var_name, activas))

                if variables_activas:
                    for var_name, df in variables_activas:
                        st.markdown(f"**Variable `{var_name}`**")
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("Sin variables activas (todas en cero).")

                # Interpretación
                st.markdown("### 💡 Interpretación")
                if "ruta" in ej["tipo"].lower() and "más corta" in ej["tipo"].lower():
                    st.info(
                        f"Las variables `x[i,j] = 1` indican los **arcos que pertenecen "
                        f"a la ruta óptima**. El tiempo total mínimo es **{obj_val:.0f} minutos**."
                    )
                elif "cpm" in ej["tipo"].lower() or "más larga" in ej["tipo"].lower():
                    st.info(
                        f"La **duración mínima del proyecto** es **{obj_val:.0f} días**. "
                        f"Las actividades del camino crítico son las que NO pueden atrasarse "
                        f"sin retrasar todo el proyecto."
                    )

        except Exception as e:
            st.error(f"Error al resolver: {e}")
            st.exception(e)

# ─── FOOTER ────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "II-1122 Modelos de Optimización Industrial · "
    "Prof. David Benavides · UCR Sede Alajuela · I-2026 · "
    "[GitHub](https://github.com/davidben17-arch/Redes)"
)
