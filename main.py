
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
    "✏️ Editar Materia Prima",
    "🧪 Crear Producto",
    "🍫 Agregar Ingredientes",
    "⚙️ Categorías de Productos"
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

elif seccion == "🧪 Crear Producto":
    st.title("🧪 Crear Producto")
    categorias_prod = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
    prod_nombre = st.text_input("Nombre del producto")
    categoria_prod = st.selectbox("Categoría del producto", categorias_prod["nombre"].tolist())
    margen = st.number_input("Margen de ganancia", value=3.0, step=0.1)
    if st.button("Crear Producto"):
        categoria_id = categorias_prod[categorias_prod["nombre"] == categoria_prod]["id"].values[0]
        cursor.execute("INSERT INTO productos (nombre, categoria_id, margen) VALUES (?, ?, ?)", (prod_nombre, categoria_id, margen))
        conn.commit()
        st.success("Producto creado correctamente.")

elif seccion == "🍫 Agregar Ingredientes":
    st.title("🍫 Agregar Ingredientes a Producto")
    productos = pd.read_sql_query("SELECT id, nombre FROM productos", conn)
    if not productos.empty:
        prod_dict = dict(zip(productos["nombre"], productos["id"]))
        prod_sel = st.selectbox("Seleccioná un producto", list(prod_dict.keys()))
        prod_id = prod_dict[prod_sel]
        cat_filtro = st.selectbox("Filtrar por Categoría", cat_options["nombre"].tolist(), key="cat_mp_filtro")
        subcats = pd.read_sql_query("SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?", conn, params=(cat_filtro,))
        subcat_dict = dict(zip(subcats["nombre"], subcats["id"]))
        if subcat_dict:
            subcat_sel = st.selectbox("Subcategoría", list(subcat_dict.keys()), key="subcat_mp_filtro")
            subcat_id = subcat_dict[subcat_sel]
            materias = pd.read_sql_query("SELECT id, nombre FROM materias_primas WHERE subcategoria_id = ?", conn, params=(subcat_id,))
            if not materias.empty:
                mp_dict = dict(zip(materias["nombre"], materias["id"]))
                mp_sel = st.selectbox("Materia Prima", list(mp_dict.keys()), key="mp_sel")
                mp_id = mp_dict[mp_sel]
                cantidad = st.number_input("Cantidad utilizada", min_value=0.0, step=1.0)
                if st.button("Agregar Ingrediente"):
                    cursor.execute("INSERT INTO ingredientes_producto (producto_id, materia_prima_id, cantidad_usada) VALUES (?, ?, ?)", (prod_id, mp_id, cantidad))
                    conn.commit()
                    st.success("Ingrediente agregado.")

        st.subheader("🧾 Ingredientes del producto")
        resumen = pd.read_sql_query("""
            SELECT mp.nombre AS materia_prima, ip.cantidad_usada, mp.precio_por_unidad,
                   (ip.cantidad_usada * mp.precio_por_unidad) AS costo
            FROM ingredientes_producto ip
            JOIN materias_primas mp ON ip.materia_prima_id = mp.id
            WHERE ip.producto_id = ?
        """, conn, params=(prod_id,))
        if not resumen.empty:
            st.dataframe(resumen)
            total = resumen["costo"].sum()
            margen_base = pd.read_sql_query("SELECT margen FROM productos WHERE id = ?", conn, params=(prod_id,)).iloc[0]["margen"]
            margen_actual = st.number_input("Simular margen", value=margen_base, step=0.1, key="sim_margen")
            st.markdown(f"**Costo total:** ${total:.2f}")
            st.markdown(f"**Precio sugerido:** ${total * margen_actual:.2f}")

elif seccion == "⚙️ Categorías de Productos":
    st.title("⚙️ Categorías de Productos")

    st.subheader("Listado actual")
    categorias_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
    st.dataframe(categorias_df)

    st.subheader("Agregar nueva categoría")
    nueva_categoria = st.text_input("Nombre de la nueva categoría", key="nueva_categoria")
    if st.button("Agregar", key="btn_agregar_categoria") and nueva_categoria:
        cursor.execute("INSERT INTO categoria_productos (nombre) VALUES (?)", (nueva_categoria.strip(),))
        conn.commit()
        st.success("Categoría agregada correctamente")
        st.experimental_rerun()

    st.subheader("Editar o eliminar categoría existente")
    categorias = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
    if not categorias.empty:
        cat_dict = dict(zip(categorias["nombre"], categorias["id"]))
        seleccion = st.selectbox("Seleccioná una categoría", list(cat_dict.keys()), key="select_edit")
        id_sel = cat_dict[seleccion]

        nuevo_nombre = st.text_input("Nuevo nombre", value=seleccion, key="nuevo_nombre_cat")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Actualizar nombre", key="btn_actualizar_cat") and nuevo_nombre:
                cursor.execute("UPDATE categoria_productos SET nombre = ? WHERE id = ?", (nuevo_nombre.strip(), id_sel))
                conn.commit()
                st.success("Nombre actualizado correctamente")
                st.experimental_rerun()
        with col2:
            if st.button("Eliminar categoría", key="btn_eliminar_cat"):
                cursor.execute("DELETE FROM categoria_productos WHERE id = ?", (id_sel,))
                conn.commit()
                st.success("Categoría eliminada")
                st.experimental_rerun()
