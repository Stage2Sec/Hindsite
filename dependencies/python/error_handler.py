import traceback


def handleError(e):
    print(traceback.format_exc())

    return {"statusCode": 200}