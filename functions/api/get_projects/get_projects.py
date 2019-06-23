import json
import boto3
import os
import error_handler
import database
import response_formatter


def lambda_handler(event, context):
    print(event)
    try:
        projects =  database.getProjects()
        return response_formatter.formatSuccessfulResponse(projects)

    except Exception as e:
        error_handler.handleError(e)