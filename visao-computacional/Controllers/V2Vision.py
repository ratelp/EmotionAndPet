import json
import boto3

class V2Vision:
    @staticmethod
    def petRekognizer(parameters):
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

        # Inicializa serviços AWS
        rekog_client = boto3.client('rekognition')
        s3_client = boto3.client('s3')
        bedrock_client = boto3.client('bedrock-runtime')
       
        # Verifica existência do bucket e da imagem informados
        try:
            file_meta = s3_client.head_object(Bucket=bucket, Key=imageName)
        except:
            body = {
                "message": "Erro ao acessar o arquivo informado!"
            }

            response = {"statusCode": 500, "body": json.dumps(body)}

            return response

        # Executa reconhecimento da imagem localizando Animais e pets
        rekogResponse = rekog_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': imageName
                }
            },
            Settings={
                'GeneralLabels': {
                    'LabelCategoryInclusionFilters': ['Animals and Pets']
                }
            },
        )
        
        # Verifica se na imagem possui algum pet ou animal
        if rekogResponse['Labels'] == []:
            body = {
                "message": "Não foi localizado nenhum pet na imagem"
            }

            response = {"statusCode": 500, "body": json.dumps(body)}

            return response

        # Salva log no Cloudwatch
        print(rekogResponse)

        # Exclui labels ambíguas para o prompt
        exclude_labels = ["Canine", "Mammal", "Animal", "Pet", "Puppy", "Accessories"]
        filtered_labels = [label for label in rekogResponse['Labels'] if label['Name'] not in exclude_labels]

        # Prompt utilizado para o Bedrock
        promptText = f'''Contexto: O intuito deste prompt é gerar informações específicas a respeito de uma determinada raça de animal. A raça do pet está incluída dentre os parâmetros abaixo. As informações a serem dadas estão no tópico de instruções. A resposta gerada será enviada diretamente ao usuário final, portanto, responda somente com o texto solicitado.

        Parâmetros: {[label['Name'] for label in filtered_labels]}
        
        Tarefa: Abstraia o parâmetro referente à raça do animal em questão e formule uma resposta seguindo às intruções passadas. Siga exatamente o formato demonstrado a seguir, apenas substituindo as partes entre parênteses pelo respectivo texto solicitado.
        
        Exemplo:
        "Dicas sobre (raça abstraída dos parâmetros):
        - Nível de Energia e Necessidades de Exercícios: (texto curto e objetivo descrevendo a respeito do Nível de Energia e Necessidades de Exercícios referentes à raça recebida nos parâmetros).
        - Temperamento e Comportamento: (texto curto e objetivo descrevendo a respeito do Temperamento e Comportamento referentes à raça recebida nos parâmetros).
        - Cuidados e Necessidades: (texto curto e objetivo descrevendo a respeito dos Cuidados e Necessidades referentes à raça recebida nos parâmetros).
        - Problemas de Saúde Comuns: (texto curto e objetivo descrevendo a respeito dos Problemas de Saúde Comuns referentes à raça recebida nos parâmetros)."

        Instruções: 
        - A resposta deve conter um texto curto e objetivo para cada um dos seguintes tópicos a respeito da raça presente nos parâmetros: Nível de Energia e Necessidades de Exercícios, Temperamento e Comportamento, Cuidados e Necessidades, Problemas de Saúde Comuns;
        - A resposta deve estar em português do Brasil.
        '''
        # Anexa parâmetros do bedrock
        bodyBedrock = json.dumps({
            "prompt": promptText,
            "max_tokens": 500,
            "top_p": 0.9,
            "temperature": 0.1
        })

        # Informações do cabeçalho da requisição
        modelId = 'mistral.mistral-large-2402-v1:0'
        accept = 'application/json'
        contentType = 'application/json'

        # Gera resposta com o modelo escolhido do bedrock a partir das informações coletadas
        bedrockResponse = bedrock_client.invoke_model(body=bodyBedrock, modelId=modelId, accept=accept, contentType=contentType)
        bedrockResponse = json.loads(bedrockResponse["body"].read())
        tip = bedrockResponse.get('outputs')[0]['text'].replace("\n      ", "")
       
        # Garante que a resposta tenha 4 labels completando com as labels não filtradas ou tirando labels excedentes
        n_response_labels = 4
        if len(filtered_labels) >= n_response_labels:
            response_labels = filtered_labels[:n_response_labels]
        elif len(filtered_labels) < n_response_labels:
            unused_labels = [label for label in rekogResponse['Labels'] if label not in filtered_labels]
            response_labels = filtered_labels + unused_labels[:n_response_labels-len(filtered_labels)]
        else:
            response_labels = filtered_labels

        # Monta o corpo da resposta
        body = {
            "url_to_image": f"https://{bucket}.s3.amazonaws.com/{imageName}",
            "created_image": file_meta['LastModified'].strftime("%d-%m-%Y %H:%M:%S"),
            "labels": [{'Confidence': label['Confidence'], 'Name': label['Name']} for label in response_labels],
            "Dicas": tip
        }

        # Monta a resposta completa
        response = {"statusCode": 200, "body": json.dumps(body)}

        return response
