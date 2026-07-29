import os
import requests
import time
from datetime import datetime, timezone

# Lê as chaves registradas no GitHub Secrets
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_clima_atual():
    # Usa a API de Clima Atual em tempo real
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            umidade = dados['main']['humidity']
            chuva = dados.get('rain', {}).get('1h', 0.0)
            
            # Estimativa de radiação solar em tempo real
            nuvens = dados.get('clouds', {}).get('all', 0)
            
            # Hora atual no UTC
            hora_ponto = datetime.now(timezone.utc).hour
            
            # Ajuste aproximado para o horário local (UTC-3)
            hora_local = (hora_ponto - 3) % 24
            
            if 6 <= hora_local <= 18:
                fator_solar = max(0, 1 - abs(12 - hora_local) / 6) 
                radiacao_maxima = 1000 * fator_solar
                radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
            else:
                radiacao = 0.0
                
            ponto = {
                "umidade": umidade,
                "chuva": chuva,
                "radiacao": round(radiacao, 1)
            }
            
            print(f"Sucesso! Dados coletados: Radiação={ponto['radiacao']}, Umidade={ponto['umidade']}, Chuva={ponto['chuva']}")
            return ponto
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return None
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return None

def enviar_thingspeak(ponto):
    if not ponto:
        print("Nenhum dado para enviar.")
        return
        
    if not TS_WRITE_KEY:
        print("ERRO CRÍTICO: Chave THINGSPEAK_KEY não encontrada nas variáveis de ambiente.")
        return

    rad = ponto["radiacao"]
    umid = ponto["umidade"]
    chuv = ponto["chuva"]
    
    # Envia o ponto diretamente no tempo presente
    url = f"https://api.thingspeak.com/update?api_key={TS_WRITE_KEY}&field1={rad}&field2={umid}&field3={chuv}"
    
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200 and resposta.text != "0":
            print("Sucesso! Dados enviados para o ThingSpeak com sucesso.")
        else:
            print(f"Falha ao enviar. Código de Resposta do ThingSpeak: {resposta.text}")
    except Exception as e:
        print(f"Erro de conexão com ThingSpeak: {e}")

if __name__ == "__main__":
    dados = obter_clima_atual()
    if dados:
        enviar_thingspeak(dados)
