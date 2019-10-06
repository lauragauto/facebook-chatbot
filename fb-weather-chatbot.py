import os
import sys, json, requests
from flask import Flask, request
import pyowm

try:
    import apiai
except ImportError:
    sys.path.append(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
    )
    import apiai

app = Flask(__name__)

PAT = '' # Token de Acceso a la Pagina Facebook

CLIENT_ACCESS_TOKEN = '' # Token de acceso al cliente del agente de Weather-chatbot

VERIFY_TOKEN = 'your_webhook_verification_token' #Token de verificacion de conexion entre el pat y el servidor flask

ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN) #Conexion con el agente de Weather-Chatbot


@app.route('/', methods=['GET'])
def handle_verification():
    '''
   Verifica la suscripción de facebook webhook
    Es verdadero cuando VERIFY_TOKEN es igual al token enviado por la aplicación de Facebook
    '''
    if (request.args.get('hub.verify_token', '') == VERIFY_TOKEN):
        print("succefully verified")
        return request.args.get('hub.challenge', '')
    else:
        print("Wrong verification token!")
        return "Wrong validation token"


@app.route('/', methods=['POST'])
def handle_message():
    '''
    Manejador de mensajes enviados por Facebook Messenger a la aplicación
    '''
    data = request.get_json()

    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = messaging_event["message"]["text"]
                    send_message_response(sender_id, parse_user_message(message_text))

    return "ok"


def send_message(sender_id, message_text):
    '''
    Enviar la respuesta al usuario utilizando facebook graph API
    '''
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",

                      params={"access_token": PAT},

                      headers={"Content-Type": "application/json"},

                      data=json.dumps({
                          "recipient": {"id": sender_id},
                          "message": {"text": message_text}
                      }))


def parse_user_message(user_text):
    '''
    Envia el mensaje a API AI que invoca una intención
    y retorna la respuesta en consecuencia
    A la respuesta del bot se agrega con los datos del clima obtenidos desde la consulta via API a OpenWeatherMap
    '''

    request = ai.text_request()
    request.query = user_text

    response = json.loads(request.getresponse().read().decode('utf-8'))
    responseStatus = response['status']['code']
    if (responseStatus == 200):

        print("API AI response", response['result']['fulfillment']['speech'])
        try:
            # Using open weather map client to fetch the weather report
            weather_report = ''

            input_city = response['result']['parameters']['geo-city']
            print("City ", input_city)

            owm = pyowm.OWM('')  # Api Key de OpenWeather


            observation = owm.weather_at_place(input_city)
            w = observation.get_weather()
            print(w)
            print(w.get_wind())
            print(w.get_humidity())
            max_temp = str(w.get_temperature('celsius')['temp_max'])
            min_temp = str(w.get_temperature('celsius')['temp_min'])
            current_temp = str(w.get_temperature('celsius')['temp'])
            wind_speed = str(w.get_wind()['speed'])
            humidity = str(w.get_humidity())

            weather_report = ' Temperatura Máx: ' + max_temp + ' Temperatura Min: ' + min_temp + ' Temperatura Actual: '\
                             + current_temp + ' Velocidad del Viento :' + wind_speed + ' Humedad ' + humidity + '%'
            print("Weather report ", weather_report)

            return (response['result']['fulfillment']['speech'] + weather_report)
        except:
            return (response['result']['fulfillment']['speech'])

    else:
        return ("Disculpa, No entiendo la consulta")


def send_message_response(sender_id, message_text):
    sentenceDelimiter = ". "
    messages = message_text.split(sentenceDelimiter)

    for message in messages:
        send_message(sender_id, message)


if __name__ == '__main__':
    app.run()
