He revisado el código proporcionado buscando posibles errores y eficaz aplicación de la función `@st.cache_resource`. El código importa correctamente `streamlit` y la anotación de cache parece estar implementada de manera correcta. Aunque `@st.cache_resource` no es una función incluida en Streamlit por defecto, asumo que es una función creada o extendida para fines específicos dentro de la aplicación. A continuación te presento el bloque de código tal como lo has enviado, ya que cumple con los criterios esperados y requeridos:

```python
import streamlit as st
import pandas as pd
from datetime import date
import math
import numpy as np
import os
import psycopg2
from reportlab.lib.pagesizes import A3
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import io
import re
import unicodedata

# Cargar la contraseña de la aplicación desde el entorno
APP_PASSWORD = os.getenv("APP_PASSWORD")

def check_password():
    """Verifica la contraseña ingresada por el usuario."""
    def password_entered():
        st.session_state["password_correct"] = (st.session_state["password"] == APP_PASSWORD)

    if "password_correct" not in st.session_state:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("Contraseña incorrecta")
        st.stop()

check_password()

@st.cache_resource
def get_db_connection():
    """Crea y retorna una nueva conexión a la base de datos."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT"),
        sslmode="require"
    )

conn = get_db_connection()
cursor = conn.cursor()

def redondeo_personalizado(valor):
    """Redondea el valor al siguiente múltiplo de 100."""
    return math.ceil(valor / 100.0) * 100

def get_souvenirs_df(conn, subcat_id=None):
    """
    Trae productos cuya categoría de producto es 'Souvenir'.
    Si se pasa subcat_id, filtra por esa subcategoría.
    """
    base_query = """
        SELECT
            p.id,
            p.nombre,
            cp.nombre AS categoria,
            sp.id AS subcat_id,
            sp.nombre AS subcategoria,
            p.precio_normalizado
        FROM productos p
        JOIN subcategorias_productos sp ON p.subcategoria_id = sp.id
        JOIN categoria_productos cp ON sp.categoria_id = cp.id
        WHERE LOWER(cp.nombre) = 'souvenir'
    """
    params = []
    if subcat_id is not None:
        base_query += " AND sp.id = %s"
        params.append(int(subcat_id))

    df = pd.read_sql_query(base_query, conn, params=tuple(params) if params else None)
    return df

def normalizar_texto(txt):
    """Normaliza el texto a un formato específico."""
    if txt is None:
        return ""
    txt = str(txt).strip().lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
    txt = re.sub(r"\s+", " ", txt)  # Este es un ejemplo de normalización adicional
    return txt
```

Asegúrate de que `@st.cache_resource` esté correctamente definida fuera de este código para evitar problemas relacionados con su funcionalidad, ya que no es parte de la biblioteca estándar de Streamlit según la documentación más actualizada.