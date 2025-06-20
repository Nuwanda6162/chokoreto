
# Streamlit app local para gestión de costos de Chokoreto con SQLite
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import math
import numpy as np

# Conectar a la base SQLite local
conn = sqlite3.connect("chokoreto_costos.db", check_same_thread=False)
cursor = conn.cursor()


# Funcion de redondeo
def redondeo_personalizado(valor):
    if valor < 1000:
        return math.ceil(valor / 10.0) * 10
    elif valor < 10000:
        return math.ceil(valor / 100.0) * 100
    else:
        return math.ceil(valor / 1000.0) * 1000


st.set_page_config(page_title="Chokoreto App", layout="wide")
st.sidebar.title("Menú")
seccion = st.sidebar.radio("Ir a:", [
    "💵 Movimientos",
    "📉 Historial",
    "🧪 Simulador de productos",
    "🛠️ ABM (Gestión de Datos)"
])


# =========================
# 🛠️ ABMs
# =========================

if seccion == "🛠️ ABM (Gestión de Datos)":
    st.title("🛠️ ABM – Gestión de Datos")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Materias Primas",
        "Categorías de MP",
        "Categorías de Productos",
        "Productos",
        "Ingredientes x Producto"
    ])
    with tab1:
        # 🧱 MATERIAS PRIMAS (ABM)
        st.title("🧱 Materias Primas – ABM")
        cat_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
        if not cat_df.empty:
            cat_sel = st.selectbox("Categoría", cat_df["nombre"].tolist(), key="cat_mp_abm")
            sub_df = pd.read_sql_query(
                "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?",
                conn, params=(cat_sel,))
            sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))
            if sub_dict:
                sub_sel = st.selectbox("Subcategoría", sorted(sub_dict.keys()), key="subcat_mp_abm")
                sub_id = sub_dict[sub_sel]
                import numpy as np

                # Mostrar tabla editable de materias primas de la subcategoría elegida
                mp_df = pd.read_sql_query("""
                    SELECT mp.id, cat.nombre AS categoria, sub.nombre AS subcategoria, mp.nombre, mp.cantidad, mp.unidad,
                        mp.precio_compra, mp.precio_por_unidad, mp.fecha_actualizacion
                    FROM materias_primas mp
                    JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
                    JOIN categorias_mp cat ON sub.categoria_id = cat.id
                    WHERE mp.subcategoria_id = ?
                """, conn, params=(sub_id,))

                if mp_df.empty:
                    st.info("No hay materias primas en esta subcategoría.")
                else:
                    st.subheader("Editar materias primas (tipo Excel)")

                    edit_cols = ["nombre", "cantidad", "unidad", "precio_compra"]
                    editable_df = mp_df[["id"] + edit_cols].copy()

                    edited = st.data_editor(
                        editable_df,
                        column_config={
                            "id": st.column_config.Column("ID", disabled=True),
                            "nombre": st.column_config.TextColumn("Nombre"),
                            "cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=0.01),
                            "unidad": st.column_config.SelectboxColumn("Unidad",
                                                                       options=["Mililitros", "Centímetros cúbicos",
                                                                                "Centímetros", "Gramos", "Unidad"]),
                            "precio_compra": st.column_config.NumberColumn("Precio de compra", min_value=0, step=0.01),
                        },
                        num_rows="dynamic",
                        key="data_editor_mp"
                    )

                    if st.button("💾 Guardar cambios de materias primas"):
                        cambios = 0
                        for idx, row in edited.iterrows():
                            orig_row = editable_df.loc[idx]
                            if not np.isclose(row["cantidad"], orig_row["cantidad"]) or \
                                    not np.isclose(row["precio_compra"], orig_row["precio_compra"]) or \
                                    row["nombre"] != orig_row["nombre"] or \
                                    row["unidad"] != orig_row["unidad"]:
                                try:
                                    ppu = round(row["precio_compra"] / row["cantidad"], 4) if row[
                                                                                                  "cantidad"] > 0 else 0.0
                                    cursor.execute("""
                                        UPDATE materias_primas
                                        SET nombre = ?, cantidad = ?, unidad = ?, precio_compra = ?, precio_por_unidad = ?, fecha_actualizacion = ?
                                        WHERE id = ?
                                    """, (row["nombre"], row["cantidad"], row["unidad"], row["precio_compra"], ppu,
                                          str(date.today()), row["id"]))
                                    conn.commit()
                                    # Recalculo automático de productos
                                    prod_ids = pd.read_sql_query(
                                        "SELECT producto_id FROM ingredientes_producto WHERE materia_prima_id = ?",
                                        conn, params=(row["id"],)
                                    )["producto_id"].tolist()
                                    for pid in prod_ids:
                                        q = """
                                            SELECT ip.cantidad_usada, mp.precio_por_unidad
                                            FROM ingredientes_producto ip
                                            JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                                            WHERE ip.producto_id = ?
                                        """
                                        ing_df = pd.read_sql_query(q, conn, params=(pid,))
                                        costo_total = (ing_df["cantidad_usada"] * ing_df[
                                            "precio_por_unidad"]).sum() if not ing_df.empty else 0.0
                                        margen = pd.read_sql_query("SELECT margen FROM productos WHERE id = ?", conn,
                                                                   params=(pid,)).iloc[0]["margen"]
                                        precio_final = round(costo_total * margen, 2)
                                        precio_normalizado = redondeo_personalizado(precio_final)
                                        cursor.execute("""
                                            UPDATE productos
                                            SET precio_costo = ?, precio_final = ?, precio_normalizado = ?
                                            WHERE id = ?
                                        """, (costo_total, precio_final, precio_normalizado, pid))
                                        conn.commit()
                                    cambios += 1
                                except Exception as e:
                                    st.error(f"❌ Error al actualizar la fila ID {row['id']}: {e}")
                        if cambios:
                            st.success(f"¡Se guardaron {cambios} cambios correctamente!")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")

                    st.caption(
                        "Tip: Hacé doble click en cualquier celda para editarla. Al finalizar, hacé click en 'Guardar cambios'.")

        st.subheader("Agregar nueva materia prima")
        nuevo_nombre = st.text_input("Nombre")
        nueva_cant = st.number_input("Cantidad nueva", min_value=0.0, step=0.01)
        nueva_unidad = st.selectbox("Unidad nueva",
                                    ["Mililitros", "Centímetros cúbicos", "Centímetros", "Gramos", "Unidad"],
                                    key="unidad_new")
        nuevo_precio = st.number_input("Precio de compra nuevo", min_value=0.0, step=0.01, key="precio_new")
        fecha_new = st.date_input("Fecha de actualización", key="fecha_new")
        cat_new = st.selectbox("Categoría nueva", cat_df["nombre"].tolist(), key="cat_new")
        subcat_new_df = pd.read_sql_query(
            "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = ?",
            conn, params=(cat_new,))
        subcat_new_dict = dict(zip(subcat_new_df["nombre"], subcat_new_df["id"]))
        if subcat_new_dict:
            subcat_new_sel = st.selectbox("Subcategoría nueva", sorted(subcat_new_dict.keys()), key="subcat_new")
            subcat_new_id = subcat_new_dict[subcat_new_sel]
            if st.button("Guardar nueva MP", key="guardar_new_mp") and nuevo_nombre:
                try:
                    nuevo_ppu = round(nuevo_precio / nueva_cant, 4) if nueva_cant else 0.0
                    cursor.execute("""
                        INSERT INTO materias_primas (nombre, unidad, cantidad, precio_compra, precio_por_unidad, fecha_actualizacion, subcategoria_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (nuevo_nombre.strip(), nueva_unidad, nueva_cant, nuevo_precio, nuevo_ppu, str(fecha_new),
                          subcat_new_id))
                    conn.commit()
                    st.success("Materia prima guardada correctamente")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Ya existe una materia prima con ese nombre en esta subcategoría.")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error inesperado: {e}")

    with tab2:
        # 📂 CATEGORÍAS DE MP (ABM)
        st.title("📂 Categorías y Subcategorías de Materias Primas")
        st.subheader("Categorías")

        cat_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)

        if cat_df.empty:
            st.info("No hay categorías de materias primas.")
        else:
            st.subheader("Editar categorías (tipo Excel)")
            editable_df = cat_df[["id", "nombre"]].copy()
            edited = st.data_editor(
                editable_df,
                column_config={
                    "id": st.column_config.Column("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre")
                },
                num_rows="dynamic",
                key="data_editor_catmp"
            )

            if st.button("💾 Guardar cambios en categorías"):
                cambios = 0
                for idx, row in edited.iterrows():
                    orig_row = editable_df.loc[idx]
                    if row["nombre"] != orig_row["nombre"]:
                        try:
                            cursor.execute("UPDATE categorias_mp SET nombre = ? WHERE id = ?",
                                           (row["nombre"], row["id"]))
                            conn.commit()
                            cambios += 1
                        except Exception as e:
                            st.error(f"❌ Error al actualizar la categoría ID {row['id']}: {e}")
                if cambios:
                    st.success(f"¡Se guardaron {cambios} cambios en categorías!")
                    st.rerun()
                else:
                    st.info("No hubo cambios para guardar.")

            st.caption("Editá el nombre de la categoría y luego tocá 'Guardar cambios'.")

        st.subheader("Agregar nueva categoría de materias primas")

        nueva_cat = st.text_input("Nueva Categoría", key="nueva_cat_mp")
        if st.button("Agregar Categoría", key="btn_agregar_cat_mp"):
            if not nueva_cat.strip():
                st.warning("Por favor, ingresá un nombre de categoría.")
            else:
                try:
                    cursor.execute("INSERT INTO categorias_mp (nombre) VALUES (?)", (nueva_cat.strip(),))
                    conn.commit()
                    st.success("¡Categoría agregada correctamente!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Ya existe una categoría con ese nombre o hay un error de integridad.")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error inesperado: {e}")

        st.subheader("Subcategorías")

        subcats_df = pd.read_sql_query("""
            SELECT sub.id, sub.nombre, cat.nombre AS categoria 
            FROM subcategorias_mp sub 
            JOIN categorias_mp cat ON sub.categoria_id = cat.id
        """, conn)

        if subcats_df.empty:
            st.info("No hay subcategorías de materias primas.")
        else:
            st.subheader("Editar subcategorías (tipo Excel)")
            editable_df = subcats_df[["id", "nombre", "categoria"]].copy()
            edited = st.data_editor(
                editable_df,
                column_config={
                    "id": st.column_config.Column("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre")
                },
                num_rows="dynamic",
                key="data_editor_subcatmp"
            )

            if st.button("💾 Guardar cambios en subcategorías"):
                cambios = 0
                for idx, row in edited.iterrows():
                    orig_row = editable_df.loc[idx]
                    if row["nombre"] != orig_row["nombre"]:
                        try:
                            cursor.execute("UPDATE subcategorias_mp SET nombre = ? WHERE id = ?",
                                           (row["nombre"], row["id"]))
                            conn.commit()
                            cambios += 1
                        except Exception as e:
                            st.error(f"❌ Error al actualizar la subcategoría ID {row['id']}: {e}")
                if cambios:
                    st.success(f"¡Se guardaron {cambios} cambios en subcategorías!")
                    st.rerun()
                else:
                    st.info("No hubo cambios para guardar.")

            st.caption("Editá el nombre de la subcategoría y luego tocá 'Guardar cambios'.")

        st.subheader("Agregar nueva subcategoría de materias primas")

        # Traer categorías actuales para elegir a cuál pertenece la subcat
        cat_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
        if cat_df.empty:
            st.warning("Primero agregá al menos una categoría de materias primas.")
        else:
            cat_dict = dict(zip(cat_df["nombre"], cat_df["id"]))
            subcat_nombre = st.text_input("Nueva Subcategoría", key="nueva_subcat_mp")
            cat_sel = st.selectbox("Categoría para la subcategoría", sorted(cat_dict.keys()), key="cat_sub_sel")
            cat_id = cat_dict[cat_sel]
            if st.button("Agregar Subcategoría", key="btn_agregar_subcat_mp"):
                if not subcat_nombre.strip():
                    st.warning("Por favor, ingresá un nombre de subcategoría.")
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO subcategorias_mp (nombre, categoria_id) VALUES (?, ?)",
                            (subcat_nombre.strip(), cat_id))
                        conn.commit()
                        st.success("¡Subcategoría agregada!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Ya existe una subcategoría con ese nombre en esa categoría.")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error inesperado: {e}")

    with tab3:
        # ⚙️ Categorías de Productos (ABM)
        st.title("⚙️ Categorías y Subcategorías de Productos")
        st.subheader("Editar categorías de productos (tipo Excel)")

        cat_prod_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)

        if cat_prod_df.empty:
            st.info("No hay categorías de productos.")
        else:
            editable_catprod_df = cat_prod_df[["id", "nombre"]].copy()
            edited_catprod = st.data_editor(
                editable_catprod_df,
                column_config={
                    "id": st.column_config.Column("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre")
                },
                num_rows="dynamic",
                key="data_editor_catprod"
            )

            if st.button("💾 Guardar cambios en categorías de productos"):
                cambios = 0
                for idx, row in edited_catprod.iterrows():
                    orig_row = editable_catprod_df.loc[idx]
                    if row["nombre"] != orig_row["nombre"]:
                        try:
                            cursor.execute("UPDATE categoria_productos SET nombre = ? WHERE id = ?",
                                           (row["nombre"], row["id"]))
                            conn.commit()
                            cambios += 1
                        except Exception as e:
                            st.error(f"❌ Error al actualizar la categoría ID {row['id']}: {e}")
                if cambios:
                    st.success(f"¡Se guardaron {cambios} cambios en categorías de productos!")
                    st.rerun()
                else:
                    st.info("No hubo cambios para guardar.")

            st.caption("Editá el nombre de la categoría y luego tocá 'Guardar cambios'.")

        st.subheader("Eliminar categoría de producto")
        cat_dict = dict(zip(cat_prod_df["nombre"], cat_prod_df["id"]))
        if cat_dict:
            cat_sel = st.selectbox("Eliminar categoría", sorted(cat_dict.keys()), key="cat_edit_prod")
            cat_id = cat_dict[cat_sel]
            if st.button("Eliminar Categoría", key="delete_cat_prod"):
                try:
                    cursor.execute("DELETE FROM categoria_productos WHERE id = ?", (cat_id,))
                    conn.commit()
                    st.success("¡Categoría eliminada!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ No se puede eliminar: Hay subcategorías o productos asociados.")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error inesperado: {e}")

 
        st.subheader("Nueva categoria")
        nueva_cat = st.text_input("Nueva Categoría", key="nueva_cat_prod")
        if st.button("Agregar Categoría", key="agregar_cat_prod"):
            try:
                cursor.execute("INSERT INTO categoria_productos (nombre) VALUES (?)", (nueva_cat.strip(),))
                conn.commit()
                st.success("¡Categoría agregada correctamente!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("❌ Ya existe una categoría con ese nombre.")
            except Exception as e:
                st.error(f"❌ Ocurrió un error inesperado: {e}")

        st.subheader("Editar subcategorías de productos (tipo Excel)")
        subcats_prod_df = pd.read_sql_query("""
            SELECT sub.id, sub.nombre, cat.nombre AS categoria
            FROM subcategorias_productos sub
            JOIN categoria_productos cat ON sub.categoria_id = cat.id
        """, conn)

        if subcats_prod_df.empty:
            st.info("No hay subcategorías de productos.")
        else:
            editable_subcatprod_df = subcats_prod_df[["id", "nombre", "categoria"]].copy()
            edited_subcatprod = st.data_editor(
                editable_subcatprod_df,
                column_config={
                    "id": st.column_config.Column("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre"),
                    # "categoria" solo se muestra, no es editable aquí
                },
                num_rows="dynamic",
                key="data_editor_subcatprod"
            )

            if st.button("💾 Guardar cambios en subcategorías de productos"):
                cambios = 0
                for idx, row in edited_subcatprod.iterrows():
                    orig_row = editable_subcatprod_df.loc[idx]
                    if row["nombre"] != orig_row["nombre"]:
                        try:
                            cursor.execute("UPDATE subcategorias_productos SET nombre = ? WHERE id = ?",
                                           (row["nombre"], row["id"]))
                            conn.commit()
                            cambios += 1
                        except Exception as e:
                            st.error(f"❌ Error al actualizar la subcategoría ID {row['id']}: {e}")
                if cambios:
                    st.success(f"¡Se guardaron {cambios} cambios en subcategorías de productos!")
                    st.rerun()
                else:
                    st.info("No hubo cambios para guardar.")

            st.caption("Editá el nombre de la subcategoría y luego tocá 'Guardar cambios'.")

        cat_sub_sel = st.selectbox("Categoría para la subcategoría", cat_prod_df["nombre"].tolist(),
                                   key="cat_sub_sel_prod")
        cat_sub_id = cat_dict[cat_sub_sel]

        # Mostrar solo las subcategorías de la categoría seleccionada
        subcats_df = pd.read_sql_query("""
                SELECT sp.id, sp.nombre, cp.nombre AS categoria
                FROM subcategorias_productos sp
                JOIN categoria_productos cp ON sp.categoria_id = cp.id
                WHERE cp.id = ?
            """, conn, params=(cat_sub_id,))

        if subcats_df.empty:
            st.info("No hay subcategorías cargadas para esta categoría.")
        else:
            st.dataframe(subcats_df)

        subcat_nombre = st.text_input("Nueva Subcategoría", key="nueva_subcat_prod")
        if st.button("Agregar Subcategoría", key="agregar_subcat_prod"):
            try:
                cursor.execute("INSERT INTO subcategorias_productos (nombre, categoria_id) VALUES (?, ?)",
                               (subcat_nombre.strip(), cat_sub_id))
                conn.commit()
                st.success("¡Subcategoría agregada!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("❌ Ya existe una subcategoría con ese nombre en esa categoría.")
            except Exception as e:
                st.error(f"❌ Ocurrió un error inesperado: {e}")


    with tab4:
    # Productos (ABM)
#    elif seccion == "🧪 Producto (ABM)":
        st.title("🧪 Productos – ABM")
        cat_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
        if not cat_df.empty:
            cat_sel = st.selectbox("Categoría de Producto", cat_df["nombre"].tolist(), key="cat_prod_abm")
            sub_df = pd.read_sql_query("""
                    SELECT sp.id, sp.nombre FROM subcategorias_productos sp
                    JOIN categoria_productos cp ON sp.categoria_id = cp.id
                    WHERE cp.nombre = ?
                """, conn, params=(cat_sel,))
            sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))


            if sub_dict:
                sub_sel = st.selectbox("Subcategoría", sorted(sub_dict.keys()), key="subcat_prod_abm")
                sub_id = sub_dict[sub_sel]

                # --- PRODUCTOS CON PRECIOS VISIBLES ---
                productos_df = pd.read_sql_query("""
                    SELECT id, nombre, margen, precio_costo, precio_final, precio_normalizado
                    FROM productos
                    WHERE subcategoria_id = ?
                """, conn, params=(sub_id,))

                if productos_df.empty:
                    st.info("No hay productos en esta subcategoría.")
                else:
                    st.subheader("Editar productos (tipo Excel)")
                    editable_cols = ["id", "nombre", "margen", "precio_costo", "precio_final", "precio_normalizado"]
                    editable_prods = productos_df[editable_cols].copy()

                    edited = st.data_editor(
                        editable_prods,
                        column_config={
                            "id": st.column_config.Column("ID", disabled=True),
                            "nombre": st.column_config.TextColumn("Nombre"),
                            "margen": st.column_config.NumberColumn("Margen", min_value=0, step=0.1),
                            "precio_costo": st.column_config.NumberColumn("Costo", disabled=True),
                            "precio_final": st.column_config.NumberColumn("Precio Final", disabled=True),
                            "precio_normalizado": st.column_config.NumberColumn("Normalizado", disabled=True),
                        },
                        num_rows="dynamic",
                        key="data_editor_prods"
                    )

                    if st.button("💾 Guardar cambios en productos"):
                        cambios = 0
                        for idx, row in edited.iterrows():
                            orig_row = editable_prods.loc[idx]
                            if row["nombre"] != orig_row["nombre"] or not math.isclose(row["margen"],
                                                                                       orig_row["margen"]):
                                try:
                                    # Actualizá margen y recalculá precios
                                    precio_costo = row["precio_costo"] if row["precio_costo"] else 0.0
                                    precio_final = round(precio_costo * row["margen"], 2)
                                    precio_normalizado = redondeo_personalizado(precio_final)
                                    cursor.execute("""
                                        UPDATE productos
                                        SET nombre = ?, margen = ?, precio_final = ?, precio_normalizado = ?
                                        WHERE id = ?
                                    """, (row["nombre"], row["margen"], precio_final, precio_normalizado, row["id"]))
                                    conn.commit()
                                    cambios += 1
                                except Exception as e:
                                    st.error(f"❌ Error al actualizar el producto ID {row['id']}: {e}")
                        if cambios:
                            st.success(f"¡Se guardaron {cambios} cambios en productos!")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")

                    st.caption("Editá nombre y margen. Los precios se actualizan solos al guardar.")
                if not productos_df.empty:
                    # --- Editar o eliminar producto existente ---
                    st.subheader("Editar o eliminar producto")
                    prod_dict = dict(zip(productos_df["nombre"], productos_df["id"]))
                    prod_sel = st.selectbox("Seleccioná un producto", sorted(prod_dict.keys()), key="prod_edit_sel")
                    prod_id = prod_dict[prod_sel]
                    datos = pd.read_sql_query("SELECT * FROM productos WHERE id = ?", conn, params=(prod_id,)).iloc[0]

                    nuevo_nombre = st.text_input("Nombre", value=datos["nombre"], key="edit_nombre_prod")
                    nuevo_margen = st.number_input("Margen de ganancia", value=float(datos["margen"]), step=0.1,
                                                   key="edit_margen_prod")

                    precio_costo = datos["precio_costo"]
                    if precio_costo is None:
                        st.warning("Este producto aún no tiene ingredientes cargados. El precio de costo es 0.")
                        precio_costo = 0.0

                    precio_final = round(precio_costo * nuevo_margen, 2)

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Actualizar Producto", key="btn_actualizar_prod"):
                            try:
                                precio_normalizado = round(precio_final, -2)
                                cursor.execute("""
                                        UPDATE productos SET nombre = ?, margen = ?, precio_final = ?, precio_normalizado = ?
                                        WHERE id = ?
                                    """, (nuevo_nombre.strip(), nuevo_margen, precio_final, precio_normalizado, prod_id))
                                conn.commit()
                                st.success("Producto actualizado")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("❌ Ya existe un producto con ese nombre en esta subcategoría.")
                            except Exception as e:
                                st.error(f"❌ Ocurrió un error al actualizar: {e}")
                    with col2:
                        confirmar = st.checkbox("Confirmo que deseo eliminar este producto y sus datos relacionados",
                                                key="chk_confirm_del_prod")
                        st.warning("⚠️ Esta acción eliminará el producto y TODAS las ventas e ingredientes asociados.")
                        if confirmar:
                            if st.button("❌ Eliminar Producto", key="btn_eliminar_prod"):
                                try:
                                    cursor.execute("DELETE FROM ingredientes_producto WHERE producto_id = ?", (prod_id,))
                                    cursor.execute("DELETE FROM ventas WHERE producto_id = ?", (prod_id,))
                                    cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
                                    conn.commit()
                                    st.success("Producto y registros asociados eliminados correctamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Ocurrió un error al eliminar: {e}")
                else:
                    st.info("No hay productos cargados en esta subcategoría.")

                # --- Agregar nuevo producto (se muestra siempre si hay subcategoría válida) ---
                st.subheader("Agregar nuevo producto")
                nuevo_nombre = st.text_input("Nombre nuevo", key="nombre_nuevo_prod")
                nuevo_margen = st.number_input("Margen de ganancia", min_value=0.0, step=0.1, key="margen_nuevo_prod")

                if st.button("Guardar nuevo producto", key="guardar_nuevo_prod") and nuevo_nombre:
                    try:
                        precio_costo = 0.0  # como aún no hay ingredientes cargados
                        precio_final = round(precio_costo * nuevo_margen, 2)
                        precio_normalizado = round(precio_final, -2)

                        cursor.execute("""
                                INSERT INTO productos (nombre, margen, categoria_id, subcategoria_id, precio_costo, precio_final, precio_normalizado)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                            nuevo_nombre.strip(), nuevo_margen,
                            cat_df[cat_df["nombre"] == cat_sel]["id"].values[0],
                            sub_dict[sub_sel],
                            precio_costo,
                            precio_final,
                            precio_normalizado
                        ))
                        conn.commit()
                        st.success("Producto guardado correctamente")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Ya existe un producto con ese nombre en esta subcategoría.")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error inesperado: {e}")

            else:
                st.warning("Esta categoría no tiene subcategorías.")

    with tab5:
        # Agregar Ingredientes
        st.title("🍫 Ingredientes por Producto")
        cat_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
        if cat_df.empty:
            st.warning("No hay categorías de productos cargadas.")
        else:
            cat_sel = st.selectbox("Categoría de Producto", cat_df["nombre"].tolist(), key="cat_ing_prod")
            sub_df = pd.read_sql_query("""
                    SELECT sp.id, sp.nombre FROM subcategorias_productos sp
                    JOIN categoria_productos cp ON sp.categoria_id = cp.id
                    WHERE cp.nombre = ?
                """, conn, params=(cat_sel,))
            sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))

            if sub_dict:
                sub_sel = st.selectbox("Subcategoría de Producto", sorted(sub_dict.keys()), key="subcat_ing_prod")
                sub_id = sub_dict[sub_sel]

                prod_df = pd.read_sql_query(
                    "SELECT id, nombre FROM productos WHERE subcategoria_id = ?", conn, params=(sub_id,))
                prod_dict = dict(zip(prod_df["nombre"], prod_df["id"]))


                import numpy as np

                if prod_dict:
                    prod_sel = st.selectbox("Seleccioná un producto", sorted(prod_dict.keys()), key="ingred_prod_sel")
                    prod_id = prod_dict[prod_sel]

                    # Traer ingredientes del producto
                    st.subheader("Ingredientes actuales")
                    query = """
                        SELECT mp.id, mp.nombre, mp.unidad, ip.cantidad_usada, 
                               (mp.precio_por_unidad * ip.cantidad_usada) AS costo
                        FROM ingredientes_producto ip
                        JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                        WHERE ip.producto_id = ?
                    """
                    ingredientes_df = pd.read_sql_query(query, conn, params=(prod_id,))

                    if ingredientes_df.empty:
                        st.info("Este producto no tiene ingredientes cargados.")
                    else:
                        st.subheader("Editar ingredientes (solo cantidad)")

                        editable_cols = ["id", "nombre", "unidad", "cantidad_usada", "costo"]
                        editable_ings = ingredientes_df[editable_cols].copy()

                        edited = st.data_editor(
                            editable_ings,
                            column_config={
                                "id": st.column_config.Column("ID", disabled=True),
                                "nombre": st.column_config.TextColumn("Materia Prima", disabled=True),
                                "unidad": st.column_config.TextColumn("Unidad", disabled=True),
                                "cantidad_usada": st.column_config.NumberColumn("Cantidad usada", min_value=0,
                                                                                step=0.01),
                                "costo": st.column_config.NumberColumn("Costo", disabled=True),
                            },
                            num_rows="dynamic",
                            key="data_editor_ingreds"
                        )

                        if st.button("💾 Guardar cambios de ingredientes"):
                            cambios = 0
                            for idx, row in edited.iterrows():
                                orig_row = editable_ings.loc[idx]
                                if not np.isclose(row["cantidad_usada"], orig_row["cantidad_usada"]):
                                    try:
                                        cursor.execute("""
                                            UPDATE ingredientes_producto
                                            SET cantidad_usada = ?
                                            WHERE producto_id = ? AND materia_prima_id = ?
                                        """, (row["cantidad_usada"], prod_id, row["id"]))
                                        conn.commit()
                                        cambios += 1
                                    except Exception as e:
                                        st.error(f"❌ Error al actualizar ingrediente ID {row['id']}: {e}")
                            if cambios:
                                st.success(f"¡Se guardaron {cambios} cambios en ingredientes!")
                                st.rerun()
                            else:
                                st.info("No hubo cambios para guardar.")

                        st.caption("Solo podés editar la cantidad usada. El costo se calcula automáticamente.")
                    costo_total = ingredientes_df["costo"].sum() if not ingredientes_df.empty else 0.0
                    st.info(f"🧮 Costo total del producto: **${round(costo_total, 2)}**")
                    # --- ELIMINAR INGREDIENTE ---
                    if not ingredientes_df.empty:
                        st.subheader("Eliminar ingrediente")
                        ing_df = pd.read_sql_query("""
                                SELECT mp.id, mp.nombre FROM ingredientes_producto ip
                                JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                                WHERE ip.producto_id = ?
                            """, conn, params=(prod_id,))
                        ing_dict = dict(zip(ing_df["nombre"], ing_df["id"]))

                        ing_nombre = st.selectbox("Ingrediente a eliminar", sorted(ing_dict.keys()),
                                                  key="ingred_mod_sel")
                        mp_id = ing_dict[ing_nombre]
                        mp_info = pd.read_sql_query("""
                                SELECT unidad, cantidad_usada FROM ingredientes_producto ip
                                JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                                WHERE ip.producto_id = ? AND mp.id = ?
                            """, conn, params=(prod_id, mp_id)).iloc[0]

                        if st.button("Eliminar ingrediente", key="btn_eliminar_ing"):
                            try:
                                cursor.execute("""
                                          DELETE FROM ingredientes_producto
                                          WHERE producto_id = ? AND materia_prima_id = ?
                                      """, (prod_id, mp_id))
                                conn.commit()
                                st.success("Ingrediente eliminado")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Ocurrió un error al eliminar: {e}")


                    # --- AGREGAR INGREDIENTE ---
                    st.subheader("Agregar nuevo ingrediente")
                    cat_mp_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
                    cat_mp_sel = st.selectbox("Categoría de Materia Prima", cat_mp_df["nombre"].tolist(),
                                              key="cat_ing_mp")

                    sub_mp_df = pd.read_sql_query("""
                            SELECT sub.id, sub.nombre FROM subcategorias_mp sub
                            JOIN categorias_mp cat ON sub.categoria_id = cat.id
                            WHERE cat.nombre = ?
                        """, conn, params=(cat_mp_sel,))
                    sub_mp_dict = dict(zip(sub_mp_df["nombre"], sub_mp_df["id"]))

                    if sub_mp_dict:
                        sub_mp_sel = st.selectbox("Subcategoría de MP", sorted(sub_mp_dict.keys()), key="subcat_ing_mp")
                        sub_mp_id = sub_mp_dict[sub_mp_sel]

                        mp_df = pd.read_sql_query(
                            "SELECT id, nombre, unidad FROM materias_primas WHERE subcategoria_id = ?", conn,
                            params=(sub_mp_id,))
                        mp_dict = dict(zip(mp_df["nombre"], mp_df["id"]))

                        if mp_dict:
                            mp_sel = st.selectbox("Materia Prima", sorted(mp_dict.keys()), key="ingred_mp_sel")
                            mp_id = mp_dict[mp_sel]
                            unidad = mp_df[mp_df["id"] == mp_id]["unidad"].values[0]
                            cant_usada = st.number_input(f"Cantidad usada ({unidad})", min_value=0.0, step=0.01,
                                                         key="cant_usada")

                            if st.button("Agregar ingrediente"):
                                try:
                                    cursor.execute("""
                                            INSERT INTO ingredientes_producto (producto_id, materia_prima_id, cantidad_usada)
                                            VALUES (?, ?, ?)
                                        """, (prod_id, mp_id, cant_usada))
                                    conn.commit()
                                    st.success("Ingrediente agregado")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("❌ Ya existe ese ingrediente en este producto.")
                                except Exception as e:
                                    st.error(f"❌ Ocurrió un error inesperado: {e}")
                        else:
                            st.warning("No hay materias primas en esta subcategoría.")
                    else:
                        st.warning("Esta categoría no tiene subcategorías.")

                    # --- BOTÓN PARA ACTUALIZAR COSTO ---
                    if st.button("Actualizar costo total del producto", key="actualizar_costo_prod"):
                        try:
                            cursor.execute("UPDATE productos SET precio_costo = ? WHERE id = ?", (costo_total, prod_id))
                            conn.commit()
                            st.success("Precio de costo actualizado en el producto")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al actualizar el costo: {e}")
                else:
                    st.warning("No hay productos en esta subcategoría.")
            else:
                st.warning("Esta categoría no tiene subcategorías.")




# =========================
# Registro de Ventas y Gastos
# =========================

elif seccion == "💵 Movimientos":
    st.title("💵️ Ventas y Gastos")
    tab1, tab2 = st.tabs([
        "Registrar Ventas",
        "Registrar Gastos"
    ])
    with tab1:
        # Registrar Venta
        import math

        st.title("📦 Registrar Venta")

        # 1. Cargar todos los productos y sus datos asociados
        productos_full = pd.read_sql_query("""
            SELECT p.id, p.nombre, p.precio_normalizado, 
                   sp.nombre AS subcategoria, cp.nombre AS categoria
            FROM productos p
            JOIN subcategorias_productos sp ON p.subcategoria_id = sp.id
            JOIN categoria_productos cp ON sp.categoria_id = cp.id
        """, conn)

        if productos_full.empty:
            st.warning("No hay productos cargados.")
        else:
            # 2. Búsqueda por texto libre
            busqueda = st.text_input("Buscar producto (nombre, subcategoría o categoría):").lower()
            if busqueda:
                productos_filtrados = productos_full[
                    productos_full["nombre"].str.lower().str.contains(busqueda) |
                    productos_full["subcategoria"].str.lower().str.contains(busqueda) |
                    productos_full["categoria"].str.lower().str.contains(busqueda)
                    ]
            else:
                productos_filtrados = productos_full.copy()

            if productos_filtrados.empty:
                st.warning("No se encontraron productos que coincidan.")
            else:
                # 3. Armamos las opciones mostrando nombre + categoría/subcategoría para más info visual
                opciones = productos_filtrados["nombre"] + " [" + productos_filtrados["categoria"] + " / " + \
                           productos_filtrados["subcategoria"] + "]"
                prod_idx = st.selectbox("Seleccioná el producto", opciones.tolist(), key="prod_busqueda")
                producto = productos_filtrados.iloc[opciones.tolist().index(prod_idx)]

                st.info(f"**Categoría:** {producto['categoria']}  |  **Subcategoría:** {producto['subcategoria']}")
                st.info(f"**Precio unitario:** ${producto['precio_normalizado']:.2f}")

                precio_actual = producto['precio_normalizado']

                # Validación de precio válido
                precio_valido = (
                        precio_actual is not None and
                        not (isinstance(precio_actual, float) and (math.isnan(precio_actual) or precio_actual <= 0)) and
                        precio_actual != "None"
                )

               
                descripcion_libre = ""
                if producto["nombre"].lower() in ["ingreso libre", "varios", "reserva",
                                                  "otros"]:  # o el nombre que decidas
                    st.info("Estás registrando una venta de tipo ingreso libre.")
                    descripcion_libre = st.text_area("Descripción (ej: reserva, seña, evento, etc.)")
                    cantidad = st.number_input("Monto recibido ($)", min_value=1, value=1, step=1, key="cant_venta")
                    tipo_pago = st.selectbox("Tipo de pago", ["Efectivo", "Otros"], key="pago_venta")
                    descuento = 0.0  # opcional: deshabilitá descuento en este caso
                    fecha_actual = st.date_input("Fecha de actualización", key="fecha_new")
                    st.info(f"💲 Ingreso libre registrado: **${cantidad:.2f}**")
                    total = cantidad
                    total_unitario = 1.0  # siempre $1
                elif not precio_valido:
                    st.error("❌ Este producto no tiene un precio válido. Verificá ingredientes y costo.")
                else:
                    cantidad = st.number_input("Cantidad vendida", min_value=1, value=1, step=1, key="cant_venta")
                    tipo_pago = st.selectbox("Tipo de pago", ["Efectivo", "Otros"], key="pago_venta")
                    descuento = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5,
                                                key="desc_venta")
                    fecha_actual = st.date_input("Fecha de actualización", key="fecha_new")
                    st.info(f"💲 Precio unitario actual: **${round(precio_actual, 2)}**")
                    total = round(precio_actual * cantidad * (1 - descuento / 100), 2)
                    total_unitario = round(precio_actual * (1 - descuento / 100), 2)
                    st.info(f"💰 Total de esta venta con descuento aplicado: **${total}**")

                if st.button("Registrar Venta", key="btn_guardar_venta"):
                    try:
                        if not producto['id'] or cantidad <= 0:
                            st.error("❌ Completá todos los datos de la venta.")
                        else:
#                            fecha_actual = date.today().isoformat()
                            producto_id = int(producto['id'])

                            cursor.execute("""
                                INSERT INTO ventas (producto_id, cantidad, tipo_pago, fecha, precio_unitario, descripcion)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (producto_id, cantidad, tipo_pago, str(fecha_actual), total_unitario, descripcion_libre))
                            conn.commit()
                            st.success(
                                f"Venta registrada correctamente – {cantidad} × {producto['nombre']} el {fecha_actual}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error al registrar la venta: {e}")
    with tab2:
        # Registrar Gastos
        st.title("💸 Registrar Gasto")

        descripcion = st.text_input("Descripción del gasto", key="desc_gasto")
        monto = st.number_input("Monto", min_value=0.0, step=10.0, key="monto_gasto")
        categoria = st.selectbox("Categoría", ["Insumos", "Alquiler", "Electricidad", "Internet", "Otros"], key="cat_gasto")
        fecha = st.date_input("Fecha del gasto", value=date.today(), key="fecha_gasto")

        if st.button("Registrar Gasto", key="btn_guardar_gasto"):
            try:
                if not descripcion or monto <= 0:
                    st.error("❌ Completá todos los datos del gasto.")
                else:
                    cursor.execute("""
                        INSERT INTO gastos (descripcion, monto, categoria, fecha)
                        VALUES (?, ?, ?, ?)
                    """, (descripcion.strip(), monto, categoria, fecha.isoformat()))
                    conn.commit()
                    st.success("✅ Gasto registrado correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Ocurrió un error al registrar el gasto: {e}")



# =========================
# Registro de Ventas y Gastos
# =========================

elif seccion == "📉 Historial":
    st.title("Historial de ventas y gastos")
    tab1, tab2, tab3 = st.tabs([
        "Ventas",
        "Gastos",
        "Dashboard"
    ])
    with tab1:
        # Visor de Ventas
        st.title("📈 Visor de Ventas")

        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date.today(), key="fecha_inicio")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="fecha_fin")

        if fecha_desde > fecha_hasta:
            st.warning("La fecha 'Desde' no puede ser posterior a 'Hasta'")
        else:
            ventas_df = pd.read_sql_query("""
                SELECT v.fecha, p.nombre AS producto, v.cantidad, v.tipo_pago, v.precio_unitario,
                       (v.cantidad * v.precio_unitario) AS total
                FROM ventas v
                LEFT JOIN productos p ON v.producto_id = p.id
                WHERE v.fecha BETWEEN ? AND ?
                ORDER BY v.fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))

            if ventas_df.empty:
                st.info("No se encontraron ventas en el rango seleccionado.")
            else:
                st.dataframe(ventas_df)

                # Total por día
                total_dia = ventas_df.groupby("fecha")["total"].sum().reset_index()
                total_dia.columns = ["Fecha", "Total del día"]
                st.subheader("💰 Total de ventas por día")
                st.table(total_dia)

                # Total general
                total_general = ventas_df["total"].sum()
                st.success(f"🧮 Total del período: **${round(total_general, 2)}**")

        # --- OPCIÓN PARA ELIMINAR UNA VENTA ---
        st.subheader("🗑️ Eliminar una venta puntual")
        ventas_id_df = pd.read_sql_query("""
                SELECT v.id, v.fecha, p.nombre AS producto, v.cantidad, (v.precio_unitario * v.cantidad) AS total
                FROM ventas v
                JOIN productos p ON v.producto_id = p.id
                WHERE v.fecha BETWEEN ? AND ?
                ORDER BY v.fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))

        if not ventas_id_df.empty:
            ventas_id_df["info"] = (
                    "ID " + ventas_id_df["id"].astype(str) +
                    " – " + ventas_id_df["producto"] +
                    " – " + ventas_id_df["fecha"] +
                    " – $" + ventas_id_df["total"].round(2).astype(str)
            )
            venta_dict = dict(zip(ventas_id_df["info"], ventas_id_df["id"]))

            venta_sel = st.selectbox("Seleccioná la venta a eliminar", list(venta_dict.keys()), key="venta_del_sel")
            venta_id = venta_dict[venta_sel]

            if st.button("❌ Eliminar esta venta", key="btn_eliminar_venta"):
                try:
                    cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
                    conn.commit()
                    st.success(f"Venta ID {venta_id} eliminada correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ocurrió un error al eliminar la venta: {e}")
        else:
            st.info("No hay ventas para eliminar en este rango.")

    with tab2:
        # Gastos
        st.title("📊 Visor de Gastos")

        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date.today(), key="fecha_inicio_gasto")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="fecha_fin_gasto")

        if fecha_desde > fecha_hasta:
            st.warning("La fecha 'Desde' no puede ser posterior a 'Hasta'")
        else:
            gastos_df = pd.read_sql_query("""
                SELECT * FROM gastos
                WHERE fecha BETWEEN ? AND ?
                ORDER BY fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))

            if gastos_df.empty:
                st.info("No se encontraron gastos en el rango seleccionado.")
            else:
                st.dataframe(gastos_df)

                total_dia = gastos_df.groupby("fecha")["monto"].sum().reset_index()
                total_dia.columns = ["Fecha", "Total del día"]
                st.subheader("💰 Total de gastos por día")
                st.table(total_dia)

                total_general = gastos_df["monto"].sum()
                st.success(f"🧾 Total de gastos del período: **${round(total_general, 2)}**")

                if st.button("📤 Exportar a Excel", key="btn_exportar_gastos"):
                    try:
                        export_path = "/tmp/gastos_filtrados.xlsx"
                        gastos_df.to_excel(export_path, index=False)
                        with open(export_path, "rb") as f:
                            st.download_button("Descargar Excel", data=f, file_name="gastos_filtrados.xlsx")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error al exportar el archivo: {e}")

    with tab3:
        # Dashboard
        st.title("📉 Dashboard – Ventas, Gastos y Ganancia Neta")
        # ID del producto "Ingreso Libre" (ajustá si llegás a cambiarlo)
        id_ingreso_libre = 31
        # Rango de fechas
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date.today().replace(day=1), key="dash_inicio")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="dash_fin")

        if fecha_desde > fecha_hasta:
            st.warning("La fecha inicial no puede ser posterior a la final.")
        else:
            import matplotlib.pyplot as plt

            agrupamiento = st.radio("Agrupar datos por:", ["Día", "Mes"], horizontal=True)

            if agrupamiento == "Mes":
                ventas_df = pd.read_sql_query("""
                    SELECT SUBSTR(fecha, 1, 7) AS periodo, SUM(cantidad * precio_unitario) AS ventas
                    FROM ventas
                    WHERE fecha BETWEEN ? AND ?
                    GROUP BY periodo
                    ORDER BY periodo
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
                gastos_df = pd.read_sql_query("""
                    SELECT SUBSTR(fecha, 1, 7) AS periodo, SUM(monto) AS gastos
                    FROM gastos
                    WHERE fecha BETWEEN ? AND ?
                    GROUP BY periodo
                    ORDER BY periodo
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
            else:
                ventas_df = pd.read_sql_query("""
                    SELECT fecha AS periodo, SUM(cantidad * precio_unitario) AS ventas
                    FROM ventas
                    WHERE fecha BETWEEN ? AND ?
                    GROUP BY periodo
                    ORDER BY periodo
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
                gastos_df = pd.read_sql_query("""
                    SELECT fecha AS periodo, SUM(monto) AS gastos
                    FROM gastos
                    WHERE fecha BETWEEN ? AND ?
                    GROUP BY periodo
                    ORDER BY periodo
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))

            df = pd.merge(ventas_df, gastos_df, on="periodo", how="outer").fillna(0)
            df["ganancia"] = df["ventas"] - df["gastos"]

            # Sumar totales según el dataframe ya agrupado y filtrado
            total_ventas = df["ventas"].sum()
            total_gastos = df["gastos"].sum()
            total_ganancia = df["ganancia"].sum()

            st.markdown(f"""
            <div style="display: flex; gap: 2rem; margin-bottom: 1rem;">
              <div style="background:#e6ffed; padding: 1em 2em; border-radius:10px; border:1px solid #b2f2bb;">
                <b>💸 Total Ingresos</b><br>
                <span style="font-size:1.5em;">${total_ventas:,.2f}</span>
              </div>
              <div style="background:#fff7e6; padding: 1em 2em; border-radius:10px; border:1px solid #ffe082;">
                <b>📤 Total Gastos</b><br>
                <span style="font-size:1.5em;">${total_gastos:,.2f}</span>
              </div>
              <div style="background:#e6f7ff; padding: 1em 2em; border-radius:10px; border:1px solid #91d5ff;">
                <b>🧮 Balance</b><br>
                <span style="font-size:1.5em; color:{"green" if total_ganancia >= 0 else "red"};">${total_ganancia:,.2f}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)


            st.dataframe(df)

            fig, ax = plt.subplots()
            ax.bar(df["periodo"], df["ventas"], label="Ventas", alpha=0.7)
            ax.bar(df["periodo"], df["gastos"], label="Gastos", alpha=0.7, bottom=df["ventas"])
            ax.plot(df["periodo"], df["ganancia"], label="Ganancia Neta", color="black", linewidth=2)
            plt.xticks(rotation=45)
            plt.title(f"Ventas, Gastos y Ganancia Neta por {agrupamiento.lower()}")
            plt.xlabel(agrupamiento)
            plt.ylabel("Monto")
            plt.legend()
            st.pyplot(fig)

        # Ventas totales por producto en el rango
        ventas_productos = pd.read_sql_query("""
            SELECT p.nombre AS producto, SUM(v.cantidad) AS unidades, SUM(v.cantidad * v.precio_unitario) AS total_ventas
            FROM ventas v
            JOIN productos p ON v.producto_id = p.id
            WHERE v.fecha BETWEEN ? AND ?
            GROUP BY p.nombre
            ORDER BY total_ventas DESC
        """, conn, params=(str(fecha_desde), str(fecha_hasta)))
        ventas_productos = ventas_productos[ventas_productos["producto"] != "Ingreso Libre"]

        if not ventas_productos.empty and ventas_productos["total_ventas"].sum() > 0:
            st.subheader("🍫 Ventas por producto")
            st.dataframe(ventas_productos)

            # Barras horizontales
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots()
            ax.barh(ventas_productos["producto"], ventas_productos["total_ventas"])
            ax.set_xlabel("Total Ventas ($)")
            ax.set_title("Ventas por producto")
            st.pyplot(fig)

            # Gráfico de torta opcional
            if len(ventas_productos) <= 8:
                fig2, ax2 = plt.subplots()
                ax2.pie(
                    ventas_productos["total_ventas"],
                    labels=ventas_productos["producto"],
                    autopct='%1.1f%%',
                    startangle=90
                )
                ax2.axis('equal')
                st.pyplot(fig2)
        else:
            st.info("No hay ventas en este rango para mostrar ventas por producto.")


        # Ganancia por producto en el rango
        ganancia_prod = pd.read_sql_query("""
            SELECT 
                p.nombre AS producto,
                SUM(v.cantidad) AS unidades,
                SUM(v.cantidad * v.precio_unitario) AS total_ventas,
                SUM(v.cantidad * p.precio_costo) AS total_costos,
                SUM(v.cantidad * (v.precio_unitario - p.precio_costo)) AS ganancia
            FROM ventas v
            JOIN productos p ON v.producto_id = p.id
            WHERE v.fecha BETWEEN ? AND ?
            GROUP BY p.nombre
            ORDER BY ganancia DESC
        """, conn, params=(str(fecha_desde), str(fecha_hasta)))
        ganancia_prod = ganancia_prod[ganancia_prod["producto"] != "Ingreso Libre"]
        
        if not ganancia_prod.empty and ganancia_prod["ganancia"].sum() > 0:
            st.subheader("💰 Ganancia por producto")
            st.dataframe(ganancia_prod)

            # Barras horizontales
            fig, ax = plt.subplots()
            ax.barh(ganancia_prod["producto"], ganancia_prod["ganancia"])
            ax.set_xlabel("Ganancia ($)")
            ax.set_title("Ganancia por producto")
            st.pyplot(fig)
        else:
            st.info("No hay ventas en este rango para mostrar ganancia por producto.")






# =========================
# Simulador de productos
# =========================

elif seccion == "🧪 Simulador de productos":

    st.title("🧪 Simulador de costo y precio de producto")

    if "simulador_ingredientes" not in st.session_state:
        st.session_state["simulador_ingredientes"] = []

    # --- Agregar ingrediente a la simulación ---
    cat_mp_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    if cat_mp_df.empty:
        st.warning("No hay categorías de materias primas.")
    else:
        cat_mp_sel = st.selectbox("Categoría de MP", cat_mp_df["nombre"].tolist(), key="sim_cat_mp")
        sub_mp_df = pd.read_sql_query("""
            SELECT sub.id, sub.nombre FROM subcategorias_mp sub
            JOIN categorias_mp cat ON sub.categoria_id = cat.id
            WHERE cat.nombre = ?
        """, conn, params=(cat_mp_sel,))
        sub_mp_dict = dict(zip(sub_mp_df["nombre"], sub_mp_df["id"]))

        if sub_mp_dict:
            sub_mp_sel = st.selectbox("Subcategoría de MP", sorted(sub_mp_dict.keys()), key="sim_subcat_mp")
            sub_mp_id = sub_mp_dict[sub_mp_sel]

            mp_df = pd.read_sql_query(
                "SELECT id, nombre, unidad, precio_por_unidad FROM materias_primas WHERE subcategoria_id = ?", conn, params=(sub_mp_id,))
            mp_dict = dict(zip(mp_df["nombre"], mp_df["id"]))

            if mp_dict:
                mp_sel = st.selectbox("Materia Prima", sorted(mp_dict.keys()), key="sim_ingred_mp_sel")
                mp_row = mp_df[mp_df["nombre"] == mp_sel].iloc[0]
                unidad = mp_row["unidad"]
                precio_por_unidad = mp_row["precio_por_unidad"]
                cant_usada = st.number_input(f"Cantidad usada ({unidad})", min_value=0.0, step=0.01, key="sim_cant_usada")

                if st.button("Agregar a simulación"):
                    # Ver si ya existe y suma cantidades
                    repetido = False
                    for ing in st.session_state["simulador_ingredientes"]:
                        if ing["nombre"] == mp_sel:
                            ing["cantidad_usada"] += cant_usada
                            ing["costo"] = round(ing["cantidad_usada"] * precio_por_unidad, 2)
                            repetido = True
                            break
                    if not repetido:
                        st.session_state["simulador_ingredientes"].append({
                            "nombre": mp_sel,
                            "unidad": unidad,
                            "cantidad_usada": cant_usada,
                            "precio_por_unidad": precio_por_unidad,
                            "costo": round(cant_usada * precio_por_unidad, 2)
                        })

    # --- Tabla editable de ingredientes simulados ---
    if st.session_state["simulador_ingredientes"]:
        sim_df = pd.DataFrame(st.session_state["simulador_ingredientes"])
        st.subheader("Ingredientes simulados")
        edited = st.data_editor(
            sim_df,
            column_config={
                "nombre": st.column_config.TextColumn("Materia Prima", disabled=True),
                "unidad": st.column_config.TextColumn("Unidad", disabled=True),
                "cantidad_usada": st.column_config.NumberColumn("Cantidad usada", min_value=0, step=0.01),
                "precio_por_unidad": st.column_config.NumberColumn("Precio por unidad", disabled=True),
                "costo": st.column_config.NumberColumn("Costo", disabled=True)
            },
            num_rows="dynamic",
            key="simulador_editor"
        )

        # Sincroniza cambios de cantidad
        cambios = False
        for idx, row in edited.iterrows():
            if not np.isclose(row["cantidad_usada"], sim_df.loc[idx, "cantidad_usada"]):
                st.session_state["simulador_ingredientes"][idx]["cantidad_usada"] = row["cantidad_usada"]
                st.session_state["simulador_ingredientes"][idx]["costo"] = round(row["cantidad_usada"] * row["precio_por_unidad"], 2)
                cambios = True
        if cambios:
            sim_df = pd.DataFrame(st.session_state["simulador_ingredientes"])

        # Botón para eliminar ingrediente
        ingr_a_borrar = st.selectbox("Eliminar ingrediente de la simulación", sim_df["nombre"].tolist(), key="simulador_borrar")
        if st.button("Eliminar ingrediente seleccionado"):
            st.session_state["simulador_ingredientes"] = [ing for ing in st.session_state["simulador_ingredientes"] if ing["nombre"] != ingr_a_borrar]
            st.experimental_rerun()

        # Calcula costo total, margen y precios
        costo_total = sim_df["costo"].sum()
        margen = st.number_input("Margen de ganancia", min_value=0.1, value=2.0, step=0.1, key="simulador_margen")
        precio_final = round(costo_total * margen, 2)
        try:
            precio_normalizado = redondeo_personalizado(precio_final)
        except:
            precio_normalizado = precio_final

        ganancia = precio_normalizado - costo_total

        st.dataframe(sim_df[["nombre", "unidad", "cantidad_usada", "precio_por_unidad", "costo"]])
        st.info(f"🧮 **Costo total:** ${costo_total:.2f}")
        st.info(f"💲 **Precio sugerido de venta:** ${precio_normalizado:.2f}")
        st.info(f"💰 **Ganancia estimada:** ${ganancia:.2f}")

        # Botón para limpiar simulación
        if st.button("Limpiar simulación"):
            st.session_state["simulador_ingredientes"] = []
            st.experimental_rerun()
    else:
        st.info("Agregá ingredientes y cantidades para simular el costo y precio del producto.")

    st.caption("Todo lo que hagas acá es SOLO simulación. No se guarda nada en la base.")
