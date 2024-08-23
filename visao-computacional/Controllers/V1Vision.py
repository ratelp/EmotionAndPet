import json
import boto3
from datetime import datetime

class V1Vision:

    @staticmethod
    def detectEmotion(parameters):
        
        try:
            # Coleta parâmetros
            bucket = parameters['bucket']
            imageName = parameters['imageName']
            
            # Verifica se parâmetros estão vazios
            if bucket == "" or imageName == "":
                raise ValueError(f"Parâmetros inválidos!")

        except KeyError as e:
            # Algum parâmetro não foi informado
            body = {
                "message": f"Parâmetro {str(e)} não encontrado!"
            }

            response = {"statusCode": 500, "body": json.dumps(body)}

            return response
        except ValueError as e:
            # Parâmetro informado inválido
            body = {
                "message": str(e)
            }

            response = {"statusCode": 500, "body": json.dumps(body)}

            return response

        # Inicializa serviços da AWS
        s3 = boto3.client('s3')
        rekognition = boto3.client('rekognition')


        # Verifica existencia do Bucket e da imagem
        try :
            s3.head_bucket(Bucket=bucket) # Verifica existencia do bucket
            try:
                s3.head_object(Bucket=bucket, Key=imageName) # Verifica existencia da imagem
            except:
                return {"statusCode":500, "body": "Imagem inexistente"}
        except:
            return {"statusCode":500, "body": "Bucket inexistente"}


        try:
            # Enviando a imagem para o Rekognition para detecção de rótulos
            rekognitionResponse = rekognition.detect_faces(
                Image={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': imageName
                    }
                },
                Attributes=['ALL'] # Obtém todos os atributos da face
            )

            # Envia LOG para cloudwatch com a resposta do rekognition
            print(json.dumps(rekognitionResponse))

            # Obtém metadados do objeto no S3 para obter a data de criação
            object_metadata = s3.head_object(Bucket=bucket, Key=imageName)
            creation_date = object_metadata['LastModified'].strftime("%d-%m-%Y %H:%M:%S")

            # Inicializa lista que será colocada as informações da face caso houver
            faces_info = []

            # Verifica se foram detectadas faces na imagem
            if rekognitionResponse['FaceDetails'] != []:
                
                # Itera sobre todas as faces detectadas
                for face_detail in rekognitionResponse['FaceDetails']:
                    face_info = {}
                    # Verifica se o Rekognition detectou expressões faciais
                    if 'Emotions' in face_detail:
                        
                        # Adiciona características da posição da face
                        position = face_detail['BoundingBox']
                        position = {key: position[key] for key in sorted(position)} # Ordena por ordem alfabética
                        face_info['position'] = position

                        max_confidence = 0
                        classified_emotion = None
                        # Itera sobre todas as emoções detectadas na face
                        for emotion in face_detail['Emotions']:
                            # Atualiza a emoção classificada se a confiança for maior
                            if emotion['Confidence'] > max_confidence:
                                max_confidence = emotion['Confidence']
                                classified_emotion = emotion['Type']
                            # Adiciona as informações da emoção com maior confiança à lista de emoções
                            face_info['classified_emotion'] = classified_emotion
                            face_info['classified_emotion_confidence'] = max_confidence
                    # Adiciona as informações da face à lista de faces
                    faces_info.append(face_info)
                
                # Monta o corpo da resposta
                body = {
                    "url_to_image": f"https://{bucket}.s3.amazonaws.com/{imageName}",
                    "created_image": creation_date,  
                    "faces": faces_info
                }
                # Monta a resposta completa
                response = {"statusCode": 200, "body": json.dumps(body, indent=4, separators=(',', ': '))}
                return response
            else:
                # Se nenhuma face foi detectada na imagem adiciona valor None nas características
                faces_info.append({
                            "position": {
                            "Height": None,
                            "Left": None,
                            "Top": None,
                            "Width": None
                        },
                        "classified_emotion": None,
                        "classified_emotion_confidence": None
                        })
                # Monta o corpo da resposta
                body = {
                    "url_to_image": f"https://{bucket}.s3.amazonaws.com/{imageName}",
                    "created_image": creation_date,  
                    "faces": faces_info
                }
                # Monta a resposta completa
                return {"statusCode": 500, "body": json.dumps(body)}                

        except Exception as e:
            print("Ocorreu um erro ao acessar o Amazon Rekognition:", e)
            return {"statusCode": 500, "body": "Erro interno do servidor"}