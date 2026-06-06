import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

# ===================== CONFIGURACIÓN DE LA PÁGINA =====================
# set_page_config TIENE que ser la primera orden de Streamlit del archivo.
st.set_page_config(page_title="Analizador de Acciones", page_icon="📊", layout="wide")

rf = 0.03  # tasa libre de riesgo (3%), igual que en tu analizador

# ===================== TÍTULO Y EXPLICACIÓN =====================
st.title("📊 Analizador de Acciones")
st.write(
    "Introduce el ticker de una acción para ver sus métricas de riesgo y "
    "rentabilidad del último año. Los valores españoles llevan el sufijo `.MC` "
    "(por ejemplo `SAN.MC`)."
)

# ===================== ENTRADA DEL USUARIO =====================
ticker = st.text_input("Ticker:", value="AAPL").strip().upper()

# ===================== DESCARGA Y CÁLCULOS =====================
if ticker:
    with st.spinner(f"Descargando datos de {ticker}..."):
        datos = yf.download([ticker, "SPY"], period="1y", auto_adjust=True)["Close"].dropna()

    # Si Yahoo no devuelve datos válidos para ese ticker, avisamos.
    if datos.empty or ticker not in datos.columns:
        st.error(
            f"No he encontrado datos para «{ticker}». "
            "Revisa el símbolo (recuerda el `.MC` para valores españoles)."
        )
    else:
        precio = datos[ticker]
        retornos = datos.pct_change().dropna()

        # Rentabilidad, volatilidad y Sharpe (anualizados)
        rent_anual = retornos[ticker].mean() * 252
        vol_anual = retornos[ticker].std() * np.sqrt(252)
        sharpe = (rent_anual - rf) / vol_anual

        # Beta frente al S&P 500 (CAPM)
        beta = retornos[ticker].cov(retornos["SPY"]) / retornos["SPY"].var()

        # Máximo drawdown (peor caída desde un máximo)
        curva = (1 + retornos[ticker]).cumprod()
        max_dd = (curva / curva.cummax() - 1).min()

        # VaR 95% diario (histórico)
        var95 = retornos[ticker].quantile(0.05)

        # ===================== MÉTRICAS EN TARJETAS =====================
        st.subheader(f"Métricas de {ticker} (último año)")

        c1, c2, c3 = st.columns(3)
        c1.metric("Rentabilidad anual", f"{rent_anual*100:.1f} %")
        c2.metric("Volatilidad anual", f"{vol_anual*100:.1f} %")
        c3.metric("Ratio de Sharpe", f"{sharpe:.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Beta (vs S&P 500)", f"{beta:.2f}")
        c5.metric("Máximo drawdown", f"{max_dd*100:.1f} %")
        c6.metric("VaR 95% diario", f"{var95*100:.2f} %")

        # ===================== GRÁFICOS =====================
        st.subheader(f"Evolución del precio de {ticker}")
        st.line_chart(precio)

        st.subheader(f"{ticker} frente al S&P 500 (base 100)")
        normalizado = datos / datos.iloc[0] * 100
        st.line_chart(normalizado)

        # ===================== AVISO =====================
        st.caption(
            "Datos de Yahoo Finance (gratuitos, no institucionales). "
            "Herramienta de aprendizaje, no constituye asesoramiento financiero."
        )
