from Controllers.Home import Home
from Controllers.V1Description import V1Description
from Controllers.V2Description import V2Description
from Controllers.V1Vision import V1Vision
from Controllers.V2Vision import V2Vision
import json

def health(event, context):
    return Home.showMessage(event)

def v1_description(event, context):
    return V1Description.showMessage()

def v2_description(event, context):
    return V2Description.showMessage()

def v1_vision(event, context):
    # Decodifica o corpo da solicitação JSON
    parameters = json.loads(event['body'])
    return V1Vision.detectEmotion(parameters)

def v2_vision(event, context):
    parameters = json.loads(event['body'])
    return V2Vision.petRekognizer(parameters)
