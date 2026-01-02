import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
# Importamos la función de Inteligencia Artificial que creamos en el otro archivo
from ml_forecasting import predecir_produccion 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Vaca Muerta Intelligence",
    page_icon="🛢️",
    layout="wide"
)

# --- CONEXIÓN A BASE DE DATOS (SEGURA) ---
@st.cache_resource
def init_connection():
    # Ahora lee la contraseña desde el archivo de secretos o de la nube
    # st.secrets lee automáticamente el archivo .streamlit/secrets.toml localmente
    # o los secretos de la nube cuando estemos en Streamlit Cloud.
    try:
        db_connection_str = st.secrets["postgres"]["url"]
        return create_engine(db_connection_str)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- ¡CORRECCIÓN AQUÍ! ---
# Ejecutamos la función para crear la variable 'engine'
engine = init_connection()
# -------------------------

# --- FUNCIÓN DE CARGA DE DATOS SQL ---
@st.cache_data(ttl=3600)
def cargar_datos_sql():
    # Verificamos que el engine exista antes de usarlo
    if engine is None:
        return pd.DataFrame()

    try:
        # QUERY COMPLETA: VOLUMEN + PRECIOS
        query = """
        SELECT 
            p.empresa, 
            p.fecha_data as fecha, 
            p.prod_pet, 
            p.prod_gas, 
            pr.precio_usd as precio_brent,
            (p.prod_pet * pr.precio_usd) as revenue_usd
        FROM produccion p
        LEFT JOIN precios_brent pr ON p.anio = pr.anio AND p.mes = pr.mes
        WHERE p.formacion ILIKE '%%VACA%%' OR p.formacion ILIKE '%%VM%%'
        ORDER BY p.fecha_data ASC;
        """
        
        df = pd.read_sql(query, engine)
        df['fecha'] = pd.to_datetime(df['fecha'])
        return df
    except Exception as e:
        st.error(f"❌ Error SQL: {e}")
        return pd.DataFrame()

# --- INTERFAZ DE USUARIO ---
st.title("🛢️ Vaca Muerta Intelligence (Powered by SQL)")
st.markdown("Monitor de producción, rentabilidad y predicción IA conectado a PostgreSQL.")

data = cargar_datos_sql()

if not data.empty:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros")
    
    lista_operadoras = sorted(data['empresa'].unique())
    operadoras_sel = st.sidebar.multiselect(
        "Operadora",
        lista_operadoras,
        default=lista_operadoras[:3] if len(lista_operadoras) > 0 else None
    )
    
    if operadoras_sel:
        df_view = data[data['empresa'].isin(operadoras_sel)]
    else:
        df_view = data

    # --- KPI METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    total_revenue = df_view['revenue_usd'].sum()
    
    c1.metric("Petróleo (m³)", f"{df_view['prod_pet'].sum():,.0f}")
    c2.metric("Gas (Mm³)", f"{df_view['prod_gas'].sum():,.0f}")
    c3.metric("Registros SQL", f"{len(df_view):,}")
    c4.metric("Facturación Estimada", f"US$ {total_revenue/1_000_000:,.1f} M")

    st.markdown("---")

    # --- PESTAÑAS DE ANÁLISIS ---
    tab_volumen, tab_dinero, tab_ia = st.tabs(["🛢️ Volumen", "💵 Flujo de Caja", "🔮 Predicción IA"])

    # 1. VOLUMEN
    with tab_volumen:
        st.subheader("Tendencia de Producción Física")
        df_chart = df_view.groupby(['fecha', 'empresa'])[['prod_pet']].sum().reset_index()
        fig_vol = px.line(
            df_chart, x='fecha', y='prod_pet', color='empresa',
            title="Curva de Producción de Petróleo", markers=True
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # 2. DINERO
    with tab_dinero:
        st.subheader("Competencia Financiera")
        col_rank, col_pie = st.columns([2, 1])
        
        df_rank = df_view.groupby('empresa')[['revenue_usd']].sum().reset_index()
        df_rank = df_rank.sort_values('revenue_usd', ascending=True).tail(10)
        
        with col_rank:
            fig_rank = px.bar(
                df_rank, x='revenue_usd', y='empresa', orientation='h', 
                text_auto='.2s', title="Top 10 Operadoras por Facturación (US$)",
                color='revenue_usd', color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_rank, use_container_width=True)
            
        with col_pie:
            fig_pie = px.pie(
                df_rank, values='revenue_usd', names='empresa',
                title="Market Share", hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        st.info("💡 Insight: Estimación bruta (Producción x Brent Mensual).")

    # 3. PREDICCIÓN IA (FORECASTING) CORREGIDO
    with tab_ia:
        st.subheader("Proyección de Producción (12 Meses)")
        st.markdown("Modelo de **Regresión Polinómica** aplicado sobre la producción total de la compañía.")

        empresa_pred = st.selectbox("Seleccionar Operadora para Simular:", operadoras_sel if operadoras_sel else lista_operadoras)
        
        if empresa_pred:
            # --- CORRECCIÓN CLAVE: AGRUPACIÓN DE DATOS ---
            # 1. Filtramos por empresa
            df_filtered = df_view[df_view['empresa'] == empresa_pred]
            
            # 2. AGRUPAMOS por fecha y SUMAMOS (Esto arregla el gráfico de "electrocardiograma")
            df_empresa = df_filtered.groupby('fecha')[['prod_pet']].sum().reset_index()
            df_empresa = df_empresa.sort_values('fecha')
            
            if len(df_empresa) > 6:
                with st.spinner(f"Entrenando cerebro digital para {empresa_pred}..."):
                    # Ahora le pasamos la SUMA mensual, no los pozos sueltos
                    df_prediccion = predecir_produccion(df_empresa)
                
                # Unir datos para visualizar
                df_hist = df_empresa.copy()
                df_hist['tipo'] = 'Dato Real'
                df_hist.rename(columns={'prod_pet': 'produccion'}, inplace=True)
                
                df_prediccion.rename(columns={'prod_pet_pred': 'produccion'}, inplace=True)
                df_total = pd.concat([df_hist, df_prediccion])
                
                # Graficar
                fig_forecast = px.line(
                    df_total, x='fecha', y='produccion', color='tipo',
                    title=f"Proyección Agregada 2026: {empresa_pred}", markers=True,
                    color_discrete_map={"Dato Real": "blue", "Predicción IA": "orange"}
                )
                
                # Línea de "Hoy"
                fig_forecast.add_vline(
                    x=pd.Timestamp.now().timestamp() * 1000, 
                    line_dash="dash", 
                    line_color="green", 
                    annotation_text="Hoy"
                )
                
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                # Insight final
                if not df_hist.empty and not df_prediccion.empty:
                    ultimo_real = df_hist['produccion'].iloc[-1]
                    ultimo_pred = df_prediccion['produccion'].iloc[-1]
                    
                    # Evitamos división por cero
                    if ultimo_real > 0:
                        variacion = ((ultimo_pred - ultimo_real) / ultimo_real) * 100
                        
                        if variacion > 0:
                            st.success(f"📈 Tendencia: Crecimiento proyectado del **{variacion:.1f}%** (Volumen Total).")
                        else:
                            st.warning(f"📉 Tendencia: Declino proyectado del **{variacion:.1f}%** (Volumen Total).")
                    else:
                        st.info("Datos insuficientes en el último mes para calcular variación porcentual.")
            else:
                st.warning("⚠️ Datos históricos insuficientes (menos de 6 meses) para entrenar el modelo.")
else:
    st.warning("⚠️ No hay datos. Revisa la conexión a la base de datos.")