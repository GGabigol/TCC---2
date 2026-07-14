import os
import requests
import json
from datetime import datetime

# Chaves obtidas do cofre de Secrets do GitHub
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")
TS_CHANNEL_ID = os.environ.get("THINGSPEAK_CHANNEL_ID")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_previsao_5_dias():
    # API de previsão para 5 dias (dados detalhados de 3 em 3 horas)
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            lista_previsoes = dados.get('list', [])
            updates = []
            
            for item in lista_previsoes:
                # Extrai o carimbo de data/hora futura
                timestamp = item.get('dt')
                # Converte o tempo Unix para o formato padrão do ThingSpeak (ISO 8601)
                data_hora_iso = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                umidade = item['main']['humidity']
                chuva = item.get('rain', {}).get('3h', 0.0)  # Chuva acumulada em 3 horas
                
                # Estimativa de radiação solar calculada com base em nuvens e horário
                nuvens = item.get('clouds', {}).get('all', 0)
                hora_ponto = datetime.utcfromtimestamp(timestamp).hour
                
                if 6 <= hora_ponto <= 18:
                    fator_solar = max(0, 1 - abs(12 - hora_ponto) / 6) 
                    radiacao_maxima = 1000 * fator_solar
                    radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
                else:
                    radiacao = 0.0
                
                # Monta a estrutura correta exigida pela API de lote do ThingSpeak
                updates.append({
                    "created_at": data_hora_iso,
                    "field1": umidade,
                    "field2": chuva,
                    "field3": round(radiacao, 1)
                })
                
            print(f"Previsão de {len(updates)} pontos obtida com sucesso!")
            return updates
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return []
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return []

def enviar_lote_thingspeak(updates):
    if not updates:
        print("Sem novos dados para atualizar.")
        return
        
    url = f"https://api.thingspeak.com/channels/{TS_CHANNEL_ID}/bulk_update.json"
    
    payload = {
        "write_api_key": TS_WRITE_KEY,
        "updates": updates
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        resposta = requests.post(url, data=json.dumps(payload), headers=headers)
        if resposta.status_code == 202 or resposta.status_code == 201:
            print("Sucesso! Previsão para os próximos 5 dias carregada no ThingSpeak.")
        else:
            print(f"Erro no envio em lote: {resposta.status_code} - {resposta.text}")
    except Exception as e:
        print(f"Falha de conexão com o ThingSpeak ao enviar lote: {e}")

if __name__ == "__main__":
    previsoes = obter_previsao_5_dias()
    if previsoes:
        enviar_lote_thingspeak(previsoes)
