
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

conn = sqlite3.connect("chokoreto_costos.db", check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(page_title="Chokoreto App", layout="wide")
st.sidebar.title("Menú")
seccion = st.sidebar.radio("Ir a:", [
    "📋 Ver Materias Primas",
    "➕ Cargar Materia Prima",
    "✏️ Editar Materia Prima"
])

cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)

if seccion == "📋 Ver Materias Primas":
    st.title("📋 Materias Primas")
    if not cat_options.empty:
        cat_filtro_tabla = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_filtro_tabla")
        subcats_tabla = pd.read_sql_query("SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?", conn, params=(cat_filtro_tabla,))
        subcat_dict_tabla = dict(zip(subcats_tabla["nombre"], subcats_tabla["id"]))
        if subcat_dict_tabla:
            subcat_tabla_nombre = st.selectbox("Filtrar por Subcategoría", list(subcat_dict_tabla.keys()), key="subcat_filtro_tabla")
            subcat_tabla_id = subcat_dict_tabla[subcat_tabla_nombre]
            query_mp = """
            SELECT mp.id, mp.nombre, mp.unidad, mp.precio_por_unidad, mp.fecha_actualizacion,
                   sub.nombre AS subcategoria, cat.nombre AS categoria
            FROM materias_primas mp
            LEFT JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
            LEFT JOIN categorias_mp cat ON sub.categoria_id = cat.id
            WHERE sub.id = ?
            """
            materias_primas = pd.read_sql_query(query_mp, conn, params=(subcat_tabla_id,))
            st.dataframe(materias_primas)

elif seccion == "➕ Cargar Materia Prima":
    st.title("➕ Cargar nueva Materia Prima")
    nombre = st.text_input("Nombre")
    unidad = st.selectbox("Unidad", ["unidad", "g", "kg", "cc", "ml", "otro"], key="unidad_nueva")
    precio = st.number_input("Precio por unidad", min_value=0.0, step=0.01, key="precio_nuevo")
    fecha = st.date_input("Fecha de actualización", key="fecha_nueva")
    selected_cat = st.selectbox("Categoría", cat_options["nombre"].tolist(), key="cat_nueva")
    subcat_query = "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?"
    filtered_subcats = pd.read_sql_query(subcat_query, conn, params=(selected_cat,))
    subcat_dict = dict(zip(filtered_subcats["nombre"], filtered_subcats["id"]))
    if not filtered_subcats.empty:
        subcat_nombre = st.selectbox("Subcategoría", list(subcat_dict.keys()), key="subcat_nueva")
        subcat_id = subcat_dict[subcat_nombre]
        if st.button("Guardar", key="guardar_nueva") and nombre:
            cursor.execute("INSERT INTO materias_primas (nombre, unidad, precio_por_unidad, fecha_actualizacion, subcategoria_id) VALUES (?, ?, ?, ?, ?)",
                           (nombre, unidad, precio, str(fecha), subcat_id))
            conn.commit()
            st.success("Materia prima guardada correctamente")

elif seccion == "✏️ Editar Materia Prima":
    st.title("✏️ Editar Materia Prima")
    if not cat_options.empty:
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
