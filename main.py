
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Conexión
conn = sqlite3.connect("chokoreto_costos.db", check_same_thread=False)
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

# 📋 Ver Materias Primas
if seccion == "📋 Ver Materias Primas":
    st.title("📋 Materias Primas")
    cat_filtro_tabla = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_filtro_tabla")
    subcats_tabla = pd.read_sql_query("""
    SELECT sub.id, sub.nombre FROM subcategorias_mp sub
    JOIN categorias_mp cat ON sub.categoria_id = cat.id
    WHERE cat.nombre = ?
    """, conn, params=(cat_filtro_tabla,))
    subcat_dict_tabla = dict(zip(subcats_tabla["nombre"], subcats_tabla["id"]))

    if subcat_dict_tabla:
        subcat_tabla_nombre = st.selectbox("Filtrar por Subcategoría", list(subcat_dict_tabla.keys()), key="subcat_filtro_tabla")
        subcat_tabla_id = subcat_dict_tabla[subcat_tabla_nombre]
        query_mp = """
        SELECT mp.id, mp.nombre, mp.unidad, mp.precio_por_unidad, mp.fecha_actualizacion,
               sub.nombre AS subcategoria,
               cat.nombre AS categoria
        FROM materias_primas mp
        LEFT JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
        LEFT JOIN categorias_mp cat ON sub.categoria_id = cat.id
        WHERE sub.id = ?
        """
        materias_primas = pd.read_sql_query(query_mp, conn, params=(subcat_tabla_id,))
        st.dataframe(materias_primas)
    else:
        st.info("No hay subcategorías para esta categoría.")

# ➕ Cargar Materia Prima
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
            new_unidad = st.selectbox("Unidad (edición)", ["unidad", "g", "kg", "cc", "ml", "otro"], index=["unidad", "g", "kg", "cc", "ml", "otro"].index(mp_data["unidad"]), key="unidad_edicion")
            new_precio = st.number_input("Precio por unidad (edición)", value=mp_data["precio_por_unidad"], step=0.01, key="precio_edicion")
            if st.button("Actualizar materia prima", key="actualizar_mp"):
                hoy = date.today()
                cursor.execute("UPDATE materias_primas SET unidad = ?, precio_por_unidad = ?, fecha_actualizacion = ? WHERE id = ?", (new_unidad, new_precio, str(hoy), mp_id_sel))
                conn.commit()
                st.success("Materia prima actualizada correctamente")

# 🧱 Crear Categorías/Subcategorías
elif seccion == "🧱 Crear Categorías/Subcategorías":
    st.title("🧱 Crear nuevas Categorías y Subcategorías")
    nueva_cat = st.text_input("Nueva categoría", key="nueva_categoria")
    if st.button("Agregar Categoría"):
        cursor.execute("INSERT OR IGNORE INTO categorias_mp (nombre) VALUES (?)", (nueva_cat.strip(),))
        conn.commit()
        st.success("Categoría creada.")
    cat_sel = st.selectbox("Seleccioná una categoría", cat_options["nombre"].tolist(), key="cat_subcat_crear")
    nueva_subcat = st.text_input("Nueva subcategoría", key="nueva_subcat")
    if st.button("Agregar Subcategoría"):
        cat_id = cat_options[cat_options["nombre"] == cat_sel]["id"].values[0]
        cursor.execute("INSERT OR IGNORE INTO subcategorias_mp (nombre, categoria_id) VALUES (?, ?)", (nueva_subcat.strip(), cat_id))
        conn.commit()
        st.success("Subcategoría creada.")

# 🧪 Crear Producto
elif seccion == "🧪 Crear Producto":
    st.title("🧪 Crear Producto")
    cat_prod_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
    prod_nombre = st.text_input("Nombre del producto")
    cat_prod = st.selectbox("Categoría de producto", cat_prod_df["nombre"].tolist())
    margen = st.number_input("Margen por defecto", min_value=1.0, value=3.0, step=0.1)
    if st.button("Crear Producto"):
        cat_id = cat_prod_df[cat_prod_df["nombre"] == cat_prod]["id"].values[0]
        cursor.execute("INSERT INTO productos (nombre, categoria_id, margen) VALUES (?, ?, ?)", (prod_nombre, cat_id, margen))
        conn.commit()
        st.success("Producto creado.")

# 🍫 Agregar Ingredientes a Producto
elif seccion == "🍫 Agregar Ingredientes a Producto":
    st.title("🍫 Agregar Ingredientes a Producto")

    productos = pd.read_sql_query("SELECT id, nombre FROM productos ORDER BY nombre", conn)
    if productos.empty:
        st.info("No hay productos creados.")
    else:
        prod_dict = dict(zip(productos["nombre"], productos["id"]))
        prod_sel = st.selectbox("Seleccioná un producto", list(prod_dict.keys()))
        prod_id = prod_dict[prod_sel]

        cat_f = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_ing")
        subcat_f_df = pd.read_sql_query(subcat_filtro_query, conn, params=(cat_f,))
        subcat_dict_f = dict(zip(subcat_f_df["nombre"], subcat_f_df["id"]))

        if subcat_dict_f:
            subcat_sel = st.selectbox("Subcategoría", list(subcat_dict_f.keys()), key="subcat_ing")
            subcat_id = subcat_dict_f[subcat_sel]
            mps = pd.read_sql_query("SELECT id, nombre FROM materias_primas WHERE subcategoria_id = ?", conn, params=(subcat_id,))
            if not mps.empty:
                mp_dict = dict(zip(mps["nombre"], mps["id"]))
                mp_sel = st.selectbox("Materia prima", list(mp_dict.keys()), key="mp_ing")
                mp_id = mp_dict[mp_sel]
                cantidad = st.number_input("Cantidad usada", min_value=0.0, step=1.0)
                if st.button("Agregar ingrediente"):
                    cursor.execute("INSERT INTO ingredientes_producto (producto_id, materia_prima_id, cantidad_usada) VALUES (?, ?, ?)", (prod_id, mp_id, cantidad))
                    conn.commit()
                    st.success("Ingrediente agregado.")

        # Mostrar resumen de ingredientes
        st.subheader("🧾 Ingredientes del producto")
        resumen = pd.read_sql_query("""
        SELECT mp.nombre AS materia_prima, ip.cantidad_usada, mp.precio_por_unidad,
               (ip.cantidad_usada * mp.precio_por_unidad) AS costo_parcial
        FROM ingredientes_producto ip
        JOIN materias_primas mp ON ip.materia_prima_id = mp.id
        WHERE ip.producto_id = ?
        """, conn, params=(prod_id,))
        if not resumen.empty:
            st.dataframe(resumen)
            costo_total = resumen["costo_parcial"].sum()
            margen_default = pd.read_sql_query("SELECT margen FROM productos WHERE id = ?", conn, params=(prod_id,)).iloc[0]["margen"]
            st.markdown(f"**Costo total del producto:** ${costo_total:.2f}")
            margen_real = st.number_input("Simular margen de ganancia", value=margen_default, step=0.1)
            st.markdown(f"**Precio de venta sugerido:** ${costo_total * margen_real:.2f}")
