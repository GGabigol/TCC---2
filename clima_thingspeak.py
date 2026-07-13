import os
import requests
from datetime import datetime

# O GitHub Actions vai pegar as chaves diretamente do cofre (Secrets) que você criou!
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")

CITY_NAME = "Indaiatuba"  # Altere para o nome da sua cidade se desejar
COUNTRY_CODE = "BR"

def obter_dados_clima():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            agora = datetime.now()
            # Formata a data e hora em modo legível para o Field 1
            data_hora_string = agora.strftime("%d/%m/%Y %H:%M")
            
            umidade = dados['main']['humidity']
            chuva = dados.get('rain', {}).get('1h', 0.0)
            
            # Cálculo de radiação solar estimada com base nas nuvens e na hora do dia
            nuvens = dados.get('clouds', {}).get('all', 0)
            hora_atual = agora.hour
            if 6 <= hora_atual <= 18:
                fator_solar = max(0, 1 - abs(12 - hora_atual) / 6) 
                radiacao_maxima = 1000 * fator_solar
                radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
            else:
                radiacao = 0.0
                
            print(f"Dados meteorológicos de {CITY_NAME} obtidos com sucesso!")
            return data_hora_string, umidade, chuva, round(radiacao, 1)
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return None, None, None, None
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return None, None, None, None

def enviar_para_thingspeak(data_hora, umidade, chuva, radiacao):
    # Envia para o ThingSpeak exatamente na sua estrutura de canais
    # Field 1 = Data/hora | Field 2 = Umidade | Field 3 = Chuva | Field 4 = Radiação
    url = f"https://api.thingspeak.com/update?api_key={TS_WRITE_KEY}&field1={data_hora}&field2={umidade}&field3={chuva}&field4={radiacao}"
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200 and resposta.text != "0":
            print("Sucesso! Dados enviados para o ThingSpeak.")
        else:
            print("Erro ao enviar dados. Verifique a chave ou limites de tempo.")
    except Exception as e:
        print(f"Falha de conexão com o ThingSpeak: {e}")

if __name__ == "__main__":
    dt, umid, chuv, rad = obter_dados_clima()
    if dt is not None:
        enviar_para_thingspeak(dt, umid, chuv, rad)
