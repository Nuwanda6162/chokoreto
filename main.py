
import streamlit as st
import pandas as pd
from datetime import date
import math
import numpy as np
#from dotenv import load_dotenv
import os
import psycopg2

#load_dotenv()  # Esto carga el .env
APP_PASSWORD = os.getenv("APP_PASSWORD")

def check_password():
    def password_entered():
        if st.session_state["password"] == APP_PASSWORD:
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("Contraseña incorrecta")
        st.stop()

check_password()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    port=os.getenv("DB_PORT"),
    sslmode="require"
)
cursor = conn.cursor()




# Funcion de redondeo
def redondeo_personalizado(valor):
    if valor < 1000:
        return math.ceil(valor / 10.0) * 10
    elif valor < 10000:
        return math.ceil(valor / 100.0) * 100
    else:
        return math.ceil(valor / 100.0) * 100

def redondeo_personalizadov2(valor):
    if valor < 1000:
        return math.ceil(valor / 10.0) * 10
    elif valor < 10000:
        return math.ceil(valor / 100.0) * 100
    else:
        return math.ceil(valor / 100.0) * 100


st.set_page_config(page_title="Chokoreto App", layout="wide")
st.sidebar.title("Menú")
seccion = st.sidebar.radio("Ir a:", [
    "💵 Movimientos",
    "📉 Reportes",
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
                "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = %s",
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
                    WHERE mp.subcategoria_id = %s
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
                                        SET nombre = %s, cantidad = %s, unidad = %s, precio_compra = %s, precio_por_unidad = %s, fecha_actualizacion = %s
                                        WHERE id = %s
                                    """, (row["nombre"], row["cantidad"], row["unidad"], row["precio_compra"], ppu,
                                          str(date.today()), row["id"]))
                                    conn.commit()
                                    # Recalculo automático de productos
                                    prod_ids = pd.read_sql_query(
                                        "SELECT producto_id FROM ingredientes_producto WHERE materia_prima_id = %s",
                                        conn, params=(row["id"],)
                                    )["producto_id"].tolist()
                                    for pid in prod_ids:
                                        q = """
                                            SELECT ip.cantidad_usada, mp.precio_por_unidad
                                            FROM ingredientes_producto ip
                                            JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                                            WHERE ip.producto_id = %s
                                        """
                                        ing_df = pd.read_sql_query(q, conn, params=(pid,))
                                        costo_total = (ing_df["cantidad_usada"] * ing_df[
                                            "precio_por_unidad"]).sum() if not ing_df.empty else 0.0
                                        margen = pd.read_sql_query("SELECT margen FROM productos WHERE id = %s", conn,
                                                                   params=(pid,)).iloc[0]["margen"]
                                        precio_final = round(costo_total * margen, 2)
                                        precio_normalizado = redondeo_personalizado(precio_final)
                                        cursor.execute("""
                                            UPDATE productos
                                            SET precio_costo = %s, precio_final = %s, precio_normalizado = %s
                                            WHERE id = %s
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
            "SELECT sub.id, sub.nombre FROM subcategorias_mp sub JOIN categorias_mp cat ON sub.categoria_id = cat.id WHERE cat.nombre = %s",
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (nuevo_nombre.strip(), nueva_unidad, nueva_cant, nuevo_precio, nuevo_ppu, str(fecha_new),
                          subcat_new_id))
                    conn.commit()
                    st.success("Materia prima guardada correctamente")
                    st.rerun()
                except psycopg2.IntegrityError:
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
                            cursor.execute("UPDATE categorias_mp SET nombre = %s WHERE id = %s",
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
                    cursor.execute("INSERT INTO categorias_mp (nombre) VALUES (%s)", (nueva_cat.strip(),))
                    conn.commit()
                    st.success("¡Categoría agregada correctamente!")
                    st.rerun()
                except psycopg2.IntegrityError:
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
                            cursor.execute("UPDATE subcategorias_mp SET nombre = %s WHERE id = %s",
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
                            "INSERT INTO subcategorias_mp (nombre, categoria_id) VALUES (%s, %s)",
                            (subcat_nombre.strip(), cat_id))
                        conn.commit()
                        st.success("¡Subcategoría agregada!")
                        st.rerun()
                    except psycopg2.IntegrityError:
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
                            cursor.execute("UPDATE categoria_productos SET nombre = %s WHERE id = %s",
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
                    cursor.execute("DELETE FROM categoria_productos WHERE id = %s", (cat_id,))
                    conn.commit()
                    st.success("¡Categoría eliminada!")
                    st.rerun()
                except psycopg2.IntegrityError:
                    st.error("❌ No se puede eliminar: Hay subcategorías o productos asociados.")
                except Exception as e:
                    st.error(f"❌ Ocurrió un error inesperado: {e}")

 
        st.subheader("Nueva categoria")
        nueva_cat = st.text_input("Nueva Categoría", key="nueva_cat_prod")
        if st.button("Agregar Categoría", key="agregar_cat_prod"):
            try:
                cursor.execute("INSERT INTO categoria_productos (nombre) VALUES (%s)", (nueva_cat.strip(),))
                conn.commit()
                st.success("¡Categoría agregada correctamente!")
                st.rerun()
            except psycopg2.IntegrityError:
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
                            cursor.execute("UPDATE subcategorias_productos SET nombre = %s WHERE id = %s",
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
                WHERE cp.id = %s
            """, conn, params=(cat_sub_id,))

        if subcats_df.empty:
            st.info("No hay subcategorías cargadas para esta categoría.")
        else:
            st.dataframe(subcats_df)

        subcat_nombre = st.text_input("Nueva Subcategoría", key="nueva_subcat_prod")
        if st.button("Agregar Subcategoría", key="agregar_subcat_prod"):
            try:
                cursor.execute("INSERT INTO subcategorias_productos (nombre, categoria_id) VALUES (%s, %s)",
                               (subcat_nombre.strip(), cat_sub_id))
                conn.commit()
                st.success("¡Subcategoría agregada!")
                st.rerun()
            except psycopg2.IntegrityError:
                st.error("❌ Ya existe una subcategoría con ese nombre en esa categoría.")
            except Exception as e:
                st.error(f"❌ Ocurrió un error inesperado: {e}")


    with tab4:
        # --- Productos (ABM) ---
        st.title("🧪 Productos – ABM")
    
        # Cargar categorías y subcategorías
        cat_df = pd.read_sql_query("SELECT * FROM categoria_productos", conn)
        if not cat_df.empty:
            cat_sel = st.selectbox("Categoría de Producto", cat_df["nombre"].tolist(), key="cat_prod_abm")
            sub_df = pd.read_sql_query("""
                SELECT sp.id, sp.nombre FROM subcategorias_productos sp
                JOIN categoria_productos cp ON sp.categoria_id = cp.id
                WHERE cp.nombre = %s
            """, conn, params=(cat_sel,))
            sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))
    
            if sub_dict:
                sub_sel = st.selectbox("Subcategoría", sorted(sub_dict.keys()), key="subcat_prod_abm")
                sub_id = sub_dict[sub_sel]
    
                # --- PRODUCTOS CON PRECIOS VISIBLES Y EDITABLES ---
                productos_df = pd.read_sql_query("""
                    SELECT id, nombre, margen, precio_costo, precio_final, precio_normalizado, descripcion
                    FROM productos
                    WHERE subcategoria_id = %s
                """, conn, params=(sub_id,))
    
                if productos_df.empty:
                    st.info("No hay productos en esta subcategoría.")
                else:
                    st.subheader("Editar productos (tipo Excel)")
    
                    editable_cols = ["id", "nombre", "margen", "precio_costo", "precio_final", "precio_normalizado", "descripcion"]
                    editable_prods = productos_df[editable_cols].copy()
    
                    # Casts seguros para todos los valores
                    editable_prods["margen"] = editable_prods["margen"].astype(float)
                    editable_prods["precio_costo"] = editable_prods["precio_costo"].astype(float)
                    editable_prods["precio_final"] = editable_prods["precio_final"].astype(float)
                    editable_prods["precio_normalizado"] = editable_prods["precio_normalizado"].astype(float)
                    editable_prods["id"] = editable_prods["id"].astype(int)
                    editable_prods["descripcion"] = editable_prods["descripcion"].fillna("")
    
                    edited = st.data_editor(
                        editable_prods,
                        column_config={
                            "id": st.column_config.Column("ID", disabled=True),
                            "nombre": st.column_config.TextColumn("Nombre"),
                            "margen": st.column_config.NumberColumn("Margen", min_value=0, step=0.1),
                            "precio_costo": st.column_config.NumberColumn("Costo", disabled=True),
                            "precio_final": st.column_config.NumberColumn("Precio Final", disabled=True),
                            "precio_normalizado": st.column_config.NumberColumn("Normalizado", disabled=True),
                            "descripcion": st.column_config.TextColumn("Descripción / Notas")
                        },
                        num_rows="dynamic",
                        key="data_editor_prods"
                    )
    
                    if st.button("💾 Guardar cambios en productos"):
                        cambios = 0
                        for idx, row in edited.iterrows():
                            orig_row = editable_prods.loc[idx]
                            if (
                                row["nombre"] != orig_row["nombre"] or
                                not math.isclose(float(row["margen"]), float(orig_row["margen"])) or
                                row["descripcion"] != orig_row["descripcion"]
                            ):
                                try:
                                    nombre = row["nombre"]
                                    margen = float(row["margen"])
                                    descripcion = row["descripcion"] or ""
                                    precio_costo = float(row["precio_costo"]) if row["precio_costo"] else 0.0
                                    precio_final = round(precio_costo * margen, 2)
                                    precio_normalizado = float(redondeo_personalizado(precio_final))
                                    prod_id = int(row["id"])
                                    cursor.execute("""
                                        UPDATE productos
                                        SET nombre = %s, margen = %s, precio_final = %s, precio_normalizado = %s, descripcion = %s
                                        WHERE id = %s
                                    """, (nombre, margen, precio_final, precio_normalizado, descripcion, prod_id))
                                    conn.commit()
                                    cambios += 1
                                except psycopg2.IntegrityError:
                                    conn.rollback()
                                    st.error("❌ Ya existe un producto con ese nombre en esta subcategoría.")
                                except Exception as e:
                                    st.error(f"❌ Error al actualizar el producto ID {row['id']}: {e}")
                        if cambios:
                            st.success(f"¡Se guardaron {cambios} cambios en productos!")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")
    
                    st.caption("Editá nombre, margen o notas. Los precios se actualizan solos al guardar.")
    
                # --- Agregar nuevo producto ---
                st.subheader("Agregar nuevo producto")
                nuevo_nombre = st.text_input("Nombre nuevo", key="nombre_nuevo_prod")
                nuevo_margen = st.number_input("Margen de ganancia", min_value=0.0, step=0.1, key="margen_nuevo_prod")
                nueva_descripcion = st.text_area("Descripción / Notas", key="descripcion_nuevo_prod")
    
                if st.button("Guardar nuevo producto", key="guardar_nuevo_prod"):
                    try:
                        # Cast seguro a float
                        margen_val = float(nuevo_margen)
                        descripcion_val = nueva_descripcion or ""
                        precio_costo = 0.0  # como aún no hay ingredientes cargados
                        precio_final = round(precio_costo * margen_val, 2)
                        precio_normalizado = float(redondeo_personalizado(precio_final))
    
                        cursor.execute("""
                            INSERT INTO productos (nombre, margen, categoria_id, subcategoria_id, precio_costo, precio_final, precio_normalizado, descripcion)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            nuevo_nombre.strip(),
                            margen_val,
                            int(cat_df[cat_df["nombre"] == cat_sel]["id"].values[0]),
                            int(sub_dict[sub_sel]),
                            precio_costo,
                            precio_final,
                            precio_normalizado,
                            descripcion_val
                        ))
                        conn.commit()
                        st.success("Producto guardado correctamente")
                        st.rerun()
                    except psycopg2.IntegrityError as e:
                        conn.rollback()
                        st.error(f"❌ Error de integridad: {e}")
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error inesperado: {e}")


                # --- Eliminar producto ---
                st.subheader("❌ Eliminar producto")
                # Cargá productos de la subcategoría seleccionada (así solo aparecen los relevantes)
                productos_borrar_df = pd.read_sql_query("""
                    SELECT id, nombre FROM productos WHERE subcategoria_id = %s
                """, conn, params=(sub_id,))
                if productos_borrar_df.empty:
                    st.info("No hay productos para eliminar en esta subcategoría.")
                else:
                    prod_dict = dict(zip(productos_borrar_df["nombre"], productos_borrar_df["id"]))
                    prod_borrar_sel = st.selectbox("Seleccioná el producto a eliminar", sorted(prod_dict.keys()), key="prod_borrar_sel")
                    prod_borrar_id = prod_dict[prod_borrar_sel]
                    st.warning("⚠️ Esta acción eliminará el producto **y TODAS las ventas e ingredientes asociados**. No se puede deshacer.")
            
                    confirmar = st.checkbox("Confirmo que deseo eliminar este producto y sus datos relacionados", key="chk_confirm_del_prod")
                    if confirmar:
                        if st.button("❌ Eliminar producto seleccionado", key="btn_eliminar_prod"):
                            try:
                                # Primero borrar ingredientes y ventas asociados (si tu base no borra en cascada)
                                cursor.execute("DELETE FROM ingredientes_producto WHERE producto_id = %s", (prod_borrar_id,))
                                cursor.execute("DELETE FROM ventas WHERE producto_id = %s", (prod_borrar_id,))
                                cursor.execute("DELETE FROM productos WHERE id = %s", (prod_borrar_id,))
                                conn.commit()
                                st.success("Producto y registros asociados eliminados correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Ocurrió un error al eliminar: {e}")

            
            
            else:
                st.warning("Esta categoría no tiene subcategorías.")
        else:
            st.warning("No hay categorías de productos cargadas.")
    
        if st.button("🔄 Recalcular precios de TODOS los productos", key="recalcular_todos_prod"):
            try:
                productos = pd.read_sql_query("SELECT id, margen, precio_costo FROM productos", conn)
                cambios = 0
                for _, prod in productos.iterrows():
                    margen = float(prod["margen"])
                    precio_costo = float(prod["precio_costo"])
                    precio_final = round(precio_costo * margen, 2)
                    precio_normalizado = float(redondeo_personalizado(precio_final))
                    cursor.execute("""
                        UPDATE productos
                        SET precio_final = %s, precio_normalizado = %s
                        WHERE id = %s
                    """, (precio_final, precio_normalizado, int(prod["id"])))
                    cambios += 1
                conn.commit()
                st.success(f"¡Precios recalculados en {cambios} productos!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ocurrió un error al recalcular precios: {e}")


    
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
                    WHERE cp.nombre = %s
                """, conn, params=(cat_sel,))
            sub_dict = dict(zip(sub_df["nombre"], sub_df["id"]))

            if sub_dict:
                sub_sel = st.selectbox("Subcategoría de Producto", sorted(sub_dict.keys()), key="subcat_ing_prod")
                sub_id = sub_dict[sub_sel]

                prod_df = pd.read_sql_query(
                    "SELECT id, nombre FROM productos WHERE subcategoria_id = %s", conn, params=(sub_id,))
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
                        WHERE ip.producto_id = %s
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
                                            SET cantidad_usada = %s
                                            WHERE producto_id = %s AND materia_prima_id = %s
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
                                WHERE ip.producto_id = %s
                            """, conn, params=(prod_id,))
                        ing_dict = dict(zip(ing_df["nombre"], ing_df["id"]))

                        ing_nombre = st.selectbox("Ingrediente a eliminar", sorted(ing_dict.keys()),
                                                  key="ingred_mod_sel")
                        mp_id = ing_dict[ing_nombre]
                        mp_info = pd.read_sql_query("""
                                SELECT unidad, cantidad_usada FROM ingredientes_producto ip
                                JOIN materias_primas mp ON ip.materia_prima_id = mp.id
                                WHERE ip.producto_id = %s AND mp.id = %s
                            """, conn, params=(prod_id, mp_id)).iloc[0]

                        if st.button("Eliminar ingrediente", key="btn_eliminar_ing"):
                            try:
                                cursor.execute("""
                                          DELETE FROM ingredientes_producto
                                          WHERE producto_id = %s AND materia_prima_id = %s
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
                            WHERE cat.nombre = %s
                        """, conn, params=(cat_mp_sel,))
                    sub_mp_dict = dict(zip(sub_mp_df["nombre"], sub_mp_df["id"]))

                    if sub_mp_dict:
                        sub_mp_sel = st.selectbox("Subcategoría de MP", sorted(sub_mp_dict.keys()), key="subcat_ing_mp")
                        sub_mp_id = sub_mp_dict[sub_mp_sel]

                        mp_df = pd.read_sql_query(
                            "SELECT id, nombre, unidad FROM materias_primas WHERE subcategoria_id = %s", conn,
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
                                            VALUES (%s, %s, %s)
                                        """, (prod_id, mp_id, cant_usada))
                                    conn.commit()
                                    st.success("Ingrediente agregado")
                                    st.rerun()
                                except psycopg2.IntegrityError:
                                    st.error("❌ Ya existe ese ingrediente en este producto.")
                                except Exception as e:
                                    st.error(f"❌ Ocurrió un error inesperado: {e}")
                        else:
                            st.warning("No hay materias primas en esta subcategoría.")
                    else:
                        st.warning("Esta categoría no tiene subcategorías.")

                    # --- BOTÓN PARA ACTUALIZAR COSTO ---
                    if st.button("Actualizar costos y precios del producto", key="actualizar_costo_prod"):
                        try:
                            # 1. Traer margen actual
                            cursor.execute("SELECT margen FROM productos WHERE id = %s", (int(prod_id),))
                            margen_row = cursor.fetchone()
                            margen = float(margen_row[0]) if margen_row else 1.0
                    
                            # 2. Calcular precios
                            precio_final = round(float(costo_total) * margen, 2)
                            precio_normalizado = float(redondeo_personalizado(precio_final))
                    
                            # 3. Actualizar costo y precios
                            cursor.execute("""
                                UPDATE productos
                                SET precio_costo = %s, precio_final = %s, precio_normalizado = %s
                                WHERE id = %s
                            """, (float(costo_total), precio_final, precio_normalizado, int(prod_id)))
                            conn.commit()
                            st.success("Costo y precios actualizados en el producto")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al actualizar el costo/precio: {e}")
        
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
        st.title("📦 Registrar Venta")
    
        if st.session_state.get("venta_recien_registrada", False):
            st.session_state["desc_libre"] = ""
            st.session_state["venta_recien_registrada"] = False
    
        # Traer productos y buscador
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
            busqueda = st.text_input(
                "Buscar producto (nombre, subcategoría o categoría):",
                value="", key="busqueda_venta"
            ).lower()
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
                opciones = productos_filtrados["nombre"] + " [" + productos_filtrados["categoria"] + " / " + productos_filtrados["subcategoria"] + "]"
                prod_idx = st.selectbox("Seleccioná el producto", opciones.tolist(), key="prod_busqueda")
                producto = productos_filtrados.iloc[opciones.tolist().index(prod_idx)]
    
                precio_actual = float(producto['precio_normalizado'])
                categoria = producto['categoria']
                subcategoria = producto['subcategoria']
    
                # --- Inputs principales en columnas ---
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    cantidad = st.number_input(
                        "Cantidad", min_value=1, value=1, step=1, key="cant_venta"
                    )
                with col2:
                    tipo_pago_default = st.session_state.get("tipo_pago", "Efectivo")
                    tipo_pago = st.selectbox(
                        "Tipo de pago", ["Efectivo", "Otros"],
                        key="pago_venta",
                        index=0 if tipo_pago_default == "Efectivo" else 1
                    )
                with col3:
                    precio_unitario_manual = st.number_input(
                        "Precio unitario de venta",
                        min_value=0.01,
                        value=precio_actual,
                        step=1.0,
                        key="precio_unitario_manual"
                    )
                    st.markdown(
                        f"""
                        <div style="background:#e6f7ff; padding:10px 20px; border-radius:8px; border:1px solid #91d5ff;">
                        <b>Precio sugerido:</b> ${precio_actual:,.2f}<br>
                        <b>Categoría:</b> {categoria}<br>
                        <b>Subcategoría:</b> {subcategoria}
                        </div>
                        """, unsafe_allow_html=True
                    )
    
                # --- Opciones avanzadas ---
                with st.expander("Opciones avanzadas (descuento, fecha, descripción)"):
                    descuento = st.number_input(
                        "Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="desc_venta"
                    )
                    fecha_actual = st.date_input("Fecha de la venta", key="fecha_new")
                    descripcion_libre = st.text_area("Descripción (ej: seña, nota)", key="desc_libre")
    
                # --- Cálculo de totales ---
                precio_unitario_con_descuento = round(precio_unitario_manual * (1 - descuento / 100), 2)
                total = round(precio_unitario_con_descuento * cantidad, 2)
    
                # --- Resumen de la venta ---
                st.markdown(
                    f"""
                    <div style="background:#e6ffed; padding:10px 20px; border-radius:8px; border:1px solid #b2f2bb; margin-bottom:10px;">
                        <span style="font-size:1.2em;">💲 <b>Precio final unitario:</b> ${precio_unitario_con_descuento:,.2f}</span><br>
                        <span style="font-size:1.2em;">💰 <b>Total de esta venta:</b> ${total:,.2f}</span>
                    </div>
                    """, unsafe_allow_html=True
                )
    
                # --- Botón para registrar ---
                btn_cols = st.columns([3, 1, 3])
                with btn_cols[1]:
                    if st.button("🟢 Registrar Venta", key="btn_guardar_venta"):
                        try:
                            if not producto['id'] or cantidad <= 0 or precio_unitario_manual <= 0:
                                st.error("❌ Completá todos los datos de la venta.")
                            else:
                                producto_id = int(producto['id'])
                                import datetime
                                fecha_str = str(fecha_actual)
                                cursor.execute("""
                                    INSERT INTO ventas (producto_id, cantidad, tipo_pago, fecha, precio_unitario, descripcion)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (producto_id, cantidad, tipo_pago, fecha_str, precio_unitario_con_descuento, descripcion_libre))
                                conn.commit()
                                st.session_state["tipo_pago"] = tipo_pago
                                st.session_state['ultima_venta'] = f"{cantidad} × {producto['nombre']} ({categoria} / {subcategoria}) – ${total:,.2f} el {fecha_str}"
                                st.success(f"✅ Venta registrada: {cantidad} × {producto['nombre']} – ${total:,.2f}")
                                st.session_state["venta_recien_registrada"] = True
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al registrar la venta: {e}")
    
                # --- Mostrar la última venta registrada siempre arriba ---
                if "ultima_venta" in st.session_state:
                    st.info(f"Última venta: {st.session_state['ultima_venta']}")

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
                        VALUES (%s, %s, %s, %s)
                    """, (descripcion.strip(), monto, categoria, fecha.isoformat()))
                    conn.commit()
                    st.success("✅ Gasto registrado correctamente.")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Ocurrió un error al registrar el gasto: {e}")



# =========================
# Reportes de Ventas, gastos, etc
# =========================

elif seccion == "📉 Reportes":
    st.title("📉 Reportes")
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ventas",
        "Gastos",
        "Dashboard",
        "📊 Reportes Avanzados",
        "🍫 Ranking de chocolates por precio por gramo"
        
    ])
    with tab1:
        st.title("📈 Visor de Ventas (editable)")
        
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date.today(), key="fecha_inicio")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="fecha_fin")
        
        if fecha_desde > fecha_hasta:
            st.warning("La fecha 'Desde' no puede ser posterior a 'Hasta'")
        else:
            ventas_df = pd.read_sql_query("""
                SELECT v.id, v.fecha, p.nombre AS producto, v.cantidad, v.tipo_pago, v.precio_unitario,
                       (v.cantidad * v.precio_unitario) AS total,
                       v.descripcion
                FROM ventas v
                LEFT JOIN productos p ON v.producto_id = p.id
                WHERE v.fecha BETWEEN %s AND %s
                ORDER BY v.fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))
        
            if ventas_df.empty:
                st.info("No se encontraron ventas en el rango seleccionado.")
            else:
                # --- SETUP para edición ---
                productos_df = pd.read_sql_query("SELECT id, nombre, precio_normalizado FROM productos", conn)
                productos_lista = productos_df["nombre"].tolist()
                productos_dict = dict(zip(productos_df["nombre"], productos_df["id"]))
                productos_precio = dict(zip(productos_df["nombre"], productos_df["precio_normalizado"]))
        
                edit_cols = ["fecha", "producto", "cantidad", "tipo_pago", "descripcion"]
                editable_df = ventas_df[["id"] + edit_cols].copy()
        
                # --- Conversión y control de tipos ---
                editable_df["fecha"] = pd.to_datetime(editable_df["fecha"], errors="coerce").dt.date
                if not editable_df["producto"].isin(productos_lista).all():
                    editable_df.loc[~editable_df["producto"].isin(productos_lista), "producto"] = productos_lista[0]
                if not editable_df["tipo_pago"].isin(["Efectivo", "Otros"]).all():
                    editable_df.loc[~editable_df["tipo_pago"].isin(["Efectivo", "Otros"]), "tipo_pago"] = "Efectivo"
                editable_df = editable_df.fillna({"descripcion": ""})
                editable_df["cantidad"] = editable_df["cantidad"].astype(float)
        
                column_config = {
                    "id": st.column_config.Column("ID", disabled=True),
                    "fecha": st.column_config.DateColumn("Fecha"),
                    "producto": st.column_config.SelectboxColumn("Producto", options=productos_lista),
                    "cantidad": st.column_config.NumberColumn("Cantidad / Importe", min_value=0, step=1),
                    "tipo_pago": st.column_config.SelectboxColumn("Tipo de pago", options=["Efectivo", "Otros"]),
                    "descripcion": st.column_config.TextColumn("Descripción"),
                }
        
                # --- Expander para edición ---
                with st.expander("Editar ventas (abrir solo si necesitás cambiar algo)", expanded=False):
                    edited = st.data_editor(
                        editable_df,
                        column_config=column_config,
                        num_rows="dynamic",
                        key="ventas_editor"
                    )
        
                    if st.button("💾 Guardar cambios en ventas"):
                        cambios = 0
                        for idx, row in edited.iterrows():
                            orig_row = editable_df.loc[idx]
                            if not (row == orig_row).all():
                                prod_id = productos_dict[row["producto"]]
                                if row["producto"].lower() in ["ingreso libre", "seña", "adelanto", "varios", "otros"]:
                                    # Importe libre
                                    precio_unitario = 1
                                    cantidad = row["cantidad"]  # Cantidad = importe recibido
                                else:
                                    precio_unitario = productos_precio[row["producto"]]
                                    cantidad = row["cantidad"]
                                cursor.execute("""
                                    UPDATE ventas
                                    SET fecha = %s, producto_id = %s, cantidad = %s, tipo_pago = %s, descripcion = %s, precio_unitario = %s
                                    WHERE id = %s
                                """, (row["fecha"], prod_id, cantidad, row["tipo_pago"], row["descripcion"], precio_unitario, row["id"]))
                                cambios += 1
                        conn.commit()
                        if cambios:
                            st.success(f"¡Se guardaron {cambios} cambios en ventas!")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")
        
                # --- Tabla historial de ventas (siempre visible, no editable) ---
                ventas_df = pd.read_sql_query("""
                    SELECT v.id, v.fecha, p.nombre AS producto, v.cantidad, v.tipo_pago, v.precio_unitario,
                           (v.cantidad * v.precio_unitario) AS total,
                           v.descripcion
                    FROM ventas v
                    LEFT JOIN productos p ON v.producto_id = p.id
                    WHERE v.fecha BETWEEN %s AND %s
                    ORDER BY v.fecha DESC
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
                st.dataframe(ventas_df)
        
                # --- Opción para eliminar una venta puntual ---
                st.subheader("🗑️ Eliminar una venta puntual")
                ventas_df["info"] = (
                    "ID " + ventas_df["id"].astype(str) +
                    " – " + ventas_df["producto"] +
                    " – " + ventas_df["fecha"].astype(str) +
                    " – $" + ventas_df["total"].round(2).astype(str)
                )
                venta_dict = dict(zip(ventas_df["info"], ventas_df["id"]))
        
                if venta_dict:
                    venta_sel = st.selectbox("Seleccioná la venta a eliminar", list(venta_dict.keys()), key="venta_del_sel")
                    venta_id = venta_dict[venta_sel]
        
                    if st.button("❌ Eliminar esta venta", key="btn_eliminar_venta"):
                        try:
                            cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
                            conn.commit()
                            st.success(f"Venta ID {venta_id} eliminada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al eliminar la venta: {e}")
                else:
                    st.info("No hay ventas para eliminar en este resultado.")
        
                # --- Totales por día ---
                total_dia = ventas_df.groupby("fecha")["total"].sum().reset_index()
                total_dia.columns = ["Fecha", "Total del día"]
                st.subheader("💰 Total de ventas por día")
                st.table(total_dia)
        
                total_general = ventas_df["total"].sum()
                st.success(f"🧮 Total del período: **${round(total_general, 2)}**")

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
                SELECT id, fecha, descripcion, monto, categoria
                FROM gastos
                WHERE fecha BETWEEN %s AND %s
                ORDER BY fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))
        
            if gastos_df.empty:
                st.info("No se encontraron gastos en el rango seleccionado.")
            else:
                # ---- Setup y chequeo de tipos ----
                edit_cols = ["fecha", "descripcion", "monto", "categoria"]
                editable_df = gastos_df[["id"] + edit_cols].copy()
        
                editable_df["fecha"] = pd.to_datetime(editable_df["fecha"], errors="coerce").dt.date
                categorias_validas = ["Insumos", "Alquiler", "Electricidad", "Internet", "Otros"]
                if not editable_df["categoria"].isin(categorias_validas).all():
                    editable_df.loc[~editable_df["categoria"].isin(categorias_validas), "categoria"] = categorias_validas[0]
                editable_df["monto"] = editable_df["monto"].astype(float)
                editable_df = editable_df.fillna({"descripcion": ""})
        
                column_config = {
                    "id": st.column_config.Column("ID", disabled=True),
                    "fecha": st.column_config.DateColumn("Fecha"),
                    "descripcion": st.column_config.TextColumn("Descripción"),
                    "monto": st.column_config.NumberColumn("Monto", min_value=0.0, step=10.0),
                    "categoria": st.column_config.SelectboxColumn("Categoría", options=categorias_validas),
                }
        
                with st.expander("Editar gastos (abrir solo si necesitás cambiar algo)", expanded=False):
                    edited = st.data_editor(
                        editable_df,
                        column_config=column_config,
                        num_rows="dynamic",
                        key="gastos_editor"
                    )
        
                    if st.button("💾 Guardar cambios en gastos"):
                        cambios = 0
                        for idx, row in edited.iterrows():
                            orig_row = editable_df.loc[idx]
                            if not (row == orig_row).all():
                                cursor.execute("""
                                    UPDATE gastos
                                    SET fecha = %s, descripcion = %s, monto = %s, categoria = %s
                                    WHERE id = %s
                                """, (row["fecha"], row["descripcion"], row["monto"], row["categoria"], row["id"]))
                                cambios += 1
                        conn.commit()
                        if cambios:
                            st.success(f"¡Se guardaron {cambios} cambios en gastos!")
                            st.rerun()
                        else:
                            st.info("No hubo cambios para guardar.")
        
                # --- Tabla de historial (no editable) ---
                gastos_df = pd.read_sql_query("""
                    SELECT fecha, descripcion, monto, categoria
                    FROM gastos
                    WHERE fecha BETWEEN %s AND %s
                    ORDER BY fecha DESC
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
                st.dataframe(gastos_df)
        
                # --- Totales por día ---
                total_dia = gastos_df.groupby("fecha")["monto"].sum().reset_index()
                total_dia.columns = ["Fecha", "Total del día"]
                st.subheader("💰 Total de gastos por día")
                st.table(total_dia)
        
                total_general = gastos_df["monto"].sum()
                st.success(f"🧾 Total de gastos del período: **${round(total_general, 2)}**")

                st.subheader("🗑️ Eliminar un gasto puntual")
                
                # Cargá de nuevo los gastos en el rango, con IDs
                gastos_id_df = pd.read_sql_query("""
                    SELECT id, fecha, descripcion, monto, categoria
                    FROM gastos
                    WHERE fecha BETWEEN %s AND %s
                    ORDER BY fecha DESC
                """, conn, params=(str(fecha_desde), str(fecha_hasta)))
                
                if not gastos_id_df.empty:
                    gastos_id_df["info"] = (
                        "ID " + gastos_id_df["id"].astype(str) +
                        " – " + gastos_id_df["descripcion"] +
                        " – " + gastos_id_df["fecha"] +
                        " – $" + gastos_id_df["monto"].round(2).astype(str)
                    )
                    gasto_dict = dict(zip(gastos_id_df["info"], gastos_id_df["id"]))
                
                    gasto_sel = st.selectbox("Seleccioná el gasto a eliminar", list(gasto_dict.keys()), key="gasto_del_sel")
                    gasto_id = gasto_dict[gasto_sel]
                
                    if st.button("❌ Eliminar este gasto", key="btn_eliminar_gasto"):
                        try:
                            cursor.execute("DELETE FROM gastos WHERE id = %s", (gasto_id,))
                            conn.commit()
                            st.success(f"Gasto ID {gasto_id} eliminado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Ocurrió un error al eliminar el gasto: {e}")
                else:
                    st.info("No hay gastos para eliminar en este rango.")
    
    
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
            ventas_df = pd.read_sql_query("""
                SELECT v.fecha, p.nombre AS producto, v.cantidad, v.tipo_pago, v.precio_unitario,
                    (v.cantidad * v.precio_unitario) AS total
                FROM ventas v
                LEFT JOIN productos p ON v.producto_id = p.id
                WHERE v.fecha BETWEEN %s AND %s
                ORDER BY v.fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))
    
            gastos_df = pd.read_sql_query("""
                SELECT * FROM gastos
                WHERE fecha BETWEEN %s AND %s
                ORDER BY fecha DESC
            """, conn, params=(str(fecha_desde), str(fecha_hasta)))        

        modo_agrupacion = st.radio("Agrupar datos por:", ["Día", "Mes"], horizontal=True)

        if modo_agrupacion == "Día":
            ventas_df["periodo"] = pd.to_datetime(ventas_df["fecha"]).dt.strftime("%d/%m/%Y")
            gastos_df["periodo"] = pd.to_datetime(gastos_df["fecha"]).dt.strftime("%d/%m/%Y")
        else:
            ventas_df["periodo"] = pd.to_datetime(ventas_df["fecha"]).dt.strftime("%m/%Y")
            gastos_df["periodo"] = pd.to_datetime(gastos_df["fecha"]).dt.strftime("%m/%Y")
        
        # --------- Agrupación por periodo ---------
        ventas_agrup = ventas_df.groupby("periodo").agg({"total":"sum"}).rename(columns={"total": "ventas"})
        gastos_agrup = gastos_df.groupby("periodo").agg({"monto":"sum"}).rename(columns={"monto": "gastos"})
        
        # --------- Unificá los períodos para gráficos ---------
        periodos = pd.DataFrame(index=ventas_agrup.index.union(gastos_agrup.index).sort_values())
        periodos["ventas"] = ventas_agrup["ventas"]
        periodos["gastos"] = gastos_agrup["gastos"]
        periodos = periodos.fillna(0)
        periodos["balance"] = periodos["ventas"] - periodos["gastos"]
        
        # --------- Cards de resumen ---------
        total_ventas = ventas_df["total"].sum() if not ventas_df.empty else 0
        total_gastos = gastos_df["monto"].sum() if not gastos_df.empty else 0
        total_ganancia = total_ventas - total_gastos
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div style='background:#e6ffed; padding:1.5em; border-radius:12px; text-align:center; border:1px solid #b2f2bb;'><b>💸 Total Ingresos</b><br><span style='font-size:2em;'>${total_ventas:,.2f}</span></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='background:#fff7e6; padding:1.5em; border-radius:12px; text-align:center; border:1px solid #ffe082;'><b>📤 Total Gastos</b><br><span style='font-size:2em;'>${total_gastos:,.2f}</span></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='background:#e6f7ff; padding:1.5em; border-radius:12px; text-align:center; border:1px solid #91d5ff;'><b>🧮 Balance</b><br><span style='font-size:2em; color:{'green' if total_ganancia>=0 else 'red'};'>${total_ganancia:,.2f}</span></div>", unsafe_allow_html=True)
        
        st.divider()
        
        # --------- Gráfico de barras de ventas y gastos ---------
        st.subheader(f"Evolución {'diaria' if modo_agrupacion == 'Día' else 'mensual'} de Ventas y Gastos")
        st.bar_chart(periodos[["ventas", "gastos"]])
        
        # --------- Gráfico de balance ---------
        st.subheader(f"Balance {'diario' if modo_agrupacion == 'Día' else 'mensual'}")
        st.line_chart(periodos["balance"])
        
        # --------- Top productos vendidos ---------
        st.subheader("Top productos más vendidos")
        if not ventas_df.empty:
            top_prod = ventas_df.groupby("producto").agg({"cantidad":"sum", "total":"sum"}).sort_values("total", ascending=False).head(10)
            st.dataframe(top_prod, height=320)
        else:
            st.info("No hay ventas en el periodo.")
        
        # --------- Gastos por categoría ---------
        st.subheader("Gastos por categoría")
        if not gastos_df.empty:
            gastos_cat = gastos_df.groupby("categoria")["monto"].sum().sort_values(ascending=False)
            st.bar_chart(gastos_cat)
        else:
            st.info("No hay gastos en el periodo.")
        
        # --------- Tablas completas en expanders ---------
        with st.expander("Ver tabla completa de ventas"):
            st.dataframe(ventas_df)
        
        with st.expander("Ver tabla completa de gastos"):
            st.dataframe(gastos_df)
        
    with tab4:
        # =========================================
        # REPORTES AVANZADOS – PRODUCTOS
        # =========================================
        
        st.title("📊 Reportes Avanzados")
        
        # -----------------------------------------
        # 1. REPORTE GENERAL DE PRODUCTOS Y VENTAS
        # -----------------------------------------
        
        st.header("📦 Resumen de productos, ventas y filtros")
        
        # --- Filtros dinámicos de fecha ---
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Fecha desde (opcional)", value=None, key="filtro_fecha_desde")
        with col2:
            fecha_hasta = st.date_input("Fecha hasta (opcional)", value=None, key="filtro_fecha_hasta")
        
        # --- Filtros dinámicos de categoría/subcategoría ---
        categorias = pd.read_sql_query("SELECT id, nombre FROM categoria_productos ORDER BY nombre", conn)
        subcategorias = pd.read_sql_query("SELECT id, nombre, categoria_id FROM subcategorias_productos", conn)
        
        # Opciones "Ver todos"
        cat_opciones = ["(Ver todas)"] + categorias["nombre"].tolist()
        cat_sel = st.selectbox("Filtrar por categoría", cat_opciones, key="filtro_categoria")
        if cat_sel == "(Ver todas)":
            cat_ids = categorias["id"].tolist()
        else:
            cat_ids = [int(categorias[categorias["nombre"] == cat_sel]["id"].iloc[0])]
        
        # Filtra subcats por categoría elegida
        subcat_opciones = ["(Ver todas)"]
        if cat_sel == "(Ver todas)":
            subcat_opciones += subcategorias["nombre"].tolist()
        else:
            subcat_opciones += subcategorias[subcategorias["categoria_id"].isin(cat_ids)]["nombre"].tolist()
        subcat_sel = st.selectbox("Filtrar por subcategoría", subcat_opciones, key="filtro_subcat")
        
        if subcat_sel == "(Ver todas)":
            subcat_ids = subcategorias[subcategorias["categoria_id"].isin(cat_ids)]["id"].tolist()
        else:
            subcat_ids = [int(subcategorias[subcategorias["nombre"] == subcat_sel]["id"].iloc[0])]
        
        # --- Traé todos los productos filtrados ---
        productos_query = """
        SELECT p.id, p.nombre, cp.nombre AS categoria, sp.nombre AS subcategoria,
               p.precio_costo, p.margen, p.precio_final, p.precio_normalizado
        FROM productos p
        JOIN subcategorias_productos sp ON p.subcategoria_id = sp.id
        JOIN categoria_productos cp ON sp.categoria_id = cp.id
        WHERE sp.id = ANY(%s)
        """
        productos_df = pd.read_sql_query(productos_query, conn, params=(subcat_ids,))
        
        # --- Traé ventas (en el rango pedido, si hay filtro) ---
        ventas_query = """
        SELECT v.producto_id, SUM(v.cantidad) AS cantidad_vendida, SUM(v.cantidad * v.precio_unitario) AS total_vendido
        FROM ventas v
        WHERE v.producto_id = ANY(%s)
        """
        ventas_params = [productos_df["id"].tolist()]
        if fecha_desde and fecha_hasta:
            ventas_query += " AND v.fecha BETWEEN %s AND %s"
            ventas_params += [str(fecha_desde), str(fecha_hasta)]
        ventas_query += " GROUP BY v.producto_id"
        
        ventas_df = pd.read_sql_query(ventas_query, conn, params=ventas_params) if not productos_df.empty else pd.DataFrame(columns=["producto_id", "cantidad_vendida", "total_vendido"])
        
        # --- Merge productos y ventas ---
        rep_df = productos_df.merge(ventas_df, left_on="id", right_on="producto_id", how="left").fillna({"cantidad_vendida": 0, "total_vendido": 0})
        rep_df["cantidad_vendida"] = rep_df["cantidad_vendida"].astype(int)
        rep_df["total_vendido"] = rep_df["total_vendido"].astype(float)
        
        # --- Reordena y muestra la tabla ---
        rep_df = rep_df[["categoria", "subcategoria", "nombre", "precio_costo", "margen", "precio_final", "precio_normalizado", "cantidad_vendida", "total_vendido"]]
        rep_df.columns = ["Categoría", "Subcategoría", "Producto", "Costo", "Margen", "Precio Final", "Precio Normalizado", "Vendidos", "Total vendido"]
        
        st.dataframe(rep_df, height=500, hide_index=True)
        
    with tab5:
        # -----------------------------------------
        # 2. REPORTE PRECIO POR GRAMO – CHOCOLATES
        # -----------------------------------------
        
        st.header("🍫 Ranking de chocolates por precio por gramo (materias primas)")
        
        # Traé las materias primas con categoría "Chocolate"
        mp_df = pd.read_sql_query("""
            SELECT mp.nombre, cat.nombre AS categoria, mp.precio_por_unidad
            FROM materias_primas mp
            JOIN subcategorias_mp sub ON mp.subcategoria_id = sub.id
            JOIN categorias_mp cat ON sub.categoria_id = cat.id
            WHERE LOWER(cat.nombre) = 'chocolate'
            ORDER BY mp.precio_por_unidad ASC
        """, conn)
        
        if mp_df.empty:
            st.info("No hay materias primas de chocolate cargadas en la base.")
        else:
            mp_df = mp_df.rename(columns={
                "nombre": "Materia Prima",
                "categoria": "Categoría",
                "precio_por_unidad": "Precio por gramo"
            })
            st.dataframe(mp_df[["Materia Prima", "Precio por gramo"]], hide_index=True)






# =========================
# Simulador de productos
# =========================

elif seccion == "🧪 Simulador de productos":

    st.title("🧪 Simulador de costo y precio de producto")
    
    st.info("💡 *Usá este simulador para experimentar con recetas, ver cuánto costaría un producto nuevo o ajustar una receta existente. Agregá ingredientes, modificá cantidades y márgenes. **Nada se guarda**: es solo para probar.*")
    
    if "simulador_ingredientes" not in st.session_state:
        st.session_state["simulador_ingredientes"] = []
#    if "sim_cant_usada" not in st.session_state:
#        st.session_state["sim_cant_usada"] = 1.0
    
    # --- Agregar ingrediente a la simulación ---
    cat_mp_df = pd.read_sql_query("SELECT * FROM categorias_mp", conn)
    if cat_mp_df.empty:
        st.warning("No hay categorías de materias primas.")
    else:
        # --- Cambiá el flujo: primero selectbox de MP, luego cantidad, luego agregar ---
        cat_mp_sel = st.selectbox("Categoría de MP", cat_mp_df["nombre"].tolist(), key="sim_cat_mp")
        sub_mp_df = pd.read_sql_query("""
            SELECT sub.id, sub.nombre FROM subcategorias_mp sub
            JOIN categorias_mp cat ON sub.categoria_id = cat.id
            WHERE cat.nombre = %s
        """, conn, params=(cat_mp_sel,))
        sub_mp_dict = dict(zip(sub_mp_df["nombre"], sub_mp_df["id"]))
    
        if sub_mp_dict:
            sub_mp_sel = st.selectbox("Subcategoría de MP", sorted(sub_mp_dict.keys()), key="sim_subcat_mp")
            sub_mp_id = sub_mp_dict[sub_mp_sel]
    
            mp_df = pd.read_sql_query(
                "SELECT id, nombre, unidad, precio_por_unidad FROM materias_primas WHERE subcategoria_id = %s", conn, params=(sub_mp_id,))
            mp_dict = dict(zip(mp_df["nombre"], mp_df["id"]))
    
            if mp_dict:
                mp_sel = st.selectbox("Materia Prima", sorted(mp_dict.keys()), key="sim_ingred_mp_sel")
                mp_row = mp_df[mp_df["nombre"] == mp_sel].iloc[0]
                unidad = mp_row["unidad"]
                precio_por_unidad = mp_row["precio_por_unidad"]
                # --- Siempre default 1.0 ---
                cant_usada = st.number_input(f"Cantidad usada ({unidad})", min_value=0.0, value=1.0, step=0.1, key="sim_cant_usada")
    
                if st.button("Agregar a simulación"):
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
#                    # --- Resetea cantidad a 1.0 para sumar más fácil ---
#                    st.session_state["sim_cant_usada"] = 1.0
    
    # --- Tabla editable de ingredientes simulados (mostrar siempre, aunque esté vacía) ---
    sim_df = pd.DataFrame(st.session_state["simulador_ingredientes"])
    st.subheader("Ingredientes simulados")
    if not sim_df.empty:
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
    
        ingr_a_borrar = st.selectbox("Eliminar ingrediente de la simulación", sim_df["nombre"].tolist(), key="simulador_borrar")
        if st.button("Eliminar ingrediente seleccionado"):
            st.session_state["simulador_ingredientes"] = [ing for ing in st.session_state["simulador_ingredientes"] if ing["nombre"] != ingr_a_borrar]
            st.rerun()
    else:
        st.info("Sumá ingredientes para simular el costo y precio.")
    
    # --- Calcula costo total, margen y precios ---
    costo_total = sim_df["costo"].sum() if not sim_df.empty else 0.0
    margen = st.number_input("Margen de ganancia", min_value=0.1, value=3.0, step=0.1, key="simulador_margen")
    descuento = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key="simulador_descuento")
    precio_final = round(costo_total * margen, 2)
    try:
        precio_normalizado = redondeo_personalizado(precio_final)
    except:
        precio_normalizado = precio_final
    
    precio_con_descuento = round(precio_normalizado * (1 - descuento / 100), 2)
    ganancia = precio_con_descuento - costo_total
    
    if not sim_df.empty:
        st.info(f"🧮 **Costo total:** ${costo_total:.2f}")
        st.info(f"💲 **Precio sugerido de venta (sin descuento):** ${precio_normalizado:.2f}")
        st.info(f"💲 **Precio con descuento aplicado:** ${precio_con_descuento:.2f}")
        st.info(f"💰 **Ganancia estimada (con descuento):** ${ganancia:.2f}")
    else:
        st.info("Sumá ingredientes para simular el costo y precio.")
    
    if st.button("Limpiar simulación"):
        st.session_state["simulador_ingredientes"] = []
        st.rerun()
