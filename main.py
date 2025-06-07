
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Conectar a la base SQLite
conn = sqlite3.connect("chokoreto_costos.db", check_same_thread=False)
cursor = conn.cursor()

st.title("📦 Gestor de Costos - Chokoreto Chocolates")

# Mostrar categorías
st.header("Categorías de Materias Primas")
categorias = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
st.dataframe(categorias)

# Mostrar subcategorías
st.header("Subcategorías de Materias Primas")
query = """
SELECT sub.id, sub.nombre, cat.nombre AS categoria
FROM subcategorias_mp sub
JOIN categorias_mp cat ON sub.categoria_id = cat.id
"""
subcategorias = pd.read_sql_query(query, conn)
st.dataframe(subcategorias)

# Carga dinámica de nueva materia prima
st.header("➕ Cargar nueva Materia Prima")

nombre = st.text_input("Nombre de la materia prima")
unidad = st.selectbox("Unidad", ["unidad", "g", "kg", "cc", "ml", "otro"], key="unidad_nueva")
precio = st.number_input("Precio por unidad", min_value=0.0, step=0.01, key="precio_nuevo")
fecha = st.date_input("Fecha de actualización", key="fecha_nueva")

cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
selected_cat = st.selectbox("Categoría", cat_options["nombre"].tolist(), key="cat_nueva")

subcat_query = f"""
SELECT sub.id, sub.nombre
FROM subcategorias_mp sub
JOIN categorias_mp cat ON sub.categoria_id = cat.id
WHERE cat.nombre = ?
"""
filtered_subcats = pd.read_sql_query(subcat_query, conn, params=(selected_cat,))
subcat_dict = dict(zip(filtered_subcats["nombre"], filtered_subcats["id"]))

if filtered_subcats.empty:
    st.warning("No hay subcategorías para esta categoría.")
    subcat_id = None
else:
    subcat_nombre = st.selectbox("Subcategoría", list(subcat_dict.keys()), key="subcat_nueva")
    subcat_id = subcat_dict[subcat_nombre]

if st.button("Guardar", key="guardar_nueva") and nombre and subcat_id:
    cursor.execute("""
        INSERT INTO materias_primas (nombre, unidad, precio_por_unidad, fecha_actualizacion, subcategoria_id)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, unidad, precio, str(fecha), subcat_id))
    conn.commit()
    st.success("Materia prima guardada correctamente")

# Mostrar materias primas
st.header("📋 Materias Primas")
query_mp = """
SELECT mp.id, mp.nombre, mp.unidad, mp.precio_por_unidad, mp.fecha_actualizacion,
       sub.nombre AS subcategoria,
       cat.nombre AS categoria
FROM materias_primas mp
LEFT JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
LEFT JOIN categorias_mp cat ON sub.categoria_id = cat.id
"""
materias_primas = pd.read_sql_query(query_mp, conn)
st.dataframe(materias_primas)

# Editar materia prima existente
st.header("✏️ Editar Materia Prima")

# Selección de categoría y subcategoría para filtrar
cat_filtro = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_filtro_edit")

subcat_filtro_query = f"""
SELECT sub.id, sub.nombre
FROM subcategorias_mp sub
JOIN categorias_mp cat ON sub.categoria_id = cat.id
WHERE cat.nombre = ?
"""
subcats_filtradas = pd.read_sql_query(subcat_filtro_query, conn, params=(cat_filtro,))
subcat_dict_filtro = dict(zip(subcats_filtradas["nombre"], subcats_filtradas["id"]))

if not subcat_dict_filtro:
    st.warning("No hay subcategorías para esta categoría.")
else:
    subcat_sel_nombre = st.selectbox("Filtrar por Subcategoría", list(subcat_dict_filtro.keys()), key="subcat_filtro_edit")
    subcat_sel_id = subcat_dict_filtro[subcat_sel_nombre]

    # Filtrar materias primas por subcategoría seleccionada
    mp_filtradas = pd.read_sql_query(
        "SELECT id, nombre FROM materias_primas WHERE subcategoria_id = ? ORDER BY nombre",
        conn, params=(subcat_sel_id,)
    )

    if mp_filtradas.empty:
        st.info("No hay materias primas para esa subcategoría.")
    else:
        mp_dict = dict(zip(mp_filtradas["nombre"], mp_filtradas["id"]))
        mp_nombre_sel = st.selectbox("Seleccioná una materia prima para editar", list(mp_dict.keys()), key="editar_mp_sel")
        mp_id_sel = mp_dict[mp_nombre_sel]

        mp_data = pd.read_sql_query("SELECT * FROM materias_primas WHERE id = ?", conn, params=(mp_id_sel,)).iloc[0]

        new_unidad = st.selectbox("Unidad (edición)", ["unidad", "g", "kg", "cc", "ml", "otro"], 
                                  index=["unidad", "g", "kg", "cc", "ml", "otro"].index(mp_data["unidad"]) if mp_data["unidad"] in ["unidad", "g", "kg", "cc", "ml", "otro"] else 0,
                                  key="unidad_edicion")
        new_precio = st.number_input("Precio por unidad (edición)", value=mp_data["precio_por_unidad"], step=0.01, key="precio_edicion")

        if st.button("Actualizar materia prima", key="actualizar_mp"):
            hoy = date.today()
            cursor.execute("""
                UPDATE materias_primas
                SET unidad = ?, precio_por_unidad = ?, fecha_actualizacion = ?
                WHERE id = ?
            """, (new_unidad, new_precio, str(hoy), mp_id_sel))
            conn.commit()
            st.success("Materia prima actualizada correctamente")
