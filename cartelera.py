import streamlit as st
import pandas as pd

st.set_page_config(page_title="Chokoreto – Cartelera Modal", layout="wide")
st.title("🍫 Chokoreto – Catálogo interactivo con 'modal'")

nro_wsp = "5491123456789"

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

if "modal_abierto" not in st.session_state:
    st.session_state["modal_abierto"] = False
if "producto_modal" not in st.session_state:
    st.session_state["producto_modal"] = None

def abrir_modal(producto):
    st.session_state["modal_abierto"] = True
    st.session_state["producto_modal"] = producto

def cerrar_modal():
    st.session_state["modal_abierto"] = False
    st.session_state["producto_modal"] = None

# --- Modal: se “superpone” visualmente ---
if st.session_state["modal_abierto"] and st.session_state["producto_modal"] is not None:
    prod = st.session_state["producto_modal"]
    st.markdown(
        """
        <style>
        .fondo-modal {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(50, 40, 25, 0.60);
            z-index: 9999;
        }
        .ventana-modal {
            background: #fffbea;
            border-radius: 26px;
            box-shadow: 0 6px 34px #a97e47b2;
            padding: 44px 50px 32px 50px;
            margin: 60px auto 0 auto;
            max-width: 640px;
            z-index: 10000;
            position: relative;
        }
        .btn-cerrar {
            position:absolute;
            top:12px; right:18px;
            background:#c86e56;
            color:#fff;
            border:none;
            font-size:1.5em;
            border-radius:8px;
            padding:2px 13px;
            cursor:pointer;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # Fondo difuminado
    st.markdown("<div class='fondo-modal'></div>", unsafe_allow_html=True)
    # Ventana modal
    st.markdown("<div class='ventana-modal'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <button class="btn-cerrar" onclick="window.location.reload();">✖</button>
        <div style='text-align:center'>
            <img src="{prod['foto_principal']}" style='width:220px; border-radius:18px; margin-bottom:14px;'/><br>
            <span style='font-size:2em; font-weight:bold; color:#64451d;'>{prod["nombre"]}</span><br>
            <span style='font-size:1.15em; color:#977a51;'>{prod["categoria"]} – {prod["subcategoria"]}</span><br>
            <span style='font-size:2em; color:#be8725; font-weight:bold;'>${prod["precio"]:,.0f}</span><br>
            <span style='font-size:1.1em; color:#444;'>{prod["descripcion"]}</span><br>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.subheader("Galería de producto")
    st.image(prod["galeria"], width=170, caption=[f"{prod['nombre']} {i+1}" for i in range(len(prod["galeria"]))])
    st.markdown("---")
    st.subheader("Maridaje sugerido")
    st.markdown(f"🥃 {prod['maridaje']}")
    st.markdown("---")
    st.subheader("Fotos con clientes")
    st.image(prod["fotos_clientes"], width=60, caption=[f"Cliente {i+1}" for i in range(len(prod["fotos_clientes"]))])

    mensaje = f"Hola! Quiero consultar por el producto: {prod['nombre']}"
    link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
    st.markdown(
        f"""
        <div style='text-align:center;'>
            <a href="{link_wsp}" target="_blank" style="text-decoration:none;">
                <button style="background:#25d366; color:white; border:none; padding:10px 36px; border-radius:8px; margin-top:18px; font-size:1.15em; cursor:pointer;">
                    📲 Consultar por WhatsApp
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )
    # Botón cerrar (real, por código)
    if st.button("Cerrar", key="cerrar_modal"):
        cerrar_modal()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- Grid normal ---
else:
    if filtro.empty:
        st.warning("No hay productos que coincidan con tu búsqueda.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(filtro.iterrows()):
            with cols[i % 3]:
                mensaje = f"Hola! Quiero consultar por el producto: {row['nombre']}"
                link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
                # El truco: abrir el “modal” al clickear en la imagen
                if st.button(f"Ver más de {row['nombre']}", key=f"modal_{i}"):
                    abrir_modal(row)
                    st.rerun()
                st.image(row["foto_principal"], width=220)
                st.markdown(
                    f"""
                    <span style='font-size:1em; color:#977a51;'>{row["categoria"]} – {row["subcategoria"]}</span><br>
                    <span style='font-size:1.6em; color:#be8725; font-weight:bold;'>${row["precio"]:,.0f}</span><br>
                    <span style='color:#444;'>{row["descripcion"]}</span><br>
                    <a href="{link_wsp}" target="_blank" style="text-decoration:none;">
                        <button style="background:#25d366; color:white; border:none; padding:7px 18px; border-radius:7px; margin-top:10px; font-size:1em; cursor:pointer;">
                            📲 WhatsApp
                        </button>
                    </a>
                    """,
                    unsafe_allow_html=True
                )

st.caption("Mostrando productos premium. Para consultas, tocá WhatsApp o usá 'Ver más'.")
