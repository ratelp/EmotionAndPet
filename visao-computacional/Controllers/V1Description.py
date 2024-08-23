import json

class V1Description:

    @staticmethod
    def showMessage():
        body = {
            "message": "VISION api version 1."
        }

        response = {"statusCode": 200, "body": json.dumps(body)}

        return response