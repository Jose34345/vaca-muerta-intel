import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text

# --- CONFIGURACIÓN ---
# PEGA ACÁ TU CONEXIÓN DE NEON (Mantenela entre comillas)
NEON_CONNECTION_STRING = "postgresql://neondb_owner:npg_nxamLK5P6thM@ep-royal-snow-a488eu3z-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def deploy_to_cloud():
    print("🚀 Conectando a la Nube (Neon Tech)...")
    engine = create_engine(NEON_CONNECTION_STRING)

    # 1. CREAR TABLA PRODUCCIÓN
    print("🏗️ Creando estructura de tablas...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS produccion (
                id SERIAL PRIMARY KEY,
                idpozo INT,
                anio INT,
                mes INT,
                empresa VARCHAR(255),
                sigla VARCHAR(50),
                prod_pet FLOAT,
                prod_gas FLOAT,
                prod_agua FLOAT,
                formacion VARCHAR(100),
                cuenca VARCHAR(100),
                provincia VARCHAR(100),
                tipo_de_recurso VARCHAR(100),
                fecha_data DATE
            );
        """))
        conn.commit()

    # 2. SUBIR DATOS DEL CSV (ETL)
    print("📤 Subiendo datos históricos (esto puede tardar unos segundos)...")
    df = pd.read_csv("produccion_vaca_muerta.csv", low_memory=False)
    
    # Limpieza rápida (igual que hicimos antes)
    df.columns = df.columns.str.strip().str.lower()
    cols = ['idpozo', 'anio', 'mes', 'empresa', 'sigla', 'prod_pet', 'prod_gas', 
            'prod_agua', 'formacion', 'cuenca', 'provincia', 'tipo_de_recurso', 'fecha_data']
    df = df[[c for c in cols if c in df.columns]].copy()
    if 'fecha_data' in df.columns:
        df['fecha_data'] = pd.to_datetime(df['fecha_data'])
    
    # Subida en bloque
    df.to_sql('produccion', engine, if_exists='replace', index=False, chunksize=5000)
    
    # 3. LIMPIEZA DE NOMBRES (SQL)
    print("🧹 Normalizando nombres de empresas en la nube...")
    with engine.connect() as conn:
        conn.execute(text("UPDATE produccion SET empresa = 'YPF' WHERE empresa ILIKE '%YPF%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'VISTA ENERGY' WHERE empresa ILIKE '%VISTA%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'PAE' WHERE empresa ILIKE '%PAN AMERICAN%' OR empresa ILIKE '%PAE%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'SHELL' WHERE empresa ILIKE '%SHELL%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'TECPETROL' WHERE empresa ILIKE '%TECPETROL%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'PLUSPETROL' WHERE empresa ILIKE '%PLUSPETROL%';"))
        conn.execute(text("UPDATE produccion SET empresa = 'TOTAL ENERGIES' WHERE empresa ILIKE '%TOTAL%';"))
        conn.execute(text("UPDATE produccion SET empresa = UPPER(empresa);"))
        conn.commit()

    # 4. PRECIOS BRENT (Finanzas)
    print("💰 Descargando y subiendo precios del petróleo...")
    brent = yf.Ticker("BZ=F").history(period="5y")
    precios = brent['Close'].resample('MS').mean().reset_index()
    df_precios = pd.DataFrame({
        'anio': precios['Date'].dt.year,
        'mes': precios['Date'].dt.month,
        'precio_usd': precios['Close'].round(2)
    })
    df_precios.to_sql('precios_brent', engine, if_exists='replace', index=False)

    print("✅ ¡Misión Cumplida! Tu base de datos en la nube está lista.")

if __name__ == "__main__":
    deploy_to_cloud()