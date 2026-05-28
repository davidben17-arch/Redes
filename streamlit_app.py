"""
REDES UCR · II-1122 Modelos de Optimización Industrial
=======================================================
App Streamlit INTERACTIVA — Modelos de Redes (Clase 12)
Prof. David Benavides · UCR Sede Alajuela · I-2026

Funciones:
  • Tabla de arcos editable (cambiar nombres, tiempos, agregar/borrar filas)
  • Grafo de la red con la ruta óptima resaltada
  • Comparación de rutas alternativas lado a lado
  • Resolución en vivo con AMPL (HiGHS / CBC)
"""

import streamlit as st
from amplpy import AMPL
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import tempfile, os

matplotlib.use("Agg")

# ─── CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="Redes UCR — II-1122", page_icon="🕸️", layout="wide")

NAVY = "#003366"
BAC_RED = "#D52B1E"
LIGHT = "#cfe0f0"

# ═══════════════════════════════════════════════════════════
#  MODELOS AMPL EMBEBIDOS
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

# ═══════════════════════════════════════════════════════════
#  DATOS INICIALES (como DataFrames editables)
# ═══════════════════════════════════════════════════════════
ARCOS_WALMART = pd.DataFrame([
    ["Coyol", "SanJose", 35], ["SanJose", "Cartago", 40],
    ["Cartago", "CerroMuerte", 90], ["CerroMuerte", "SanIsidro", 70],
    ["SanIsidro", "PerezZ", 25], ["Coyol", "Atenas", 20],
    ["Atenas", "Orotina", 25], ["Orotina", "Jaco", 35],
    ["Jaco", "Parrita", 40], ["Parrita", "Quepos", 25],
    ["Quepos", "Dominical", 45], ["Dominical", "PerezZ", 40],
    ["Coyol", "Esparza", 50], ["Esparza", "Orotina", 30],
    ["Cartago", "SanIsidro", 155],
], columns=["Desde", "Hasta", "Tiempo"])

ARCOS_DOSPINOS = pd.DataFrame([
    ["Coyol", "Atenas", 15], ["Atenas", "Esparza", 30],
    ["Esparza", "Miramar", 20], ["Miramar", "Canas", 45],
    ["Canas", "Bagaces", 20], ["Bagaces", "Liberia", 25],
    ["Esparza", "Puntarenas", 15], ["Puntarenas", "Caldera", 15],
    ["Caldera", "Miramar", 25], ["Canas", "Tilaran", 30],
    ["Tilaran", "Liberia", 55], ["Canas", "Nicoya", 50],
    ["Nicoya", "Liberia", 60], ["Esparza", "Canas", 80],
], columns=["Desde", "Hasta", "Tiempo"])

ARCOS_CPM = pd.DataFrame([
    ["Inicio", "finA", 5], ["Inicio", "finB", 3],
    ["finA", "finC", 8], ["finB", "finD", 6],
    ["finC", "finE", 4], ["finC", "finF", 7],
    ["finD", "finF", 7], ["finE", "finG", 3],
    ["finF", "Fin", 4], ["finG", "Fin", 4],
], columns=["Desde", "Hasta", "Duracion"])

EJERCICIOS = {
    "Ejercicio 1 · Walmart CR — Ruta más corta": {
        "tipo": "ruta", "arcos": ARCOS_WALMART,
        "origen": "Coyol", "destino": "PerezZ", "unidad": "minutos",
        "descripcion": "Distribución desde el CEDI Walmart en Coyol (Alajuela) "
                       "al MaxiPalí de Pérez Zeledón. Dos rutas paralelas: "
                       "GAM/Cerro de la Muerte vs. Pacífico/Costanera.",
        "esperado": "230 minutos (ruta Pacífico/Costanera)",
    },
    "Ejercicio 2 · Dos Pinos — Ruta más corta": {
        "tipo": "ruta", "arcos": ARCOS_DOSPINOS,
        "origen": "Coyol", "destino": "Liberia", "unidad": "minutos",
        "descripcion": "Despacho refrigerado desde la planta Dos Pinos en Coyol "
                       "al AutoMercado de Liberia. Red del Pacífico Norte.",
        "esperado": "155 minutos (Interamericana Norte directa)",
    },
    "Ejercicio 3 · CPM Proyecto — Camino crítico": {
        "tipo": "cpm", "arcos": ARCOS_CPM,
        "origen": "Inicio", "destino": "Fin", "unidad": "días",
        "descripcion": "Proyecto industrial con 8 actividades (A-H) y sus "
                       "precedencias. El modelo encuentra el camino más largo "
                       "(crítico): las actividades que no pueden atrasarse.",
        "esperado": "24 días (camino A→C→F→H)",
    },
}

# ═══════════════════════════════════════════════════════════
#  SOLVER
# ═══════════════════════════════════════════════════════════
def resolver_ruta(df, origen, destino, solver):
    nodos = sorted(set(df["Desde"]) | set(df["Hasta"]))
    datos = f"set NODOS := {' '.join(nodos)} ;\n"
    datos += f"param origen := {origen};\nparam destino := {destino};\n"
    datos += "param: ARCOS: tiempo :=\n"
    for _, r in df.iterrows():
        datos += f"  {r['Desde']} {r['Hasta']} {r['Tiempo']}\n"
    datos += ";\n"
    with tempfile.TemporaryDirectory() as d:
        mp, dp = os.path.join(d, "m.mod"), os.path.join(d, "d.dat")
        open(mp, "w").write(MODELO_RUTA); open(dp, "w").write(datos)
        a = AMPL(); a.read(mp); a.read_data(dp)
        a.option["solver"] = solver; a.solve()
        obj = a.get_objective("Tiempo_total").value()
        xdf = a.get_variable("x").get_values().to_pandas()
        col = xdf.columns[-1]
        usados = [(i, j) for (i, j), v in xdf[col].items() if v > 0.5]
        return obj, usados, nodos

def resolver_cpm(df, inicio, fin, solver):
    eventos = sorted(set(df["Desde"]) | set(df["Hasta"]))
    datos = f"set EVENTOS := {' '.join(eventos)} ;\n"
    datos += f"param inicio := {inicio};\nparam fin := {fin};\n"
    datos += "param: PRECEDENCIAS: duracion :=\n"
    for _, r in df.iterrows():
        datos += f"  {r['Desde']} {r['Hasta']} {r['Duracion']}\n"
    datos += ";\n"
    with tempfile.TemporaryDirectory() as d:
        mp, dp = os.path.join(d, "m.mod"), os.path.join(d, "d.dat")
        open(mp, "w").write(MODELO_CPM); open(dp, "w").write(datos)
        a = AMPL(); a.read(mp); a.read_data(dp)
        a.option["solver"] = solver; a.solve()
        obj = a.get_objective("Duracion_proyecto").value()
        tdf = a.get_variable("t").get_values().to_pandas()
        col = tdf.columns[-1]
        tiempos = {k: v for k, v in tdf[col].items()}
        # Camino crítico = camino MÁS LARGO de inicio a fin.
        # Se construye sobre el subgrafo de arcos sin holgura
        # (t[j] == t[i] + dur) y se toma el de mayor duración total.
        Gc = nx.DiGraph()
        for _, r in df.iterrows():
            i, j, dur = r["Desde"], r["Hasta"], r["Duracion"]
            if abs(tiempos[j] - tiempos[i] - dur) < 1e-6:
                Gc.add_edge(i, j, peso=dur)
        criticos = []
        try:
            mejor, mejor_costo = None, -1
            for path in nx.all_simple_paths(Gc, inicio, fin):
                costo = sum(Gc[path[k]][path[k+1]]["peso"]
                            for k in range(len(path)-1))
                if costo > mejor_costo:
                    mejor, mejor_costo = path, costo
            if mejor:
                criticos = [(mejor[k], mejor[k+1]) for k in range(len(mejor)-1)]
        except Exception:
            pass
        return obj, criticos, eventos, tiempos

# ═══════════════════════════════════════════════════════════
#  GRAFO
# ═══════════════════════════════════════════════════════════
def dibujar_grafo(df, usados, origen, destino, peso_col, titulo):
    G = nx.DiGraph()
    for _, r in df.iterrows():
        G.add_edge(r["Desde"], r["Hasta"], peso=r[peso_col])
    fig, ax = plt.subplots(figsize=(11, 7))
    try:
        pos = nx.kamada_kawai_layout(G)
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=1.5)
    usados_set = {(i, j) for i, j in usados}

    # Colores de nodos
    ncolors = []
    for n in G.nodes():
        if n == origen: ncolors.append(BAC_RED)
        elif n == destino: ncolors.append("#1a7a3c")
        else: ncolors.append(NAVY)

    # Aristas: ruta óptima resaltada vs. resto
    e_opt = [(u, v) for u, v in G.edges() if (u, v) in usados_set]
    e_rest = [(u, v) for u, v in G.edges() if (u, v) not in usados_set]
    nx.draw_networkx_edges(G, pos, edgelist=e_rest, edge_color="#bbbbbb",
                           width=1.3, arrows=True, arrowsize=14,
                           connectionstyle="arc3,rad=0.06", ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=e_opt, edge_color=BAC_RED,
                           width=3.5, arrows=True, arrowsize=20,
                           connectionstyle="arc3,rad=0.06", ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=ncolors, node_size=1300,
                           edgecolors="white", linewidths=2, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white",
                            font_weight="bold", ax=ax)
    elabels = {(u, v): G[u][v]["peso"] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=elabels, font_size=8,
                                 bbox=dict(boxstyle="round,pad=0.2",
                                           fc="white", ec="none", alpha=0.8), ax=ax)
    ax.set_title(titulo, fontsize=13, fontweight="bold", color=NAVY)
    ax.axis("off")
    plt.tight_layout()
    return fig

# ═══════════════════════════════════════════════════════════
#  CAMINOS ALTERNATIVOS (enumerar rutas simples)
# ═══════════════════════════════════════════════════════════
def rutas_alternativas(df, origen, destino, peso_col, max_rutas=6):
    G = nx.DiGraph()
    for _, r in df.iterrows():
        G.add_edge(r["Desde"], r["Hasta"], peso=r[peso_col])
    rutas = []
    try:
        for path in nx.all_simple_paths(G, origen, destino, cutoff=15):
            costo = sum(G[path[k]][path[k+1]]["peso"] for k in range(len(path)-1))
            rutas.append((path, costo))
    except Exception:
        return []
    rutas.sort(key=lambda x: x[1])
    return rutas[:max_rutas]

# ═══════════════════════════════════════════════════════════
#  ESTILO + HEADER
# ═══════════════════════════════════════════════════════════
st.markdown(f"""
<style>
.main-header {{ background: linear-gradient(135deg,{NAVY} 0%,#0066a2 100%);
    padding:1.3rem 1.8rem; border-radius:10px; margin-bottom:1.2rem; color:white; }}
.main-header h1 {{ margin:0; font-size:1.5rem; }}
.main-header p  {{ margin:0.3rem 0 0; opacity:0.9; font-size:0.85rem; }}
.tipo-badge {{ display:inline-block; background:{NAVY}; color:white;
    padding:0.2rem 0.7rem; border-radius:12px; font-size:0.78rem;
    font-weight:600; margin-bottom:0.4rem; }}
[data-testid="stSidebar"] {{ background-color:#f5f8fc; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="main-header">
    <h1>🕸️ Modelos de Redes — Laboratorio Interactivo</h1>
    <p>II-1122 Modelos de Optimización Industrial · Clase 12 · Prof. David Benavides · UCR Sede Alajuela · I-2026</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📚 Ejercicios")
    seleccion = st.selectbox("Elegí un ejercicio:", list(EJERCICIOS.keys()),
                             label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### ⚙️ Solver")
    solver_choice = st.radio("Motor:", ["highs", "cbc"], index=0)
    st.markdown("---")
    st.caption("💡 Editá la tabla de arcos, agregá o borrá filas, y volvé a "
               "resolver para ver cómo cambia la ruta óptima.")
    if st.button("🔄 Restaurar datos originales"):
        for k in list(st.session_state.keys()):
            if k.startswith("tabla_"):
                del st.session_state[k]
        st.rerun()

ej = EJERCICIOS[seleccion]
es_ruta = ej["tipo"] == "ruta"
peso_col = "Tiempo" if es_ruta else "Duracion"

# ─── ENCABEZADO EJERCICIO ──────────────────────────────────
st.markdown(f'<div class="tipo-badge">{"Ruta más corta" if es_ruta else "CPM · Camino crítico"}</div>',
            unsafe_allow_html=True)
st.markdown(f"## {seleccion.split('· ', 1)[1]}")
st.write(ej["descripcion"])

# ─── ORIGEN / DESTINO EDITABLES ────────────────────────────
key_tabla = f"tabla_{seleccion}"
if key_tabla not in st.session_state:
    st.session_state[key_tabla] = ej["arcos"].copy()

c1, c2 = st.columns(2)
nodos_actuales = sorted(set(st.session_state[key_tabla]["Desde"]) |
                        set(st.session_state[key_tabla]["Hasta"]))
with c1:
    origen = st.selectbox("🟥 Origen" if es_ruta else "🟥 Inicio",
                          nodos_actuales,
                          index=nodos_actuales.index(ej["origen"])
                          if ej["origen"] in nodos_actuales else 0)
with c2:
    destino = st.selectbox("🟩 Destino" if es_ruta else "🟩 Fin",
                           nodos_actuales,
                           index=nodos_actuales.index(ej["destino"])
                           if ej["destino"] in nodos_actuales else len(nodos_actuales)-1)

# ─── TABLA EDITABLE ────────────────────────────────────────
st.markdown(f"### ✏️ Arcos de la red ({peso_col.lower()})")
st.caption("Editá celdas, agregá filas con **+** abajo, o borralas seleccionando "
           "la fila. Podés cambiar nombres de nodos y valores.")
edited = st.data_editor(
    st.session_state[key_tabla],
    num_rows="dynamic",
    use_container_width=True,
    key=f"editor_{seleccion}",
    column_config={
        "Desde": st.column_config.TextColumn("Desde", required=True),
        "Hasta": st.column_config.TextColumn("Hasta", required=True),
        peso_col: st.column_config.NumberColumn(peso_col, min_value=0, required=True),
    },
)
st.session_state[key_tabla] = edited

st.markdown(f"**Resultado esperado (datos originales):** `{ej['esperado']}`")
st.markdown("---")

# ─── RESOLVER ──────────────────────────────────────────────
if st.button("🚀 Resolver y dibujar", type="primary", use_container_width=True):
    df = st.session_state[key_tabla].dropna()
    df = df[(df["Desde"] != "") & (df["Hasta"] != "")]
    try:
        if es_ruta:
            obj, usados, nodos = resolver_ruta(df, origen, destino, solver_choice)
            st.success(f"### ✅ Ruta óptima: {obj:.0f} {ej['unidad']}")
            # Reconstruir orden de la ruta
            sig = {i: j for i, j in usados}
            ruta, cur = [origen], origen
            while cur in sig and len(ruta) < len(nodos) + 1:
                cur = sig[cur]; ruta.append(cur)
            st.markdown("**Camino óptimo:** " + " → ".join(ruta))
            fig = dibujar_grafo(df, usados, origen, destino, peso_col,
                                f"Ruta óptima: {' → '.join(ruta)}  ({obj:.0f} {ej['unidad']})")
            st.pyplot(fig)
        else:
            obj, criticos, eventos, tiempos = resolver_cpm(df, origen, destino, solver_choice)
            st.success(f"### ✅ Duración del proyecto: {obj:.0f} {ej['unidad']}")
            crit_nodos = sorted(set([c[0] for c in criticos] + [c[1] for c in criticos]),
                                key=lambda n: tiempos[n])
            st.markdown("**Camino crítico:** " + " → ".join(crit_nodos))
            fig = dibujar_grafo(df, criticos, origen, destino, peso_col,
                                f"Camino crítico ({obj:.0f} {ej['unidad']})")
            st.pyplot(fig)

        # ─── COMPARACIÓN DE RUTAS ALTERNATIVAS ──────────────
        if es_ruta:
            st.markdown("### 🔀 Comparación de rutas alternativas")
            alts = rutas_alternativas(df, origen, destino, peso_col)
            if alts:
                comp = pd.DataFrame([
                    {"#": i+1, "Ruta": " → ".join(p),
                     f"Total ({ej['unidad']})": c,
                     "Óptima": "✅" if i == 0 else ""}
                    for i, (p, c) in enumerate(alts)
                ])
                st.dataframe(comp, use_container_width=True, hide_index=True)
                st.bar_chart(comp.set_index("Ruta")[f"Total ({ej['unidad']})"])
            else:
                st.info("No se encontraron rutas alternativas simples.")
    except Exception as e:
        st.error(f"Error al resolver: {e}")
        st.caption("Revisá que origen y destino existan en la tabla y que haya un "
                   "camino conectado entre ellos.")

st.markdown("---")
st.caption("II-1122 · Prof. David Benavides · UCR Sede Alajuela · I-2026 · "
           "[GitHub](https://github.com/davidben17-arch/Redes)")
