import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import ta
import telegram
import asyncio
from time import sleep
import threading


class ForexAlerts:
    def __init__(self, token, chat_id, symbol, interval='1h'):
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
        self.symbol = symbol
        self.interval = interval

        self.interval_mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1h',
            '1d': '1d'
        }

    def get_data(self):
        periods = {
            '1m': '1d',
            '5m': '5d',
            '15m': '5d',
            '30m': '10d',
            '1h': '1mo',  # Cambiado de '30d' a '1mo'
            '1d': '100d'
        }

        ticker = yf.Ticker(self.symbol)
        df = ticker.history(
            period=periods[self.interval],
            interval=self.interval_mapping[self.interval]
        )
        return df

    def analyze_data(self, df):
        """Analiza los datos y genera señales usando RSI de 5 períodos"""
        df['EMA35'] = ta.trend.ema_indicator(df['Close'], window=35)
        df['EMA50'] = ta.trend.ema_indicator(df['Close'], window=50)
        # Cambiado el RSI a 5 períodos
        df['RSI'] = ta.momentum.rsi(df['Close'], window=5)

        df['sobrecompra'] = (
                (df['RSI'] > 70) &
                (df['Close'] < df['EMA50']) &
                (df['EMA50'] > df['EMA35'])
        )

        df['sobreventa'] = (
                (df['RSI'] < 30) &
                (df['Close'] > df['EMA50']) &
                (df['EMA50'] < df['EMA35'])
        )

        return df

    async def send_alert(self, message):
        await self.bot.send_message(chat_id=self.chat_id, text=message)

    def check_signals(self, df):
        last_row = df.iloc[-1]

        if last_row['sobrecompra']:
            message = f"""🔴 ALERTA SOBRECOMPRA {self.symbol}
Temporalidad: {self.interval}
Precio: {last_row['Close']:.4f}
RSI(5): {last_row['RSI']:.2f}
Precio < EMA50
EMA50 > EMA35
Fecha: {df.index[-1]}"""

            asyncio.run(self.send_alert(message))

        elif last_row['sobreventa']:
            message = f"""🟢 ALERTA SOBREVENTA {self.symbol}
Temporalidad: {self.interval}
Precio: {last_row['Close']:.4f}
RSI(5): {last_row['RSI']:.2f}
Precio > EMA50
EMA50 < EMA35
Fecha: {df.index[-1]}"""

            asyncio.run(self.send_alert(message))

    def run(self, check_interval=60):
        print(f"Iniciando monitoreo de {self.symbol} en {self.interval}")

        # Notificación de inicio
        asyncio.run(self.send_alert(f"🚀 El bot ha iniciado el monitoreo para {self.symbol} en {self.interval}."))

        try:
            while True:
                try:
                    df = self.get_data()
                    df = self.analyze_data(df)
                    self.check_signals(df)
                    sleep(check_interval)
                except Exception as e:
                    print(f"Error en {self.symbol}: {e}")
                    sleep(check_interval)
        except KeyboardInterrupt:
            # Notificación al detener manualmente
            asyncio.run(self.send_alert(f"🛑 El monitoreo para {self.symbol} en {self.interval} se ha detenido."))
        except Exception as e:
            # Notificación al detenerse por error inesperado
            asyncio.run(self.send_alert(f"⚠️ El bot para {self.symbol} se ha detenido debido a un error: {e}"))
        finally:
            print(f"Monitoreo de {self.symbol} finalizado.")


def run_symbol(token, chat_id, symbol, interval):
    alerts = ForexAlerts(token, chat_id, symbol, interval)
    alerts.run()


if __name__ == "__main__":
    # Configura estos valores con tus datos
    TOKEN = "7719986289:AAHoqk51VONwvc6ZGcI1J_tjsqj33QNDSfc"  # Tu token del bot
    CHAT_ID = "1737672124"  # Tu chat ID

    # Lista de símbolos Forex
    symbols = {
        "EUR/USD": "EURUSD=X",
        "EUR/NZD": "EURNZD=X",
        "EUR/JPY": "EURJPY=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "USDJPY=X",
        "GBP/JPY": "GBPJPY=X",
        "XAU/USD": "GC=F"
    }

    # Crear hilos para cada símbolo
    threads = []
    for pair_name, symbol in symbols.items():
        thread = threading.Thread(
            target=run_symbol,
            args=(TOKEN, CHAT_ID, symbol, "1h"),  # Puedes cambiar la temporalidad aquí
            name=f"Thread-{pair_name}"
        )
        threads.append(thread)

    # Iniciar todos los hilos
    for thread in threads:
        thread.start()
        print(f"Iniciado monitoreo de {thread.name}")
        sleep(2)  # Pequeña pausa entre inicios

    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()
