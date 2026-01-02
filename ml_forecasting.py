import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

def predecir_produccion(df_historico, meses_futuro=12):
    """
    Toma un DataFrame con fechas y producción, y devuelve
    un DataFrame con la predicción a futuro usando Regresión Polinómica.
    """
    try:
        # Preparamos los datos
        df = df_historico.copy()
        df['fecha_ordinal'] = df['fecha'].map(pd.Timestamp.toordinal)
        
        X = df[['fecha_ordinal']]
        y = df['prod_pet']
        
        # --- MODELO DE MACHINE LEARNING ---
        # Usamos Polinomio de Grado 2 o 3 para capturar curvas (no solo líneas rectas)
        poly = PolynomialFeatures(degree=2) 
        X_poly = poly.fit_transform(X)
        
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # --- GENERAR FUTURO ---
        ultima_fecha = df['fecha'].max()
        fechas_futuras = [ultima_fecha + pd.DateOffset(months=i) for i in range(1, meses_futuro + 1)]
        
        df_futuro = pd.DataFrame({'fecha': fechas_futuras})
        df_futuro['fecha_ordinal'] = df_futuro['fecha'].map(pd.Timestamp.toordinal)
        
        # Predecir
        X_futuro_poly = poly.transform(df_futuro[['fecha_ordinal']])
        y_pred = model.predict(X_futuro_poly)
        
        # Limpiar resultados (no puede haber producción negativa)
        df_futuro['prod_pet_pred'] = np.maximum(y_pred, 0)
        df_futuro['tipo'] = 'Predicción IA'
        
        # Formatear para unir con el original
        df_futuro = df_futuro[['fecha', 'prod_pet_pred', 'tipo']]
        
        return df_futuro

    except Exception as e:
        print(f"Error en predicción: {e}")
        return pd.DataFrame()