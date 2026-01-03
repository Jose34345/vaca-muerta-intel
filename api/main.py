from fastapi import FastAPI, HTTPException
import pandas as pd
from sqlalchemy import create_engine, text
import tomllib  # <--- CAMBIO 1: Usamos la librería nativa de Python 3.11+
import os

# --- CONFIGURACIÓN ---
app = FastAPI(
    title="Vaca Muerta Intelligence API",
    version="2.0.0",
    description="Backend oficial conectado a Neon PostgreSQL"
)

# Función para obtener la conexión
# --- MODIFICACIÓN EN api/main.py ---

def get_db_engine():
    # 1. INTENTO NUBE: Buscar en variables de entorno (Render)
    db_url = os.environ.get("DATABASE_URL")
    
    if db_url:
        # Si existe en el sistema, usamos esa (Modo Nube)
        return create_engine(db_url)
    
    # 2. INTENTO LOCAL: Buscar archivo secrets.toml
    try:
        secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".streamlit", "secrets.toml")
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        connection_string = secrets["postgres"]["url"]
        return create_engine(connection_string)
    except Exception as e:
        print(f"⚠️ No se encontró configuración local ni de nube: {e}")
        return None

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "online", "message": "Bienvenido al núcleo de Vaca Muerta Intelligence"}

@app.get("/empresas")
def get_empresas():
    """Devuelve la lista de todas las operadoras disponibles en la base de datos."""
    engine = get_db_engine()
    if not engine:
        raise HTTPException(status_code=500, detail="Error de conexión a Base de Datos")
    
    try:
        # Usamos SQL directo para ser ultra rápidos
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DISTINCT empresa FROM produccion ORDER BY empresa ASC"))
            empresas = [row[0] for row in result]
        return {"total": len(empresas), "data": empresas}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/produccion/{empresa}")
def get_produccion_empresa(empresa: str):
    """Obtiene volumen Y facturación histórica para una empresa."""
    engine = get_db_engine()
    
    # QUERY MEJORADA: Incluye el cruce con precios_brent para calcular revenue
    query = text("""
        SELECT 
            p.fecha_data, 
            SUM(p.prod_pet) as petroleo, 
            SUM(p.prod_gas) as gas,
            SUM(p.prod_pet * pr.precio_usd) as revenue_usd
        FROM produccion p
        LEFT JOIN precios_brent pr ON p.anio = pr.anio AND p.mes = pr.mes
        WHERE p.empresa = :empresa
        GROUP BY p.fecha_data
        ORDER BY p.fecha_data ASC
    """)
    
    try:
        df = pd.read_sql(query, engine, params={"empresa": empresa})
        # Pandas no serializa bien las fechas a JSON por defecto, así que las convertimos a string
        if not df.empty:
            df['fecha_data'] = df['fecha_data'].astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/eficiencia/{empresa}")
def get_eficiencia_empresa(empresa: str):
    """
    Devuelve métricas operativas críticas:
    1. Producción de Agua (Costo de tratamiento).
    2. GOR (Gas-Oil Ratio): Indicador de presión y madurez del reservorio.
    """
    engine = get_db_engine()
    
    # Calculamos GOR como (Gas / Petróleo).
    # Ojo: Evitamos dividir por cero usando NULLIF
    query = text("""
        SELECT 
            fecha_data,
            SUM(prod_agua) as agua_m3,
            SUM(prod_gas) * 1000 as gas_m3, -- Ajuste de unidades si es necesario
            SUM(prod_pet) as petroleo_m3,
            CASE 
                WHEN SUM(prod_pet) > 0 THEN (SUM(prod_gas) * 1000) / SUM(prod_pet) 
                ELSE 0 
            END as gor_promedio
        FROM produccion
        WHERE empresa = :empresa
        GROUP BY fecha_data
        ORDER BY fecha_data ASC
    """)
    
    try:
        df = pd.read_sql(query, engine, params={"empresa": empresa})
        if not df.empty:
            df['fecha_data'] = df['fecha_data'].astype(str)
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}