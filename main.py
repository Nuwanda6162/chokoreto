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
    "📂 Categorías de MP (ABM)",
    "⚙️ Categorías de Productos (ABM)",
    "🧪 Producto (ABM)",
    "🍫 Agregar Ingredientes"
])

# =========================
# 🧱 MATERIAS PRIMAS (ABM)
# =========================
if seccion == "🧱 Materias Primas (ABM)":
    st.title("🧱 Materias Primas – ABM")
    cat_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    if not cat_df.empty:
        cat_sel = st.selectbox("Categoría", cat_df["nombre"].tolist(), key="cat_mp_abm")
        sub_df = pd.read_sql_query("SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?", conn, params=(cat_sel,))
        sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))
        if sub_dict:
            sub_sel = st.selectbox("Subcategoría", list(sub_dict.keys()), key="subcat_mp_abm")
            sub_id = sub_dict[sub_sel]
            mp_df = pd.read_sql_query("""
                SELECT mp.id, cat.nombre AS categoria, sub.nombre AS subcategoria, mp.nombre, mp.cantidad, mp.unidad,
                       mp.precio_compra, mp.precio_por_unidad, mp.fecha_actualizacion
                FROM materias_primas mp
                JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
                JOIN categorias_mp cat ON sub.categoria_id = cat.id
                WHERE mp.subcategoria_id = ?
            """, conn, params=(sub_id,))
            st.dataframe(mp_df)

            st.subheader("Editar o eliminar una materia prima")
            mp_dict = dict(zip(mp_df["nombre"], mp_df["id"]))
            mp_sel = st.selectbox("Seleccioná una MP", list(mp_dict.keys()), key="mp_sel_abm")
            mp_id = mp_dict[mp_sel]
            datos = pd.read_sql_query("SELECT * FROM materias_primas WHERE id = ?", conn, params=(mp_id,)).iloc[0]
            opciones_unidad = ["Mililitros", "Centímetros cúbicos", "Centímetros", "Gramos", "Unidad"]
            unidad_actual = str(datos["unidad"]).strip()
            index_unidad = opciones_unidad.index(unidad_actual) if unidad_actual in opciones_unidad else 0
            new_cant = st.number_input("Cantidad", value=datos["cantidad"], step=0.01)
            new_precio = st.number_input("Precio de compra", value=datos["precio_compra"], step=0.01)
            new_unidad = st.selectbox("Unidad", opciones_unidad, index=index_unidad)
            new_ppu = round(new_precio / new_cant, 4) if new_cant else 0.0

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Actualizar MP"):
                    cursor.execute("""
                        UPDATE materias_primas
                        SET cantidad = ?, precio_compra = ?, unidad = ?, precio_por_unidad = ?, fecha_actualizacion = ?
                        WHERE id = ?
                    """, (new_cant, new_precio, new_unidad, new_ppu, str(date.today()), mp_id))
                    conn.commit()
                    st.success("Materia prima actualizada")
                    st.experimental_rerun()
            with col2:
                if st.button("Eliminar MP"):
                    cursor.execute("DELETE FROM materias_primas WHERE id = ?", (mp_id,))
                    conn.commit()
                    st.success("Materia prima eliminada")
                    st.experimental_rerun()

    st.subheader("Agregar nueva materia prima")
    nuevo_nombre = st.text_input("Nombre")
    nueva_cant = st.number_input("Cantidad nueva", min_value=0.0, step=0.01)
    nueva_unidad = st.selectbox("Unidad nueva", ["Mililitros", "Centímetros cúbicos", "Centímetros", "Gramos", "Unidad"], key="unidad_new")
    nuevo_precio = st.number_input("Precio de compra nuevo", min_value=0.0, step=0.01, key="precio_new")
    fecha_new = st.date_input("Fecha de actualización", key="fecha_new")
    cat_new = st.selectbox("Categoría nueva", cat_df["nombre"].tolist(), key="cat_new")
    subcat_new_df = pd.read_sql_query("SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?", conn, params=(cat_new,))
    subcat_new_dict = dict(zip(subcat_new_df["nombre"], subcat_new_df["id"]))
    if subcat_new_dict:
        subcat_new_sel = st.selectbox("Subcategoría nueva", list(subcat_new_dict.keys()), key="subcat_new")
        subcat_new_id = subcat_new_dict[subcat_new_sel]
        if st.button("Guardar nueva MP", key="guardar_new_mp") and nuevo_nombre:
            nuevo_ppu = round(nuevo_precio / nueva_cant, 4) if nueva_cant else 0.0
            cursor.execute("""
                INSERT INTO materias_primas (nombre, unidad, cantidad, precio_compra, precio_por_unidad, fecha_actualizacion, subcategoria_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nuevo_nombre.strip(), nueva_unidad, nueva_cant, nuevo_precio, nuevo_ppu, str(fecha_new), subcat_new_id))
            conn.commit()
            st.success("Materia prima guardada correctamente")
            st.experimental_rerun()


# 📂 CATEGORÍAS DE MP (ABM)
elif seccion == "📂 Categorías de MP (ABM)":
    st.title("📂 Categorías y Subcategorías de Materias Primas")
    st.subheader("Categorías")
    categorias_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    st.dataframe(categorias_df)
    nueva_cat = st.text_input("Nueva Categoría", key="nueva_cat_mp")
    if st.button("Agregar Categoría"):
        cursor.execute("INSERT INTO categorias_mp (nombre) VALUES (?)", (nueva_cat.strip(),))
        conn.commit()
        st.experimental_rerun()
    cat_dict = dict(zip(categorias_df["nombre"], categorias_df["id"]))
    if cat_dict:
        cat_sel = st.selectbox("Editar o eliminar categoría", list(cat_dict.keys()), key="cat_edit_mp")
        cat_id = cat_dict[cat_sel]
        new_cat_name = st.text_input("Nuevo nombre categoría", value=cat_sel, key="edit_cat_name")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Actualizar Categoría"):
                cursor.execute("UPDATE categorias_mp SET nombre = ? WHERE id = ?", (new_cat_name.strip(), cat_id))
                conn.commit()
                st.experimental_rerun()
        with col2:
            if st.button("Eliminar Categoría"):
                cursor.execute("DELETE FROM categorias_mp WHERE id = ?", (cat_id,))
                conn.commit()
                st.experimental_rerun()
    st.subheader("Subcategorías")
    subcats_df = pd.read_sql_query("SELECT sub.id, sub.nombre, cat.nombre AS categoria FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id", conn)
    st.dataframe(subcats_df)
    subcat_nombre = st.text_input("Nueva Subcategoría", key="nueva_subcat_mp")
    cat_sub_sel = st.selectbox("Categoría para la subcategoría", categorias_df["nombre"].tolist(), key="cat_sub_sel")
    cat_sub_id = cat_dict[cat_sub_sel]
    if st.button("Agregar Subcategoría"):
        cursor.execute("INSERT INTO subcategorias_mp (nombre, categoria_id) VALUES (?, ?)", (subcat_nombre.strip(), cat_sub_id))
        conn.commit()
        st.experimental_rerun()

# ⚙️ CATEGORÍAS DE PRODUCTOS (ABM)
elif seccion == "⚙️ Categorías de Productos (ABM)":
    st.title("⚙️ Categorías de Productos")
    categorias_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
    st.dataframe(categorias_df)
    nueva_categoria = st.text_input("Nombre de la nueva categoría", key="nueva_categoria")
    if st.button("Agregar", key="btn_agregar_categoria") and nueva_categoria:
        cursor.execute("INSERT INTO categoria_productos (nombre) VALUES (?)", (nueva_categoria.strip(),))
        conn.commit()
        st.success("Categoría agregada correctamente")
        st.experimental_rerun()
    seleccion = st.selectbox("Seleccioná una categoría", categorias_df["nombre"].tolist(), key="select_edit")
    id_sel = categorias_df[categorias_df["nombre"] == seleccion]["id"].values[0]
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

# Placeholder para las otras dos secciones:
# 🧪 Producto (ABM)
# 🍫 Agregar Ingredientes

# 🧪 PRODUCTO (ABM)
elif seccion == "🧪 Producto (ABM)":
    st.title("🧪 Productos – ABM")
    categorias_prod = pd.read_sql_query("SELECT * FROM categoria_productos", conn)

    st.subheader("Filtrar y ver productos")
    if not categorias_prod.empty:
        cat_sel = st.selectbox("Categoría de productos", categorias_prod["nombre"].tolist(), key="cat_prod_filtro")
        cat_id = categorias_prod[categorias_prod["nombre"] == cat_sel]["id"].values[0]
        productos_df = pd.read_sql_query("SELECT * FROM productos WHERE categoria_id = ?", conn, params=(cat_id,))
        st.dataframe(productos_df)

        st.subheader("Editar o eliminar un producto")
        if not productos_df.empty:
            prod_dict = dict(zip(productos_df["nombre"], productos_df["id"]))
            prod_sel = st.selectbox("Seleccioná un producto", list(prod_dict.keys()), key="prod_edit_sel")
            prod_id = prod_dict[prod_sel]
            datos = pd.read_sql_query("SELECT * FROM productos WHERE id = ?", conn, params=(prod_id,)).iloc[0]
            new_nombre = st.text_input("Nuevo nombre del producto", value=datos["nombre"], key="prod_edit_nombre")
            new_margen = st.number_input("Nuevo margen de ganancia", value=datos["margen"], step=0.1, key="prod_edit_margen")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Actualizar producto", key="btn_actualizar_prod"):
                    cursor.execute("UPDATE productos SET nombre = ?, margen = ? WHERE id = ?", (new_nombre.strip(), new_margen, prod_id))
                    conn.commit()
                    st.success("Producto actualizado correctamente")
                    st.experimental_rerun()
            with col2:
                if st.button("Eliminar producto", key="btn_eliminar_prod"):
                    cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
                    conn.commit()
                    st.success("Producto eliminado")
                    st.experimental_rerun()

    st.subheader("Agregar nuevo producto")
    nuevo_nombre = st.text_input("Nombre del nuevo producto", key="nuevo_prod_nombre")
    nueva_cat = st.selectbox("Categoría del nuevo producto", categorias_prod["nombre"].tolist(), key="nuevo_prod_cat")
    nuevo_margen = st.number_input("Margen de ganancia", min_value=1.0, value=3.0, step=0.1, key="nuevo_prod_margen")
    if st.button("Crear Producto", key="crear_nuevo_prod"):
        nueva_cat_id = categorias_prod[categorias_prod["nombre"] == nueva_cat]["id"].values[0]
        cursor.execute("INSERT INTO productos (nombre, categoria_id, margen) VALUES (?, ?, ?)", (nuevo_nombre.strip(), nueva_cat_id, nuevo_margen))
        conn.commit()
        st.success("Producto creado correctamente")
        st.experimental_rerun()


# 🍫 AGREGAR INGREDIENTES
elif seccion == "🍫 Agregar Ingredientes":
    st.title("🍫 Agregar Ingredientes a Producto")
    productos = pd.read_sql_query("SELECT id, nombre FROM productos", conn)
    cat_options = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    if not productos.empty:
        prod_dict = dict(zip(productos["nombre"], productos["id"]))
        prod_sel = st.selectbox("Seleccioná un producto", list(prod_dict.keys()))
        prod_id = prod_dict[prod_sel]
        cat_filtro = st.selectbox("Filtrar por Categoría MP", cat_options["nombre"].tolist(), key="cat_mp_filtro")
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
