import streamlit as st
import pandas as pd
import random

# --- Si querés usar la base real, descomentá y ajustá tu conexión:
# import psycopg2, os
# conn = psycopg2.connect(
#     host=os.getenv("DB_HOST"),
#     dbname=os.getenv("DB_NAME"),
#     user=os.getenv("DB_USER"),
#     password=os.getenv("DB_PASS"),
#     port=os.getenv("DB_PORT"),
#     sslmode="require"
# )

st.set_page_config(page_title="Chokoreto – Cartelera Visual", layout="wide")
st.title("🍫 Chokoreto – Cartelera Visual de Productos")

# --- Demo: productos ficticios con fotos random (cambiá por tu consulta real) ---
fotos_demo = [
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1519864600265-abb23847ef2c?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1458668383970-8ddd3927deed?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1502741338009-cac2772e18bc?auto=format&fit=crop&w=400&q=80",
]

prod_data = [
    {"nombre": "Tableta Amargo 70%", "categoria": "Tabletas", "subcategoria": "Amargo", "precio": 3500, "descripcion": "Tableta de chocolate amargo 70% cacao.", "foto": fotos_demo[0]},
    {"nombre": "Bombón Caramelo", "categoria": "Bombones", "subcategoria": "Relleno", "precio": 800, "descripcion": "Bombón relleno de caramelo salado.", "foto": fotos_demo[1]},
    {"nombre": "Crocante de Almendra", "categoria": "Snacks", "subcategoria": "Frutos secos", "precio": 1000, "descripcion": "Chocolate con almendras crocantes.", "foto": fotos_demo[2]},
    {"nombre": "Tableta con Leche", "categoria": "Tabletas", "subcategoria": "Leche", "precio": 3200, "descripcion": "Tableta de chocolate con leche premium.", "foto": fotos_demo[3]},
    {"nombre": "Caja Premium x 6", "categoria": "Cajas", "subcategoria": "Bombones surtidos", "precio": 4800, "descripcion": "Caja con 6 bombones variados.", "foto": fotos_demo[4]},
    {"nombre": "Trufa de Café", "categoria": "Trufas", "subcategoria": "Especiales", "precio": 900, "descripcion": "Trufa rellena con ganache de café.", "foto": fotos_demo[5]},
]
productos_df = pd.DataFrame(prod_data)

# --- Filtros ---
cat_opciones = ["Todas"] + sorted(productos_df["categoria"].unique())
categoria_filtro = st.selectbox("Filtrar por categoría", cat_opciones, key="cat_filtro")
busqueda = st.text_input("Buscar producto o subcategoría", key="busqueda_cartelera").lower()

# --- Filtrado ---
prod_filtrados = productos_df.copy()
if categoria_filtro != "Todas":
    prod_filtrados = prod_filtrados[prod_filtrados["categoria"] == categoria_filtro]
if busqueda:
    prod_filtrados = prod_filtrados[
        prod_filtrados["nombre"].str.lower().str.contains(busqueda) |
        prod_filtrados["subcategoria"].str.lower().str.contains(busqueda)
    ]

if prod_filtrados.empty:
    st.warning("No hay productos que coincidan con tu búsqueda.")
else:
    # --- Mostrar en grid elegante ---
    cols = st.columns(3)
    for i, (_, row) in enumerate(prod_filtrados.iterrows()):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div style='background:#fff; border-radius:18px; box-shadow:0 2px 8px #eee; margin-bottom:26px; overflow:hidden;'>
                    <img src="{row['foto']}" style='width:100%; aspect-ratio:1.2; object-fit:cover; border-radius:16px 16px 0 0;' alt='foto producto'/>
                    <div style='padding:16px 12px 8px 12px;'>
                        <span style='font-size:1.1em; font-weight:bold; color:#64451d;'>{row["nombre"]}</span><br>
                        <span style='font-size:0.96em; color:#977a51;'>{row["categoria"]} – {row["subcategoria"]}</span><br>
                        <span style='font-size:2em; color:#be8725; font-weight:bold;'>${row["precio"]:,.0f}</span><br>
                        <span style='color:#444;'>{row["descripcion"]}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.caption("Precios y productos actualizados. Consultá por combos y promos especiales en el local.")
