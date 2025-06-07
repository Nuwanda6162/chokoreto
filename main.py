
import streamlit as st
import sqlite3
import pandas as pd

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

# Carga rápida de nueva materia prima
st.header("➕ Cargar nueva Materia Prima")

with st.form("form_mp"):
    nombre = st.text_input("Nombre de la materia prima")
    unidad = st.selectbox("Unidad", ["unidad", "g", "kg", "cc", "ml", "otro"])
    precio = st.number_input("Precio por unidad", min_value=0.0, step=0.01)
    fecha = st.date_input("Fecha de actualización")

    # Selector encadenado categoría → subcategoría
    cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    selected_cat = st.selectbox("Categoría", cat_options["nombre"].tolist())

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
        subcat_nombre = st.selectbox("Subcategoría", list(subcat_dict.keys()))
        subcat_id = subcat_dict[subcat_nombre]

    submitted = st.form_submit_button("Guardar")

    if submitted and nombre and subcat_id:
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
