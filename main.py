
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

conn = sqlite3.connect("chokoreto_costos_completa.db", check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(page_title="Chokoreto App", layout="wide")
st.sidebar.title("Menú")
seccion = st.sidebar.radio("Ir a:", [
    "📋 Ver Materias Primas",
    "➕ Cargar Materia Prima",
    "✏️ Editar Materia Prima",
    "🧱 Crear Categorías/Subcategorías",
    "🧪 Crear Producto",
    "🍫 Agregar Ingredientes a Producto"
])

cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)

# --- OMITIDO: otras secciones previas por brevedad (quedan igual) ---

# ✏️ Editar Materia Prima
elif seccion == "✏️ Editar Materia Prima":
    st.title("✏️ Editar Materia Prima")
    cat_filtro = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_filtro_edit")
    subcat_filtro_query = "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?"
    subcats_filtradas = pd.read_sql_query(subcat_filtro_query, conn, params=(cat_filtro,))
    subcat_dict_filtro = dict(zip(subcats_filtradas["nombre"], subcats_filtradas["id"]))
    if subcat_dict_filtro:
        subcat_sel_nombre = st.selectbox("Subcategoría", list(subcat_dict_filtro.keys()), key="subcat_filtro_edit")
        subcat_sel_id = subcat_dict_filtro[subcat_sel_nombre]
        mp_filtradas = pd.read_sql_query("SELECT id, nombre FROM materias_primas WHERE subcategoria_id = ? ORDER BY nombre", conn, params=(subcat_sel_id,))
        if not mp_filtradas.empty:
            mp_dict = dict(zip(mp_filtradas["nombre"], mp_filtradas["id"]))
            mp_nombre_sel = st.selectbox("Seleccioná una materia prima", list(mp_dict.keys()), key="editar_mp_sel")
            mp_id_sel = mp_dict[mp_nombre_sel]
            mp_data = pd.read_sql_query("SELECT * FROM materias_primas WHERE id = ?", conn, params=(mp_id_sel,)).iloc[0]

            opciones_unidad = ["unidad", "g", "kg", "cc", "ml", "otro"]
            unidad_actual = str(mp_data["unidad"]).lower().strip()
            index_unidad = opciones_unidad.index(unidad_actual) if unidad_actual in opciones_unidad else opciones_unidad.index("otro")

            new_unidad = st.selectbox("Unidad (edición)", opciones_unidad, index=index_unidad, key="unidad_edicion")
            new_precio = st.number_input("Precio por unidad (edición)", value=mp_data["precio_por_unidad"], step=0.01, key="precio_edicion")

            if st.button("Actualizar materia prima", key="actualizar_mp"):
                hoy = date.today()
                cursor.execute("UPDATE materias_primas SET unidad = ?, precio_por_unidad = ?, fecha_actualizacion = ? WHERE id = ?", (new_unidad, new_precio, str(hoy), mp_id_sel))
                conn.commit()
                st.success("Materia prima actualizada correctamente")
        else:
            st.info("No hay materias primas para esa subcategoría.")
    else:
        st.warning("No hay subcategorías para esta categoría.")
