import streamlit as st
import pandas as pd

st.set_page_config(page_title="Chokoreto – Cartelera Visual", layout="wide")
st.title("🍫 Chokoreto – Cartelera de Productos Premium")

nro_wsp = "5491123456789"

# --- DATOS DEMO ---
bombon_fotos = [
    "https://images.unsplash.com/photo-1519864600265-abb23847ef2c?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1458668383970-8ddd3927deed?auto=format&fit=crop&w=400&q=80",
]
tableta_fotos = [
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1502741338009-cac2772e18bc?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1464983953574-0892a716854b?auto=format&fit=crop&w=400&q=80",
]
caja_fotos = [
    "https://images.unsplash.com/photo-1468071174046-657d9d351a40?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1519864600265-abb23847ef2c?auto=format&fit=crop&w=400&q=80",
]
cliente_fotos = [
    "https://randomuser.me/api/portraits/women/1.jpg",
    "https://randomuser.me/api/portraits/men/22.jpg",
    "https://randomuser.me/api/portraits/women/43.jpg"
]

productos = [
    {
        "nombre": "Bombón Caramelo",
        "categoria": "Bombones",
        "subcategoria": "Relleno",
        "precio": 900,
        "foto_principal": bombon_fotos[0],
        "galeria": bombon_fotos,
        "descripcion": "Bombón artesanal relleno de caramelo salado, cobertura 60% cacao.",
        "maridaje": "Café espresso, Malbec suave, té negro especiado.",
        "fotos_clientes": cliente_fotos[:2]
    },
    {
        "nombre": "Tableta Amargo 70%",
        "categoria": "Tabletas",
        "subcategoria": "Amargo",
        "precio": 3200,
        "foto_principal": tableta_fotos[0],
        "galeria": tableta_fotos,
        "descripcion": "Tableta de chocolate amargo 70% con notas intensas de cacao, sin azúcar agregada.",
        "maridaje": "Vino tinto, whisky single malt, naranja confitada.",
        "fotos_clientes": cliente_fotos[1:]
    },
    {
        "nombre": "Caja Premium x 6",
        "categoria": "Cajas",
        "subcategoria": "Surtidos",
        "precio": 4800,
        "foto_principal": caja_fotos[0],
        "galeria": caja_fotos,
        "descripcion": "Caja elegante con 6 bombones variados. Ideal para regalar o disfrutar en compañía.",
        "maridaje": "Café suave, prosecco, frutos rojos frescos.",
        "fotos_clientes": cliente_fotos
    },
    {
        "nombre": "Trufa de Café",
        "categoria": "Trufas",
        "subcategoria": "Especiales",
        "precio": 1100,
        "foto_principal": bombon_fotos[2],
        "galeria": bombon_fotos[::-1],
        "descripcion": "Trufa rellena con ganache de café intenso y cobertura de chocolate amargo.",
        "maridaje": "Americano frío, whisky dulce, cerveza negra.",
        "fotos_clientes": cliente_fotos[:1]
    },
    {
        "nombre": "Tableta con Leche",
        "categoria": "Tabletas",
        "subcategoria": "Leche",
        "precio": 3100,
        "foto_principal": tableta_fotos[2],
        "galeria": tableta_fotos[::-1],
        "descripcion": "Tableta cremosa de chocolate con leche, receta belga tradicional.",
        "maridaje": "Latte, vino blanco dulce, banana deshidratada.",
        "fotos_clientes": cliente_fotos
    },
]

df = pd.DataFrame(productos)

# --- Filtros UX ---
col1, col2 = st.columns([2, 3])
with col1:
    categorias = ["Todas"] + sorted(df["categoria"].unique())
    cat_filtro = st.selectbox("Filtrar por categoría", categorias, key="cat_filtro")
with col2:
    busqueda = st.text_input("Buscar producto o subcategoría", key="busqueda_cartelera").lower()

# --- Filtrado dinámico ---
filtro = df.copy()
if cat_filtro != "Todas":
    filtro = filtro[filtro["categoria"] == cat_filtro]
if busqueda:
    filtro = filtro[
        filtro["nombre"].str.lower().str.contains(busqueda) |
        filtro["subcategoria"].str.lower().str.contains(busqueda)
    ]

# --- CONTROL DE PANTALLA: producto seleccionado ---
if "producto_seleccionado" not in st.session_state:
    st.session_state["producto_seleccionado"] = None

# --- Mostrar pantalla de detalle si corresponde ---
if st.session_state["producto_seleccionado"] is not None:
    prod = st.session_state["producto_seleccionado"]
    st.markdown(
        f"""
        <div style='background:#fff; border-radius:18px; box-shadow:0 2px 18px #d0b689; margin-bottom:26px; overflow:hidden;'>
            <img src="{prod['foto_principal']}" style='width:100%; aspect-ratio:1.9; object-fit:cover; border-radius:16px 16px 0 0;' alt='foto producto'/>
            <div style='padding:24px 32px 16px 32px;'>
                <span style='font-size:2em; font-weight:bold; color:#64451d;'>{prod["nombre"]}</span><br>
                <span style='font-size:1.1em; color:#977a51;'>{prod["categoria"]} – {prod["subcategoria"]}</span><br>
                <span style='font-size:3em; color:#be8725; font-weight:bold;'>${prod["precio"]:,.0f}</span><br>
                <span style='font-size:1.1em; color:#444;'>{prod["descripcion"]}</span><br>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.subheader("Galería de producto")
    st.image(prod["galeria"], width=230, caption=[f"{prod['nombre']} {i+1}" for i in range(len(prod["galeria"]))])

    st.markdown("---")
    st.subheader("Maridaje sugerido")
    st.markdown(f"🥃 {prod['maridaje']}")

    st.markdown("---")
    st.subheader("Fotos con clientes")
    st.image(prod["fotos_clientes"], width=90, caption=[f"Cliente {i+1}" for i in range(len(prod["fotos_clientes"]))])

    mensaje = f"Hola! Quiero consultar por el producto: {prod['nombre']}"
    link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
    st.markdown(
        f"""
        <a href="{link_wsp}" target="_blank" style="text-decoration:none;">
            <button style="background:#25d366; color:white; border:none; padding:11px 38px; border-radius:9px; margin-top:22px; font-size:1.3em; cursor:pointer;">
                📲 Consultar por WhatsApp
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.markdown("")

    if st.button("⬅️ Volver al listado", type="primary"):
        st.session_state["producto_seleccionado"] = None
        st.experimental_rerun()

# --- Si NO hay producto seleccionado, mostrar el grid (catálogo) ---
else:
    if filtro.empty:
        st.warning("No hay productos que coincidan con tu búsqueda.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(filtro.iterrows()):
            with cols[i % 3]:
                mensaje = f"Hola! Quiero consultar por el producto: {row['nombre']}"
                link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
                # El truco: cuando hace click en el nombre, se guarda el producto seleccionado en session_state
                if st.button(f"👀 {row['nombre']}", key=f"vermas_{i}"):
                    st.session_state["producto_seleccionado"] = row
                    st.experimental_rerun()
                st.image(row["foto_principal"], width=260)
                st.markdown(
                    f"""
                    <span style='font-size:1em; color:#977a51;'>{row["categoria"]} – {row["subcategoria"]}</span><br>
                    <span style='font-size:1.8em; color:#be8725; font-weight:bold;'>${row["precio"]:,.0f}</span><br>
                    <span style='color:#444;'>{row["descripcion"]}</span><br>
                    <a href="{link_wsp}" target="_blank" style="text-decoration:none;">
                        <button style="background:#25d366; color:white; border:none; padding:7px 18px; border-radius:7px; margin-top:10px; font-size:1em; cursor:pointer;">
                            📲 WhatsApp
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )

st.caption("Mostrando productos premium. Para consultas, tocá el botón WhatsApp en cada producto o en el detalle.")
