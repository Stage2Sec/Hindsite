import os
import error_handler
import database
import json
import response_formatter

def lambda_handler(event, context):
    print(event)
    try:
        projectName = json.loads(event['body'])['projectName']
        result = database.createProject(projectName)
        return response_formatter.formatSuccessfulResponse(result)

    except Exception as e:
        error_handler.handleError(e)