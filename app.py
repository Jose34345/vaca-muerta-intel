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

    # 3. PREDICCIÓN IA + ESCENARIOS ECONÓMICOS
    with tab_ia:
        st.subheader("🔮 Bola de Cristal: Predicción y Escenarios")
        st.markdown("Proyección de volumen basada en IA + Simulación financiera ajustando el precio del barril.")

        col_config, col_graph = st.columns([1, 3])

        with col_config:
            st.markdown("#### 1. Configuración")
            empresa_pred = st.selectbox(
                "Operadora:", 
                operadoras_sel if operadoras_sel else lista_operadoras,
                key="sb_ia" # Key único para evitar conflictos
            )
            
            st.markdown("---")
            st.markdown("#### 2. Variables de Mercado")
            # Slider para jugar con el precio futuro
            precio_futuro = st.slider(
                "Precio Barril Proyectado (US$):", 
                min_value=40, 
                max_value=120, 
                value=75, 
                step=1,
                help="Ajusta este valor para ver cómo impacta en la facturación futura."
            )
            
        if empresa_pred:
            # --- LÓGICA ML (La misma de antes) ---
            df_filtered = df_view[df_view['empresa'] == empresa_pred]
            df_empresa = df_filtered.groupby('fecha')[['prod_pet']].sum().reset_index().sort_values('fecha')
            
            if len(df_empresa) > 6:
                # Entrenar y Predecir Volumen
                df_prediccion = predecir_produccion(df_empresa)
                
                # --- NUEVA LÓGICA FINANCIERA ---
                # Calculamos la facturación proyectada usando el precio del slider
                # m3 * precio = USD Revenue
                df_prediccion['revenue_proyectado'] = df_prediccion['prod_pet_pred'] * precio_futuro
                
                # Crear DataFrame unido para graficar volumen
                df_hist = df_empresa.copy()
                df_hist['tipo'] = 'Dato Real'
                df_hist.rename(columns={'prod_pet': 'produccion'}, inplace=True)
                
                df_prediccion_graf = df_prediccion.copy()
                df_prediccion_graf.rename(columns={'prod_pet_pred': 'produccion'}, inplace=True)
                
                df_total = pd.concat([df_hist, df_prediccion_graf])

                with col_graph:
                    # GRÁFICO 1: VOLUMEN FÍSICO
                    fig_vol = px.line(
                        df_total, x='fecha', y='produccion', color='tipo',
                        title=f"1. Proyección de Extracción: {empresa_pred}",
                        color_discrete_map={"Dato Real": "blue", "Predicción IA": "orange"}
                    )
                    fig_vol.add_vline(x=pd.Timestamp.now().timestamp() * 1000, line_dash="dash", line_color="green", annotation_text="Hoy")
                    st.plotly_chart(fig_vol, use_container_width=True)

                    # GRÁFICO 2: FLUJO DE DINERO FUTURO (NUEVO)
                    st.markdown("#### 💵 Impacto en Facturación (Escenario: US$ " + str(precio_futuro) + "/bbl)")
                    
                    fig_money = px.area(
                        df_prediccion, 
                        x='fecha', 
                        y='revenue_proyectado',
                        title=f"Flujo de Caja Proyectado 2026 ({empresa_pred})",
                        color_discrete_sequence=['#00CC96'] # Color verde dinero
                    )
                    st.plotly_chart(fig_money, use_container_width=True)

                # --- KPI CARDS DE RESUMEN ---
                st.markdown("---")
                # Calculamos totales del periodo predicho (próximos 12 meses)
                total_vol_futuro = df_prediccion['prod_pet_pred'].sum()
                total_plata_futura = df_prediccion['revenue_proyectado'].sum()
                
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("Volumen Estimado (12 meses)", f"{total_vol_futuro/1000:,.1f} dam³")
                kpi2.metric("Precio Simulacion", f"US$ {precio_futuro}")
                # El dato que le importa a los inversores:
                kpi3.metric("Facturación Proyectada", f"US$ {total_plata_futura/1_000_000:,.1f} M", delta="Proyección 2026")

            else:
                st.warning("⚠️ Datos insuficientes para proyectar.")
else:
    st.warning("⚠️ No hay datos. Revisa la conexión a la base de datos.")