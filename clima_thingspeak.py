import os
import requests
import time
from datetime import datetime

# Chave do cofre do GitHub
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_previsao_proximas_24h():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            lista_previsoes = dados.get('list', [])
            pontos = []
            
            # Pega exatamente os próximos 8 pontos (8 x 3h = 24 horas para frente)
            proximos_pontos = lista_previsoes[:8]
            
            for item in proximos_pontos:
                timestamp = item.get('dt')
                data_hora_iso = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                umidade = item['main']['humidity']
                chuva = item.get('rain', {}).get('3h', 0.0)
                
                # Estimativa de radiação solar
                nuvens = item.get('clouds', {}).get('all', 0)
                hora_ponto = datetime.utcfromtimestamp(timestamp).hour
                
                if 6 <= hora_ponto <= 18:
                    fator_solar = max(0, 1 - abs(12 - hora_ponto) / 6) 
                    radiacao_maxima = 1000 * fator_solar
                    radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
                else:
                    radiacao = 0.0
                
                pontos.append({
                    "created_at": data_hora_iso,
                    "umidade": umidade,
                    "chuva": chuva,
                    "radiacao": round(radiacao, 1)
                })
            
            print(f"Sucesso! {len(pontos)} pontos coletados da previsão.")
            return pontos
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return []
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return []

def enviar_pontos_sequencial(pontos):
    if not pontos:
        print("Nenhum dado para enviar.")
        return
        
    print(f"Iniciando o envio de {len(pontos)} pontos com intervalos de 16 segundos...")
    
    for i, ponto in enumerate(pontos):
        created_at = ponto["created_at"]
        umid = ponto["umidade"]
        chuv = ponto["chuva"]
        rad = ponto["radiacao"]
        
        # Mapeamento exato com base nas suas caixas de seleção:
        # field1 = Radiação | field2 = Umidade | field3 = Chuva
        url = f"https://api.thingspeak.com/update?api_key={TS_WRITE_KEY}&created_at={created_at}&field1={rad}&field2={umid}&field3={chuv}"
        
        try:
            resposta = requests.get(url)
            if resposta.status_code == 200 and resposta.text != "0":
                print(f"[{i+1}/{len(pontos)}] Sucesso! Ponto de {created_at} enviado.")
            else:
                print(f"[{i+1}/{len(pontos)}] Falha ao enviar ponto de {created_at}. Resposta: {resposta.text}")
        except Exception as e:
            print(f"Erro de conexão no ponto de {created_at}: {e}")
            
        # Espera 16 segundos exigidos pela API gratuita antes de enviar o próximo
        if i < len(pontos) - 1:
            time.sleep(16)

if __name__ == "__main__":
    previsao = obter_previsao_proximas_24h()
    if previsao:
        enviar_pontos_sequencial(previsao)
