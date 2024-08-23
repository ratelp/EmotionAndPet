import json

class V2Description:
    
    @staticmethod
    def showMessage():
        body = {
            "message": "VISION api version 2."
        }

        response = {"statusCode": 200, "body": json.dumps(body)}

        return response