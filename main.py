
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

conn = sqlite3.connect("chokoreto_costos.db", check_same_thread=False)
cursor = conn.cursor()

st.set_page_config(page_title="Chokoreto App", layout="wide")
st.sidebar.title("Menú")
seccion = st.sidebar.radio("Ir a:", [
    "🧱 Materias Primas (ABM)",
    "🧪 Crear Producto",
    "⚙️ Categorías de Productos",
    "🍫 Agregar Ingredientes"
])

cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)

if seccion == "🧪 Crear Producto":
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

elif seccion == "🧱 Materias Primas (ABM)":
    st.title("🧱 Materias Primas – Alta, Baja y Modificación")

    st.subheader("Filtrar y ver materias primas")
    cat_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    if not cat_df.empty:
        cat_sel = st.selectbox("Categoría", cat_df["nombre"].tolist(), key="cat_mp_abm")
        sub_df = pd.read_sql_query(
            "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?",
            conn, params=(cat_sel,))
        sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))
        if sub_dict:
            sub_sel = st.selectbox("Subcategoría", list(sub_dict.keys()), key="subcat_mp_abm")
            sub_id = sub_dict[sub_sel]

            mp_df = pd.read_sql_query("""
                SELECT mp.id, mp.nombre, mp.unidad, mp.precio_por_unidad, mp.fecha_actualizacion
                FROM materias_primas mp
                WHERE mp.subcategoria_id = ?
            """, conn, params=(sub_id,))
            if not mp_df.empty:
                st.dataframe(mp_df)

                st.subheader("Editar o eliminar una materia prima")
                mp_dict = dict(zip(mp_df["nombre"], mp_df["id"]))
                mp_sel = st.selectbox("Seleccioná una MP", list(mp_dict.keys()), key="mp_sel_abm")
                mp_id = mp_dict[mp_sel]
                datos = pd.read_sql_query("SELECT * FROM materias_primas WHERE id = ?", conn, params=(mp_id,)).iloc[0]

        


        opciones_unidad = ["Mililitros", "Centímetros cúbicos", "Centímetros", "Gramos", "Unidad"]
        unidad_actual = str(datos["unidad"]).strip()
        index_unidad = opciones_unidad.index(unidad_actual) if unidad_actual in opciones_unidad else opciones_unidad.index("Unidad")
        new_unidad = st.selectbox("Unidad", opciones_unidad, index=index_unidad, key="unidad_edit_abm")
        new_precio = st.number_input("Precio por unidad", value=datos["precio_por_unidad"], step=0.01, key="precio_edit_abm")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Actualizar MP", key="btn_update_mp"):
                hoy = date.today()
                cursor.execute("UPDATE materias_primas SET unidad = ?, precio_por_unidad = ?, fecha_actualizacion = ? WHERE id = ?", (new_unidad, new_precio, str(hoy), mp_id))
                conn.commit()
                st.success("Materia prima actualizada")
                st.experimental_rerun()
        with col2:
            if st.button("Eliminar MP", key="btn_delete_mp"):
                cursor.execute("DELETE FROM materias_primas WHERE id = ?", (mp_id,))
                conn.commit()
                st.success("Materia prima eliminada")
                st.experimental_rerun()
                with col2:
                    if st.button("Eliminar MP", key="btn_delete_mp"):
                        cursor.execute("DELETE FROM materias_primas WHERE id = ?", (mp_id,))
                        conn.commit()
                        st.success("Materia prima eliminada")
                        st.experimental_rerun()

    st.subheader("Agregar nueva materia prima")
    nuevo_nombre = st.text_input("Nombre")
    nueva_unidad = st.selectbox("Unidad nueva", ["Mililitros", "Centímetros cúbicos", "Centímetros", "Gramos", "Unidad"], key="unidad_new")
    nuevo_precio = st.number_input("Precio por unidad", min_value=0.0, step=0.01, key="precio_new")
    fecha_new = st.date_input("Fecha de actualización", key="fecha_new")
    cat_new = st.selectbox("Categoría nueva", cat_df["nombre"].tolist(), key="cat_new")
    subcat_new_df = pd.read_sql_query(
        "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?",
        conn, params=(cat_new,))
    subcat_new_dict = dict(zip(subcat_new_df["nombre"], subcat_new_df["id"]))
    if subcat_new_dict:
        subcat_new_sel = st.selectbox("Subcategoría nueva", list(subcat_new_dict.keys()), key="subcat_new")
        subcat_new_id = subcat_new_dict[subcat_new_sel]
        if st.button("Guardar nueva MP", key="guardar_new_mp") and nuevo_nombre:
            cursor.execute("INSERT INTO materias_primas (nombre, unidad, precio_por_unidad, fecha_actualizacion, subcategoria_id) VALUES (?, ?, ?, ?, ?)",
                           (nuevo_nombre.strip(), nueva_unidad, nuevo_precio, str(fecha_new), subcat_new_id))
            conn.commit()
            st.success("Materia prima guardada correctamente")
            st.experimental_rerun()

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
