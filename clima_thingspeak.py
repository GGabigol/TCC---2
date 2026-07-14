import os
import requests
import json
from datetime import datetime, timedelta

# Chaves do cofre do GitHub
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")
TS_CHANNEL_ID = os.environ.get("THINGSPEAK_CHANNEL_ID")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_previsao_amanha():
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            lista_previsoes = dados.get('list', [])
            updates = []
            
            # Define o intervalo do "dia de amanhã" (00:00 até 23:59 do próximo dia)
            hoje = datetime.utcnow().date()
            amanha = hoje + timedelta(days=1)
            
            for item in lista_previsoes:
                timestamp = item.get('dt')
                data_ponto = datetime.utcfromtimestamp(timestamp)
                
                # Filtra apenas se o ponto pertencer ao dia de amanhã
                if data_ponto.date() == amanha:
                    data_hora_iso = data_ponto.strftime('%Y-%m-%d %H:%M:%S')
                    
                    umidade = item['main']['humidity']
                    chuva = item.get('rain', {}).get('3h', 0.0)
                    
                    # Estimativa de radiação solar para o dia de amanhã
                    nuvens = item.get('clouds', {}).get('all', 0)
                    hora_ponto = data_ponto.hour
                    
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
            
            print(f"Previsão de {len(updates)} pontos coletada especificamente para o dia de amanhã ({amanha.strftime('%d/%m/%Y')})!")
            return updates
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return []
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return []

def enviar_lote_thingspeak(updates):
    if not updates:
        print("Nenhum ponto encontrado para o dia de amanhã.")
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
            print("Sucesso! O gráfico das próximas 24h de amanhã foi gerado no ThingSpeak.")
        else:
            print(f"Erro no envio em lote: {resposta.status_code} - {resposta.text}")
    except Exception as e:
        print(f"Falha ao enviar lote para o ThingSpeak: {e}")

if __name__ == "__main__":
    pontos_amanha = obter_previsao_amanha()
    if pontos_amanha:
        enviar_lote_thingspeak(pontos_amanha)
