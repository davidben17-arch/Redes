"""
REDES UCR · II-1122 Modelos de Optimización Industrial
=======================================================
App Streamlit INTERACTIVA — Modelos de Redes (Clase 12)
Prof. David Benavides · UCR Sede Alajuela · I-2026

• Ruta más corta: tabla de arcos editable + grafo por etapas
  (izquierda→derecha) con ruta óptima en rojo + comparación de rutas.
• CPM: tabla de tareas (Tarea/Descripción/Duración/Predecesores)
  + diagrama de Gantt con ruta crítica en rojo + tabla ES/EF/LS/LF.
"""

import streamlit as st
from amplpy import AMPL
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import tempfile, os

# ─── CONFIG ────────────────────────────────────────────────
st.set_page_config(page_title="Redes UCR — II-1122", page_icon="🕸️", layout="wide")
NAVY = "#003366"; BAC_RED = "#D52B1E"

# ═══════════════════════════════════════════════════════════
#  MODELO AMPL (ruta más corta)
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

# ═══════════════════════════════════════════════════════════
#  DATOS INICIALES
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

# CPM: tareas con predecesores (estructura tipo libro de texto)
TAREAS_CPM = pd.DataFrame([
    ["A", "Diseño y planificación",     5, ""],
    ["B", "Adquisición de materiales",  3, ""],
    ["C", "Fabricación de componentes", 8, "A"],
    ["D", "Preparación del sitio",      6, "B"],
    ["E", "Ensamblaje preliminar",      4, "C"],
    ["F", "Instalación principal",      7, "C,D"],
    ["G", "Pruebas de subsistemas",     3, "E"],
    ["H", "Puesta en marcha final",     4, "F,G"],
], columns=["Tarea", "Descripcion", "Duracion", "Predecesores"])

EJERCICIOS = {
    "Ejercicio 1 · Walmart CR — Ruta más corta": {
        "tipo": "ruta", "datos": ARCOS_WALMART,
        "origen": "Coyol", "destino": "PerezZ", "unidad": "minutos",
        "descripcion": "Distribución desde el CEDI Walmart en Coyol (Alajuela) "
                       "al MaxiPalí de Pérez Zeledón. Dos rutas paralelas: "
                       "GAM/Cerro de la Muerte vs. Pacífico/Costanera.",
        "esperado": "230 minutos (ruta Pacífico/Costanera)",
    },
    "Ejercicio 2 · Dos Pinos — Ruta más corta": {
        "tipo": "ruta", "datos": ARCOS_DOSPINOS,
        "origen": "Coyol", "destino": "Liberia", "unidad": "minutos",
        "descripcion": "Despacho refrigerado desde la planta Dos Pinos en Coyol "
                       "al AutoMercado de Liberia. Red del Pacífico Norte.",
        "esperado": "155 minutos (Interamericana Norte directa)",
    },
    "Ejercicio 3 · CPM Proyecto — Camino crítico": {
        "tipo": "cpm", "datos": TAREAS_CPM,
        "unidad": "días",
        "descripcion": "Proyecto industrial con 8 actividades (A–H). Cada tarea "
                       "tiene una duración y predecesores. El método del camino "
                       "crítico (CPM) calcula la duración mínima del proyecto y "
                       "qué tareas no pueden atrasarse (holgura cero).",
        "esperado": "24 días (ruta crítica A→C→F→H)",
    },
}

# ═══════════════════════════════════════════════════════════
#  SOLVER — RUTA MÁS CORTA (AMPL)
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

# ═══════════════════════════════════════════════════════════
#  CPM — Forward / Backward pass (ES, EF, LS, LF, holgura)
# ═══════════════════════════════════════════════════════════
def calcular_cpm(df):
    tareas = {}
    for _, r in df.iterrows():
        t = str(r["Tarea"]).strip()
        if not t:
            continue
        preds = [p.strip() for p in str(r["Predecesores"]).split(",") if p.strip()]
        tareas[t] = {"desc": str(r["Descripcion"]), "dur": float(r["Duracion"]),
                     "preds": preds, "ES": 0, "EF": 0, "LS": 0, "LF": 0, "holgura": 0}
    # Orden topológico
    orden, visto = [], set()
    def visitar(t):
        if t in visto: return
        for p in tareas[t]["preds"]:
            if p in tareas: visitar(p)
        visto.add(t); orden.append(t)
    for t in list(tareas): visitar(t)
    # Forward (ES, EF)
    for t in orden:
        i = tareas[t]
        i["ES"] = max([tareas[p]["EF"] for p in i["preds"] if p in tareas], default=0)
        i["EF"] = i["ES"] + i["dur"]
    proj = max((i["EF"] for i in tareas.values()), default=0)
    # Sucesores
    sucs = {t: [] for t in tareas}
    for t in tareas:
        for p in tareas[t]["preds"]:
            if p in sucs: sucs[p].append(t)
    # Backward (LF, LS, holgura)
    for t in reversed(orden):
        i = tareas[t]
        i["LF"] = proj if not sucs[t] else min(tareas[s]["LS"] for s in sucs[t])
        i["LS"] = i["LF"] - i["dur"]
        i["holgura"] = i["LS"] - i["ES"]
    return tareas, proj

# ═══════════════════════════════════════════════════════════
#  GRAFO POR ETAPAS (ruta más corta) — izquierda → derecha
# ═══════════════════════════════════════════════════════════
def _posiciones_por_etapas(G, origen, destino):
    capa = {origen: 0}
    nodos = list(G.nodes())
    for _ in range(len(nodos) + 1):
        cambiado = False
        for u, v in G.edges():
            base = capa.get(u, 0)
            if v not in capa or capa[v] < base + 1:
                capa[v] = base + 1; cambiado = True
        if not cambiado: break
    for n in nodos:
        capa.setdefault(n, max(capa.values(), default=0) + 1)
    capa[destino] = max(capa.values())
    cols = defaultdict(list)
    for n, c in capa.items(): cols[c].append(n)
    pos = {}
    for c, ns in cols.items():
        ns = sorted(ns); k = len(ns)
        for idx, n in enumerate(ns):
            y = 0 if k == 1 else 1 - 2 * idx / (k - 1)
            pos[n] = (c, y)
    return pos

def dibujar_grafo_ruta(df, usados, origen, destino, titulo):
    G = nx.DiGraph()
    for _, r in df.iterrows():
        G.add_edge(r["Desde"], r["Hasta"], peso=r["Tiempo"])
    pos = _posiciones_por_etapas(G, origen, destino)
    ancho = max(8, (max(p[0] for p in pos.values()) + 1) * 1.8)
    fig, ax = plt.subplots(figsize=(ancho, 6.5))
    us = {(i, j) for i, j in usados}
    ncolors = [BAC_RED if n == origen else "#1a7a3c" if n == destino else NAVY
               for n in G.nodes()]
    e_opt = [(u, v) for u, v in G.edges() if (u, v) in us]
    e_rest = [(u, v) for u, v in G.edges() if (u, v) not in us]
    nx.draw_networkx_edges(G, pos, edgelist=e_rest, edge_color="#c8c8c8", width=1.2,
                           arrows=True, arrowsize=13, connectionstyle="arc3,rad=0.08",
                           node_size=1500, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=e_opt, edge_color=BAC_RED, width=3.5,
                           arrows=True, arrowsize=20, connectionstyle="arc3,rad=0.08",
                           node_size=1500, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=ncolors, node_size=1500,
                           edgecolors="white", linewidths=2, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7.5, font_color="white",
                            font_weight="bold", ax=ax)
    el = {(u, v): G[u][v]["peso"] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=el, font_size=7.5, rotate=False,
                                 bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                           ec="#dddddd", alpha=0.9), ax=ax)
    ax.set_title(titulo, fontsize=12, fontweight="bold", color=NAVY, pad=15)
    ax.margins(0.12); ax.axis("off"); plt.tight_layout()
    return fig

# ═══════════════════════════════════════════════════════════
#  DIAGRAMA DE GANTT (CPM) — barras en ES, crítica en rojo
# ═══════════════════════════════════════════════════════════
def dibujar_gantt(tareas, proj):
    orden = sorted(tareas.keys())
    n = len(orden)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.7 * n + 1.5)))
    for idx, t in enumerate(orden):
        i = tareas[t]
        y = n - idx
        crit = abs(i["holgura"]) < 1e-6
        color = BAC_RED if crit else NAVY
        ax.barh(y, i["dur"], left=i["ES"], height=0.55, color=color,
                edgecolor="white", zorder=3)
        if not crit and i["holgura"] > 0:
            ax.barh(y, i["holgura"], left=i["EF"], height=0.55, color="#d8d8d8",
                    edgecolor="white", alpha=0.8, zorder=2)
        ax.text(i["ES"] + i["dur"] / 2, y, f"{i['dur']:.0f}d", ha="center",
                va="center", color="white", fontweight="bold", fontsize=9, zorder=4)
    ax.set_yticks(range(1, n + 1))
    ax.set_yticklabels([f"{t} · {tareas[t]['desc']}" for t in reversed(orden)],
                       fontsize=8.5)
    ax.set_xlabel("Tiempo (días)", fontsize=10, fontweight="bold")
    ax.set_xlim(0, proj + 1.5)
    ax.set_ylim(0.3, n + 1.2)
    ax.axvline(proj, color=BAC_RED, linestyle="--", alpha=0.5, zorder=1)
    ax.text(proj, n + 0.9, f"Fin: {proj:.0f}d", color=BAC_RED, fontsize=9,
            fontweight="bold", ha="center")
    ax.grid(axis="x", alpha=0.3, zorder=0)
    leg = [mpatches.Patch(color=BAC_RED, label="Tarea crítica (holgura 0)"),
           mpatches.Patch(color=NAVY, label="Tarea con holgura"),
           mpatches.Patch(color="#d8d8d8", label="Margen de holgura")]
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=3, fontsize=8, frameon=False)
    ax.set_title(f"Diagrama de Gantt — Camino crítico ({proj:.0f} días)",
                 fontsize=13, fontweight="bold", color=NAVY, pad=12)
    plt.tight_layout()
    return fig

# ═══════════════════════════════════════════════════════════
#  RUTAS ALTERNATIVAS
# ═══════════════════════════════════════════════════════════
def rutas_alternativas(df, origen, destino, max_rutas=8):
    G = nx.DiGraph()
    for _, r in df.iterrows():
        G.add_edge(r["Desde"], r["Hasta"], peso=r["Tiempo"])
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
    st.caption("💡 Editá la tabla, agregá o borrá filas, y volvé a resolver para "
               "ver cómo cambia el resultado.")
    if st.button("🔄 Restaurar datos originales"):
        for k in list(st.session_state.keys()):
            if k.startswith("tabla_"):
                del st.session_state[k]
        st.rerun()

ej = EJERCICIOS[seleccion]
es_ruta = ej["tipo"] == "ruta"

st.markdown(f'<div class="tipo-badge">{"Ruta más corta" if es_ruta else "CPM · Camino crítico"}</div>',
            unsafe_allow_html=True)
st.markdown(f"## {seleccion.split('· ', 1)[1]}")
st.write(ej["descripcion"])

key_tabla = f"tabla_{seleccion}"
if key_tabla not in st.session_state:
    st.session_state[key_tabla] = ej["datos"].copy()

# ═══════════════════════════════════════════════════════════
#  CASO A: RUTA MÁS CORTA
# ═══════════════════════════════════════════════════════════
if es_ruta:
    nodos_actuales = sorted(set(st.session_state[key_tabla]["Desde"]) |
                            set(st.session_state[key_tabla]["Hasta"]))
    c1, c2 = st.columns(2)
    with c1:
        origen = st.selectbox("🟥 Origen", nodos_actuales,
                              index=nodos_actuales.index(ej["origen"])
                              if ej["origen"] in nodos_actuales else 0)
    with c2:
        destino = st.selectbox("🟩 Destino", nodos_actuales,
                               index=nodos_actuales.index(ej["destino"])
                               if ej["destino"] in nodos_actuales else len(nodos_actuales)-1)

    st.markdown("### ✏️ Arcos de la red (tiempo)")
    st.caption("Editá celdas, agregá filas con **+**, o borralas. Podés cambiar "
               "nombres de nodos y tiempos.")
    edited = st.data_editor(
        st.session_state[key_tabla], num_rows="dynamic", use_container_width=True,
        key=f"editor_{seleccion}",
        column_config={
            "Desde": st.column_config.TextColumn("Desde", required=True),
            "Hasta": st.column_config.TextColumn("Hasta", required=True),
            "Tiempo": st.column_config.NumberColumn("Tiempo", min_value=0, required=True),
        })
    st.session_state[key_tabla] = edited
    st.markdown(f"**Resultado esperado (datos originales):** `{ej['esperado']}`")
    st.markdown("---")

    if st.button("🚀 Resolver y dibujar", type="primary", use_container_width=True):
        df = st.session_state[key_tabla].dropna()
        df = df[(df["Desde"] != "") & (df["Hasta"] != "")]
        try:
            obj, usados, nodos = resolver_ruta(df, origen, destino, solver_choice)
            st.success(f"### ✅ Ruta óptima: {obj:.0f} {ej['unidad']}")
            sig = {i: j for i, j in usados}
            ruta, cur = [origen], origen
            while cur in sig and len(ruta) < len(nodos) + 1:
                cur = sig[cur]; ruta.append(cur)
            st.markdown("**Camino óptimo (por etapas):**")
            st.markdown("  ".join(f"**{k}.** {n}" + (" →" if k < len(ruta) else "")
                                  for k, n in enumerate(ruta, 1)))
            st.pyplot(dibujar_grafo_ruta(df, usados, origen, destino,
                      f"Ruta óptima ({obj:.0f} {ej['unidad']})"))

            st.markdown("### 🔀 Comparación de rutas alternativas")
            st.caption("Todas las rutas posibles, ordenadas de menor a mayor. La #1 es la óptima.")
            alts = rutas_alternativas(df, origen, destino)
            if alts:
                optimo = alts[0][1]
                comp = pd.DataFrame([{
                    "Ruta #": i + 1, "Secuencia": " → ".join(p),
                    "Etapas": len(p) - 1, f"Total ({ej['unidad']})": int(c),
                    "Diferencia": "óptima" if i == 0 else f"+{int(c - optimo)}",
                    "": "🟢" if i == 0 else "",
                } for i, (p, c) in enumerate(alts)])
                st.dataframe(comp, use_container_width=True, hide_index=True)
                chart_df = pd.DataFrame({"Ruta": [f"#{i+1}" for i in range(len(alts))],
                                         ej['unidad'].capitalize(): [int(c) for _, c in alts]})
                st.bar_chart(chart_df.set_index("Ruta"), color=NAVY)
            else:
                st.info(f"No hay rutas simples entre **{origen}** y **{destino}**.")
        except Exception as e:
            st.error(f"Error al resolver: {e}")
            st.caption("Verificá que origen y destino estén conectados.")

# ═══════════════════════════════════════════════════════════
#  CASO B: CPM (GANTT)
# ═══════════════════════════════════════════════════════════
else:
    st.markdown("### ✏️ Tareas del proyecto")
    st.caption("Columnas: **Tarea** (letra), **Descripción**, **Duración** (días) y "
               "**Predecesores** (letras separadas por coma; dejá vacío si no tiene). "
               "Editá, agregá o borrá filas y volvé a resolver.")
    edited = st.data_editor(
        st.session_state[key_tabla], num_rows="dynamic", use_container_width=True,
        key=f"editor_{seleccion}",
        column_config={
            "Tarea": st.column_config.TextColumn("Tarea", required=True, width="small"),
            "Descripcion": st.column_config.TextColumn("Descripción", width="large"),
            "Duracion": st.column_config.NumberColumn("Duración", min_value=0, required=True),
            "Predecesores": st.column_config.TextColumn("Predecesores", width="medium",
                            help="Ej: A,C  (vacío = no tiene predecesores)"),
        })
    st.session_state[key_tabla] = edited
    st.markdown(f"**Resultado esperado (datos originales):** `{ej['esperado']}`")
    st.markdown("---")

    if st.button("🚀 Calcular camino crítico y Gantt", type="primary",
                 use_container_width=True):
        df = st.session_state[key_tabla].dropna(subset=["Tarea", "Duracion"])
        df = df[df["Tarea"].astype(str).str.strip() != ""]
        try:
            tareas, proj = calcular_cpm(df)
            criticas = [t for t in tareas if abs(tareas[t]["holgura"]) < 1e-6]
            st.success(f"### ✅ Duración del proyecto: {proj:.0f} {ej['unidad']}")
            st.markdown("**Tareas críticas (holgura 0):** " +
                        " · ".join(f"**{t}**" for t in sorted(criticas)))

            st.pyplot(dibujar_gantt(tareas, proj))

            st.markdown("### 📋 Tabla del método del camino crítico")
            st.caption("ES = inicio temprano · EF = fin temprano · LS = inicio tardío "
                       "· LF = fin tardío · Holgura = margen de atraso permitido.")
            tabla = pd.DataFrame([{
                "Tarea": t, "Descripción": tareas[t]["desc"],
                "Dur": int(tareas[t]["dur"]),
                "Predec.": ", ".join(tareas[t]["preds"]) if tareas[t]["preds"] else "—",
                "ES": int(tareas[t]["ES"]), "EF": int(tareas[t]["EF"]),
                "LS": int(tareas[t]["LS"]), "LF": int(tareas[t]["LF"]),
                "Holgura": int(tareas[t]["holgura"]),
                "Crítica": "🔴 Sí" if abs(tareas[t]["holgura"]) < 1e-6 else "",
            } for t in sorted(tareas)])
            st.dataframe(tabla, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error al calcular: {e}")
            st.caption("Verificá que los predecesores existan como tareas y que no "
                       "haya ciclos (una tarea no puede depender de sí misma).")

st.markdown("---")
st.caption("II-1122 · Prof. David Benavides · UCR Sede Alajuela · I-2026 · "
           "[GitHub](https://github.com/davidben17-arch/Redes)")
