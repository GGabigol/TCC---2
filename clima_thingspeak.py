import os
import requests

# O GitHub Actions vai pegar as chaves diretamente do cofre (Secrets)
OW_API_KEY = os.environ.get("OPENWEATHER_KEY")
TS_WRITE_KEY = os.environ.get("THINGSPEAK_KEY")

CITY_NAME = "Indaiatuba"
COUNTRY_CODE = "BR"

def obter_dados_clima():
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY_NAME},{COUNTRY_CODE}&appid={OW_API_KEY}&units=metric&lang=pt_br"
    
    try:
        resposta = requests.get(url)
        dados = resposta.json()
        
        if resposta.status_code == 200:
            umidade = dados['main']['humidity']
            chuva = dados.get('rain', {}).get('1h', 0.0)
            
            # Cálculo de radiação solar estimada com base nas nuvens e hora
            nuvens = dados.get('clouds', {}).get('all', 0)
            from datetime import datetime
            hora_atual = datetime.now().hour
            
            if 6 <= hora_atual <= 18:
                fator_solar = max(0, 1 - abs(12 - hora_atual) / 6) 
                radiacao_maxima = 1000 * fator_solar
                radiacao = radiacao_maxima * (1 - 0.75 * (nuvens / 100))
            else:
                radiacao = 0.0
                
            print(f"Dados obtidos: Umidade={umidade}%, Chuva={chuva}mm, Radiação={round(radiacao, 1)} W/m²")
            return umidade, chuva, round(radiacao, 1)
        else:
            print(f"Erro na API OpenWeather: {dados.get('message')}")
            return None, None, None
    except Exception as e:
        print(f"Erro de conexão com OpenWeather: {e}")
        return None, None, None

def enviar_para_thingspeak(umidade, chuva, radiacao):
    # Field 1 = Umidade | Field 2 = Chuva | Field 3 = Radiação
    url = f"https://api.thingspeak.com/update?api_key={TS_WRITE_KEY}&field1={umidade}&field2={chuva}&field3={radiacao}"
    try:
        resposta = requests.get(url)
        if resposta.status_code == 200 and resposta.text != "0":
            print("Sucesso! Dados numéricos enviados para o ThingSpeak.")
        else:
            print("Erro ao enviar dados para o ThingSpeak.")
    except Exception as e:
        print(f"Falha de conexão com o ThingSpeak: {e}")

if __name__ == "__main__":
    umid, chuv, rad = obter_dados_clima()
    if umid is not None:
        enviar_para_thingspeak(umid, chuv, rad)
