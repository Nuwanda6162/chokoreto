import streamlit as st

# Simula datos de productos
productos = [
    {
        "nombre": "Caja Premium x 6",
        "precio": 4800,
        "categoria": "Cajas",
        "subcategoria": "Surtidos",
        "foto_principal": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=400&q=80",
        "descripcion": "Caja elegante con 6 bombones variados. Ideal para regalar o disfrutar en compañía.",
        "maridaje": "Café, champagne, o té de jazmín.",
        "galeria": [
            "https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=crop&w=400&q=80",
            "https://images.unsplash.com/photo-1502741338009-cac2772e18bc?auto=format&fit=crop&w=400&q=80",
        ],
        "fotos_clientes": [
            "https://randomuser.me/api/portraits/women/21.jpg",
            "https://randomuser.me/api/portraits/men/42.jpg"
        ],
    },
    {
        "nombre": "Chocolate Amargo 70%",
        "precio": 2000,
        "categoria": "Tabletas",
        "subcategoria": "Amargos",
        "foto_principal": "https://images.unsplash.com/photo-1519864600265-abb23847ef2c?auto=format&fit=crop&w=400&q=80",
        "descripcion": "Tableta de chocolate belga 70%. Puro, intenso y con notas a frutos secos.",
        "maridaje": "Malbec, whisky, frutos rojos.",
        "galeria": [
            "https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?auto=format&fit=crop&w=400&q=80",
        ],
        "fotos_clientes": [
            "https://randomuser.me/api/portraits/women/68.jpg",
            "https://randomuser.me/api/portraits/men/35.jpg"
        ],
    },
    {
        "nombre": "Bombón Caramelo Salado",
        "precio": 950,
        "categoria": "Bombones",
        "subcategoria": "Clásicos",
        "foto_principal": "https://images.unsplash.com/photo-1505250469679-203ad9ced0cb?auto=format&fit=crop&w=400&q=80",
        "descripcion": "Caramelo salado bañado en chocolate con leche. Equilibrio perfecto entre dulce y salado.",
        "maridaje": "Café expreso o vermouth.",
        "galeria": [
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=400&q=80",
        ],
        "fotos_clientes": [
            "https://randomuser.me/api/portraits/men/72.jpg"
        ],
    },
    # ... Agregá más productos si querés
]

# --- Whatsapp config ---
nro_wsp = "5491112345678"  # Cambia por tu número real

# --- Streamlit state para modal inline ---
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

st.set_page_config(page_title="Catálogo Chokoreto", layout="wide")

st.markdown("## 🍫 Chokoreto – Catálogo interactivo (Modal Inline)")
st.caption("Catálogo con detalles extendidos: clic en una imagen para ver más info, maridaje, galería y clientes.")

# --- Filtros arriba ---
cat_opciones = ["Todas"] + sorted(list(set([p["categoria"] for p in productos])))
cat_sel = st.selectbox("Filtrar por categoría", cat_opciones, index=0)
busqueda = st.text_input("Buscar producto o subcategoría", "")

# --- Filtro aplicado ---
prod_filtrados = productos
if cat_sel != "Todas":
    prod_filtrados = [p for p in prod_filtrados if p["categoria"] == cat_sel]
if busqueda:
    busq = busqueda.lower()
    prod_filtrados = [
        p for p in prod_filtrados
        if busq in p["nombre"].lower() or busq in p["subcategoria"].lower()
    ]

# --- MODAL INLINE: si hay uno abierto, mostralo arriba de la grilla ---
if st.session_state["modal_abierto"] and st.session_state["producto_modal"] is not None:
    prod = st.session_state["producto_modal"]
    st.markdown("----")
    st.markdown(f"### 🪄 {prod['nombre']}")
    col1, col2 = st.columns([1,2])
    with col1:
        st.image(prod['foto_principal'], width=200, caption=prod["nombre"])
        st.markdown(f"**${prod['precio']:,.0f}**", unsafe_allow_html=True)
    with col2:
        st.markdown(f"**Categoría:** {prod['categoria']}  \n**Subcategoría:** {prod['subcategoria']}")
        st.markdown(f"**Descripción:** {prod['descripcion']}")
        st.markdown(f"**Maridaje sugerido:** {prod['maridaje']}")
        st.markdown("**Galería:**")
        st.image(prod["galeria"], width=110, caption=["Más fotos"]*len(prod["galeria"]))
        st.markdown("**Clientes felices:**")
        st.image(prod["fotos_clientes"], width=64)
        mensaje = f"Hola! Quiero consultar por el producto: {prod['nombre']}"
        link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
        st.markdown(f"[📲 Consultar por WhatsApp]({link_wsp})", unsafe_allow_html=True)
        if st.button("Cerrar detalle", key="cerrar_modal"):
            cerrar_modal()
            st.rerun()
    st.markdown("---")

# --- Grid de productos ---
st.markdown("### Catálogo de productos")
cols = st.columns(3)
for idx, prod in enumerate(prod_filtrados):
    with cols[idx % 3]:
        st.image(prod["foto_principal"], width=220, caption=prod["nombre"])
        st.markdown(f"**${prod['precio']:,.0f}**", unsafe_allow_html=True)
        st.caption(prod["descripcion"])
        mensaje = f"Hola! Quiero consultar por el producto: {prod['nombre']}"
        link_wsp = f"https://wa.me/{nro_wsp}?text={mensaje.replace(' ', '%20')}"
        st.markdown(f"[📲 Consultar por WhatsApp]({link_wsp})", unsafe_allow_html=True)
        # Simula "modal inline"
        if st.button(f"Ver más info de '{prod['nombre']}'", key=f"modal_{prod['nombre']}"):
            abrir_modal(prod)
            st.rerun()
