import yfinance as yf
import numpy as np
import matplotlib
matplotlib.use("Agg")          # no abre ventanas, solo guarda imágenes
import matplotlib.pyplot as plt
import pandas as pd
from openpyxl.chart import LineChart, Reference
import os

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

# ===================== CARGA DE DATOS (desde el CSV) =====================
if not os.path.exists("cartera.csv"):
    pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "ITX.MC", "SAN.MC", "MRL.MC"],
        "cantidad": [10, 5, 20, 150, 80],
        "precio_compra": [180, 400, 45, 4.5, 11],
    }).to_csv("cartera.csv", index=False)
    print("📄 Creado cartera.csv de ejemplo. Ábrelo y pon tus datos reales.")

cartera = pd.read_csv("cartera.csv")
tickers = cartera["ticker"].tolist()
if "SPY" not in tickers:
    tickers = tickers + ["SPY"]

datos = yf.download(tickers, period="1y", auto_adjust=True)
precios = datos["Close"]
precios = precios.dropna(axis=1, how="all")
precios = precios.dropna()
tickers = precios.columns.tolist()

# ===================== FASE 2: rentabilidad y riesgo =====================
retornos = precios.pct_change().dropna()
rent_anual = retornos.mean() * 252
volatilidad_anual = retornos.std() * np.sqrt(252)
cv = volatilidad_anual / rent_anual

print("===== RESUMEN DE LA CARTERA (último año) =====\n")
print("Rentabilidad anualizada:")
print((rent_anual * 100).round(2).astype(str) + " %")
print("\nVolatilidad anualizada (riesgo):")
print((volatilidad_anual * 100).round(2).astype(str) + " %")
print("\nCoeficiente de variación (riesgo / rentabilidad):")
print(cv.round(2))

# ===================== FASE 3: gráfico base 100 (se guarda como PNG) =====================
normalizados = precios / precios.iloc[0] * 100
plt.figure(figsize=(10, 6))
for ticker in tickers:
    plt.plot(normalizados.index, normalizados[ticker], label=ticker)
plt.title("Evolución de la cartera (base 100 = hace 1 año)")
plt.xlabel("Fecha")
plt.ylabel("Valor (base 100)")
plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("grafico_precios.png", bbox_inches="tight")

# ===================== CAPM vs S&P 500 =====================
mercado = "SPY"
rf = 0.03
var_mercado = retornos[mercado].var()

print("\n\n===== ANÁLISIS CAPM vs S&P 500 =====\n")
betas = {}
alphas = {}
for ticker in tickers:
    cov = retornos[ticker].cov(retornos[mercado])
    beta = cov / var_mercado
    rent_esperada = rf + beta * (rent_anual[mercado] - rf)
    alpha = rent_anual[ticker] - rent_esperada
    betas[ticker] = beta
    alphas[ticker] = alpha
    print(f"{ticker}:")
    print(f"   Beta  = {beta:.2f}")
    print(f"   Alpha = {alpha*100:.2f} %\n")

# ===================== A) Tabla-resumen =====================
resumen = pd.DataFrame({
    "Rentabilidad anual (%)": (rent_anual * 100).round(2),
    "Volatilidad anual (%)": (volatilidad_anual * 100).round(2),
    "Coef. variación": cv.round(2),
    "Beta": pd.Series(betas).round(2),
    "Alpha (%)": (pd.Series(alphas) * 100).round(2),
    "Sharpe": ((rent_anual - rf) / volatilidad_anual).round(2),
})
resumen = resumen.reindex(tickers)

# ===================== CARTERA REAL: pesos, P&L y Sharpe (Tema 1) =====================
cartera = cartera.set_index("ticker")
cartera = cartera[cartera.index.isin(precios.columns)]
precio_actual = precios.iloc[-1]
cartera["precio_actual"] = precio_actual
cartera["valor_compra"] = cartera["cantidad"] * cartera["precio_compra"]
cartera["valor_actual"] = cartera["cantidad"] * cartera["precio_actual"]
cartera["ganancia_%"] = (cartera["precio_actual"] / cartera["precio_compra"] - 1) * 100
valor_total = cartera["valor_actual"].sum()
cartera["peso_%"] = cartera["valor_actual"] / valor_total * 100

pesos = cartera["peso_%"] / 100
rent_cartera = (pesos * rent_anual[pesos.index]).sum()
cov_anual = retornos[pesos.index].cov() * 252
vol_cartera = np.sqrt(pesos.values @ cov_anual.values @ pesos.values)
sharpe_cartera = (rent_cartera - rf) / vol_cartera

cartera_resumen = pd.DataFrame({
    "Métrica": ["Valor total", "Rentabilidad anual (%)", "Volatilidad anual (%)", "Ratio de Sharpe"],
    "Valor": [round(valor_total, 2), round(rent_cartera*100, 2), round(vol_cartera*100, 2), round(sharpe_cartera, 2)],
})

print("\n===== CARTERA REAL =====")
print(cartera[["cantidad", "precio_compra", "precio_actual", "valor_actual", "peso_%", "ganancia_%"]].round(2))
print(f"\nValor total: {valor_total:,.2f}")
print(f"Rentabilidad anual de la cartera: {rent_cartera*100:.2f} %")
print(f"Volatilidad anual de la cartera:  {vol_cartera*100:.2f} %")
print(f"Ratio de Sharpe de la cartera:    {sharpe_cartera:.2f}")

# ===================== VALORACIÓN POR MÚLTIPLOS vs SECTOR (Tema 5) =====================
# Múltiplos por sector: Damodaran (NYU Stern), enero 2026, mercado USA. Bancos: PER + P/B.
sector_damodaran = {
    "AAPL":   {"sector": "Computers/Peripherals",          "PER_sector": 34.33, "EVEBITDA_sector": 25.42, "PB_sector": 34.08},
    "MSFT":   {"sector": "Software (System & Application)", "PER_sector": 37.52, "EVEBITDA_sector": 24.48, "PB_sector": 9.14},
    "ITX.MC": {"sector": "Apparel",                         "PER_sector": 27.09, "EVEBITDA_sector": 10.30, "PB_sector": 3.89},
    "SAN.MC": {"sector": "Bank (Money Center)",             "PER_sector": 14.17, "EVEBITDA_sector": None,  "PB_sector": 1.62},
    "MRL.MC": {"sector": "R.E.I.T.",                        "PER_sector": 28.10, "EVEBITDA_sector": 19.87, "PB_sector": 1.99},
}

print("\nDescargando fundamentales (PER, EV/EBITDA, P/B)... puede tardar unos segundos.")
filas = []
for t in cartera.index:
    info = yf.Ticker(t).info
    filas.append({
        "ticker": t,
        "PER": info.get("trailingPE"),
        "EV/EBITDA": info.get("enterpriseToEbitda"),
        "P/B": info.get("priceToBook"),
    })
valoracion = pd.DataFrame(filas).set_index("ticker")

sector_df = pd.DataFrame(sector_damodaran).T
for c in ["PER_sector", "EVEBITDA_sector", "PB_sector"]:
    sector_df[c] = pd.to_numeric(sector_df[c], errors="coerce")
valoracion = valoracion.join(sector_df)

def comparar(propio, ref):
    if pd.isna(propio) or pd.isna(ref):
        return "n/d"
    return "caro" if propio > ref else "barato"

valoracion["PER vs sector"] = [comparar(p, r) for p, r in zip(valoracion["PER"], valoracion["PER_sector"])]
valoracion["P/B vs sector"] = [comparar(p, r) for p, r in zip(valoracion["P/B"], valoracion["PB_sector"])]
valoracion["EV/EBITDA vs sector"] = [comparar(p, r) for p, r in zip(valoracion["EV/EBITDA"], valoracion["EVEBITDA_sector"])]

for col in ["PER", "P/B", "EV/EBITDA", "PER_sector", "PB_sector", "EVEBITDA_sector"]:
    valoracion[col] = pd.to_numeric(valoracion[col], errors="coerce").round(2)

valoracion = valoracion[[
    "sector",
    "PER", "PER_sector", "PER vs sector",
    "P/B", "PB_sector", "P/B vs sector",
    "EV/EBITDA", "EVEBITDA_sector", "EV/EBITDA vs sector",
]]

print("\n===== VALORACIÓN vs SECTOR (Damodaran, ene-2026) =====")
print(valoracion)

# ===================== B) Precios en formato largo (tablas dinámicas) =====================
precios_largo = precios.reset_index()
col_fecha = precios_largo.columns[0]
precios_largo = precios_largo.melt(id_vars=col_fecha, var_name="Ticker", value_name="Precio")

# ===================== C) Indicadores técnicos de UN activo (Tema 3) =====================
print("\nActivos disponibles:", ", ".join(tickers))
eleccion = input("¿Qué activo quieres analizar a fondo? (Enter = AAPL): ").strip().upper()
activo_mm = eleccion if eleccion in tickers else "AAPL"
print(f"➡ Analizando: {activo_mm}")
precio = precios[activo_mm]

mm = pd.DataFrame({
    "Precio": precio,
    "SMA20": precio.rolling(20).mean(),
    "SMA50": precio.rolling(50).mean(),
})

ema12 = precio.ewm(span=12, adjust=False).mean()
ema26 = precio.ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
senal = macd.ewm(span=9, adjust=False).mean()
macd_df = pd.DataFrame({"MACD": macd, "Senal(9)": senal, "Histograma": macd - senal})

delta = precio.diff()
ganancia = delta.clip(lower=0)
perdida = -delta.clip(upper=0)
media_g = ganancia.ewm(alpha=1/14, adjust=False).mean()
media_p = perdida.ewm(alpha=1/14, adjust=False).mean()
rs = media_g / media_p
rsi = 100 - 100 / (1 + rs)

rsi_sobrecompra = 70
rsi_sobreventa = 30
aviso = np.where(rsi > rsi_sobrecompra, "SOBRECOMPRA",
        np.where(rsi < rsi_sobreventa, "SOBREVENTA", ""))

rsi_df = pd.DataFrame({"RSI(14)": rsi})
rsi_df["Sobrecompra"] = rsi_sobrecompra
rsi_df["Sobreventa"] = rsi_sobreventa
rsi_df["Aviso"] = aviso

# ===================== D) Función reutilizable para gráficos de líneas =====================
def grafico_lineas(hoja, n_filas, n_columnas, titulo, eje_y):
    g = LineChart()
    g.title = titulo
    g.x_axis.title = "Fecha"
    g.y_axis.title = eje_y
    g.height = 9
    g.width = 20
    datos = Reference(hoja, min_col=2, max_col=1 + n_columnas, min_row=1, max_row=n_filas + 1)
    fechas = Reference(hoja, min_col=1, min_row=2, max_row=n_filas + 1)
    g.add_data(datos, titles_from_data=True)
    g.set_categories(fechas)
    hoja.add_chart(g, "G2")

# ===================== D2) BACKTESTING =====================
ret_diario = precio.pct_change().fillna(0)
pos_sma = (mm["SMA20"] > mm["SMA50"]).astype(int).shift(1).fillna(0)
pos_combi = ((mm["SMA20"] > mm["SMA50"]) & (rsi < rsi_sobrecompra)).astype(int).shift(1).fillna(0)

backtest = pd.DataFrame({
    "Comprar y mantener": (1 + ret_diario).cumprod() * 100,
    "Estrategia medias": (1 + ret_diario * pos_sma).cumprod() * 100,
    "Estrategia medias+RSI": (1 + ret_diario * pos_combi).cumprod() * 100,
})

resultado_bt = pd.DataFrame({
    "Rentabilidad total (%)": ((backtest.iloc[-1] / 100 - 1) * 100).round(2),
    "% tiempo invertido": [100.0, round(pos_sma.mean()*100, 1), round(pos_combi.mean()*100, 1)],
})

print(f"\n===== BACKTEST sobre {activo_mm} =====")
print(resultado_bt)
# ===================== F) DCF SIMPLIFICADO (valor intrínseco, Tema 5) =====================
# OJO: el DCF por flujos NO sirve para bancos ni SOCIMIs. Úsalo con AAPL, MSFT, ITX.MC...
tk = yf.Ticker(activo_mm)
info_dcf = tk.info

# --- Supuestos (cámbialos a tu criterio) ---
g_proyeccion  = 0.08
g_perpetuo    = 0.025
prima_mercado = 0.05
tasa_impuesto = 0.25
anios = 5

# --- FCF: probamos el dato directo y, si falta, lo calculamos del estado de flujos ---
fcf0 = info_dcf.get("freeCashflow")
if not fcf0:
    try:
        cf = tk.cashflow
        if "Free Cash Flow" in cf.index:
            fcf0 = float(cf.loc["Free Cash Flow"].iloc[0])
        else:
            op = capex = None
            for n in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if n in cf.index:
                    op = float(cf.loc[n].iloc[0]); break
            for n in ["Capital Expenditure", "Capital Expenditures"]:
                if n in cf.index:
                    capex = float(cf.loc[n].iloc[0]); break
            if op is not None and capex is not None:
                fcf0 = op + capex          # capex viene negativo, así que sumarlo lo resta
    except Exception:
        fcf0 = None

market_cap = info_dcf.get("marketCap")
acciones   = info_dcf.get("sharesOutstanding") or info_dcf.get("impliedSharesOutstanding")
if not market_cap and acciones:
    market_cap = acciones * float(precios[activo_mm].iloc[-1])
deuda    = info_dcf.get("totalDebt") or 0
caja     = info_dcf.get("totalCash") or 0
beta_dcf = betas.get(activo_mm, 1)

print(f"\n===== DCF SIMPLIFICADO de {activo_mm} =====")

if not fcf0 or fcf0 <= 0 or not acciones or not market_cap:
    print("No hay datos válidos (FCF, acciones o capitalización) para el DCF de este activo.")
    print("Pasa con bancos/SOCIMIs o cuando Yahoo no trae el dato. Prueba con AAPL o MSFT.")
    dcf_resumen = pd.DataFrame({"Métrica": ["DCF no disponible para"], "Valor": [activo_mm]})
else:
    ke = rf + beta_dcf * prima_mercado
    kd = rf + 0.02
    peso_e = market_cap / (market_cap + deuda)
    peso_d = deuda / (market_cap + deuda)
    wacc = peso_e * ke + peso_d * kd * (1 - tasa_impuesto)
    if wacc <= g_perpetuo:
        wacc = g_perpetuo + 0.03

    valor_actual_fcf = 0
    fcf = fcf0
    for t in range(1, anios + 1):
        fcf = fcf * (1 + g_proyeccion)
        valor_actual_fcf += fcf / (1 + wacc) ** t

    valor_terminal = fcf * (1 + g_perpetuo) / (wacc - g_perpetuo)
    valor_terminal_hoy = valor_terminal / (1 + wacc) ** anios

    enterprise_value = valor_actual_fcf + valor_terminal_hoy
    deuda_neta = deuda - caja
    equity_value = enterprise_value - deuda_neta
    valor_accion = equity_value / acciones

    precio_hoy = float(precios[activo_mm].iloc[-1])
    margen = (valor_accion / precio_hoy - 1) * 100

    print(f"Ke (CAPM)            = {ke*100:.2f} %")
    print(f"WACC                 = {wacc*100:.2f} %")
    print(f"Valor por acción DCF = {valor_accion:,.2f}")
    print(f"Precio actual        = {precio_hoy:,.2f}")
    print(f"Margen vs precio     = {margen:+.1f} %  ({'infravalorada' if margen > 0 else 'sobrevalorada'})")

    dcf_resumen = pd.DataFrame({
        "Métrica": ["Ke (CAPM) %", "WACC %", "Valor por acción (DCF)", "Precio actual", "Margen vs precio %"],
        "Valor": [round(ke*100, 2), round(wacc*100, 2), round(valor_accion, 2), round(precio_hoy, 2), round(margen, 1)],
    })

 # ===================== G) MÉTRICAS DE RIESGO: drawdown y VaR (Tema 1) =====================
# Drawdown = mayor caída desde un máximo previo. VaR = pérdida máxima esperable en un día.
# Reconstruimos la curva de la cartera con tus PESOS ACTUALES y medimos su riesgo.
ret_cartera_diaria = (retornos[pesos.index] * pesos).sum(axis=1)

# --- Máximo drawdown de la CARTERA ---
curva_cartera = (1 + ret_cartera_diaria).cumprod() * 100   # valor de la cartera, base 100
pico = curva_cartera.cummax()                              # máximo alcanzado hasta cada día
drawdown = curva_cartera / pico - 1                        # cuánto estás por debajo del pico
max_dd_cartera = drawdown.min()                            # la peor caída (sale en negativo)

# --- Máximo drawdown del ACTIVO que elegiste antes (activo_mm) ---
pico_activo = precio.cummax()
dd_activo = precio / pico_activo - 1
max_dd_activo = dd_activo.min()

# --- VaR 95% diario de la cartera ---
var_hist  = ret_cartera_diaria.quantile(0.05)                            # histórico: percentil 5
var_param = ret_cartera_diaria.mean() - 1.645 * ret_cartera_diaria.std() # paramétrico (asume normal)

print("\n===== MÉTRICAS DE RIESGO (Tema 1) =====")
print(f"Máximo drawdown de la cartera : {max_dd_cartera*100:.2f} %")
print(f"Máximo drawdown de {activo_mm}      : {max_dd_activo*100:.2f} %")
print(f"VaR 95% histórico   : {var_hist*100:.2f} %  ->  {var_hist*valor_total:,.2f} € en un día malo")
print(f"VaR 95% paramétrico : {var_param*100:.2f} %  ->  {var_param*valor_total:,.2f} € en un día malo")

# --- Tablas para el Excel ---
riesgo_resumen = pd.DataFrame({
    "Métrica": ["Máximo drawdown cartera (%)", f"Máximo drawdown {activo_mm} (%)",
                "VaR 95% histórico (%)", "VaR 95% histórico (€)",
                "VaR 95% paramétrico (%)", "VaR 95% paramétrico (€)"],
    "Valor": [round(max_dd_cartera*100, 2), round(max_dd_activo*100, 2),
              round(var_hist*100, 2), round(var_hist*valor_total, 2),
              round(var_param*100, 2), round(var_param*valor_total, 2)],
})
drawdown_chart = pd.DataFrame({"Drawdown cartera (%)": drawdown * 100})

# ===================== E) Escribimos todo en el Excel =====================
with pd.ExcelWriter("analisis_cartera.xlsx", engine="openpyxl") as writer:
    precios.to_excel(writer, sheet_name="Precios")
    normalizados.to_excel(writer, sheet_name="Normalizado")
    resumen.to_excel(writer, sheet_name="Resumen")
    precios_largo.to_excel(writer, sheet_name="Datos_largo", index=False)
    mm.to_excel(writer, sheet_name="Media_movil")
    macd_df.to_excel(writer, sheet_name="MACD")
    rsi_df.to_excel(writer, sheet_name="RSI")
    backtest.to_excel(writer, sheet_name="Backtesting")
    resultado_bt.to_excel(writer, sheet_name="Backtest_resumen")
    cartera.to_excel(writer, sheet_name="Cartera")
    cartera_resumen.to_excel(writer, sheet_name="Cartera_resumen", index=False)
    valoracion.to_excel(writer, sheet_name="Valoracion")
    dcf_resumen.to_excel(writer, sheet_name="DCF", index=False)
    riesgo_resumen.to_excel(writer, sheet_name="Riesgo", index=False)
    drawdown_chart.to_excel(writer, sheet_name="Drawdown")

    grafico_lineas(writer.sheets["Normalizado"], len(normalizados), len(normalizados.columns),
                   "Evolución de la cartera (base 100)", "Base 100")
    grafico_lineas(writer.sheets["Media_movil"], len(mm), 3,
                   f"{activo_mm}: precio y medias móviles", "Precio")
    grafico_lineas(writer.sheets["MACD"], len(macd_df), 2,
                   f"{activo_mm}: MACD (12,26) y Señal (9)", "MACD")
    grafico_lineas(writer.sheets["RSI"], len(rsi_df), 3,
                   f"{activo_mm}: RSI(14) bandas {rsi_sobreventa}-{rsi_sobrecompra}", "RSI")
    grafico_lineas(writer.sheets["Backtesting"], len(backtest), 3,
                   f"{activo_mm}: estrategias vs comprar y mantener", "Valor de 100")
    grafico_lineas(writer.sheets["Drawdown"], len(drawdown_chart), 1,
                   "Drawdown de la cartera (caída desde máximos)", "Drawdown (%)")

print("\n✅ Excel actualizado: analisis_cartera.xlsx")