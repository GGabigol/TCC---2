import os
import requests
import json
from datetime import datetime

# Chaves do cofre do GitHub
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")
TS_CHANNEL_ID = os.environ.get("THINGSPEAK_CHANNEL_ID")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_previsao_proximas_24h():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = response_json = resposta.json()
        
        if resposta.status_code == 200:
            lista_previsoes = dados.get('list', [])
            updates = []
            
            # Pega exatamente os próximos 8 pontos de previsão (8 pontos x 3 horas = 24 horas para frente!)
            proximos_pontos = lista_previsoes[:8]
            
            for item in proximos_pontos:
                timestamp = item.get('dt')
                # Converte para formato ISO esperado pelo ThingSpeak
                data_hora_iso = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                umidade = item['main']['humidity']
                chuva = item.get('rain', {}).get('3h', 0.0)
                
                # Estimativa simplificada de radiação solar
                nuvens = item.get('clouds', {}).get('all', 0)
                hora_ponto = datetime.utcfromtimestamp(timestamp).hour
                
                if 6 <= hora_ponto <= 18:
                    fator_solar = max(0, 1 - abs(12 - hora_ponto) / 6) 
                    radiacao_maxima = 1000 * fator_solar
                    radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
                else:
                    radiacao = 0.0
                
                updates.append({
                    "created_at": data_hora_iso,
                    "field1": umidade,
                    "field2": chuva,
                    "field3": round(radiacao, 1)
                })
            
            print(f"Previsão de {len(updates)} pontos (próximas 24h) coletada com sucesso!")
            return updates
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return []
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return []

def enviar_lote_thingspeak(updates):
    if not updates:
        print("Nenhum dado para enviar.")
        return
        
    url = f"https://api.thingspeak.com/channels/{TS_CHANNEL_ID}/bulk_update.json"
    
    payload = {
        "write_api_key": TS_WRITE_KEY,
        "updates": updates
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        resposta = requests.post(url, data=json.dumps(payload), headers=headers)
        if resposta.status_code in [201, 202]:
            print("Sucesso! Próximas 24h enviadas para o ThingSpeak.")
        else:
            print(f"Erro no envio: {resposta.status_code} - {resposta.text}")
    except Exception as e:
        print(f"Falha de conexão com o ThingSpeak ao enviar lote: {e}")

if __name__ == "__main__":
    pontos = obter_previsao_proximas_24h()
    if pontos:
        enviar_lote_thingspeak(pontos)
