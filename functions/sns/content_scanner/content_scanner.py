from botocore.vendored import requests
import string
import random
from urllib.parse import urljoin
from urllib.parse import urlparse
import json
import boto3
from time import sleep
import sys
import os
import error_handler
import database

def lambda_handler(event, context):
    # print(event)
    message = json.loads(event['Records'][0]["Sns"]["Message"])
    project_id = message['project_id']
    target_record = message['target_record']
    scan_id = target_record['scan_id']
    target_id = target_record['id']
    paths = message['scan_list']
    task_number = message['task_number']
    protocol = message['additional_params']['protocol']
    starting_path = message['additional_params']['starting_path']
    port = message['additional_params']['port']
    target = target_record['host'] if target_record['host'] is not "" else target_record['ip']

    try:
        task_queue_id = database.getTaskLock(project_id, target_id, task_number)
        if not task_queue_id:
            print("Task already processed")
            # this task is being processed by another function or has been before
            return
        loop = 0
        while database.at_max_concurrent_connections(project_id, target_id, task_number) and loop < 10:
            loop += 1
            sleep(5)
        if loop == 10:
            return

        session = requests.session()
        base_url = "{0}://{1}:{2}{3}".format(protocol, target, port,starting_path)
        results = scan_target(session, base_url, paths)
        results = save_target_record(scan_id, target_id, results)
        queue_recursive_scans(project_id, target_record, protocol, port, results)
        queue_content_screenshot(project_id, target_record, results)
        database.unlock_task_record(task_queue_id)

    except Exception as e:
        error_handler.handleError(e)


def scan_target(session, base_url, paths):
    results = []
    not_found_data = get_not_found_type(base_url, session)
    for path in paths:

        url = urljoin(base_url, path)
        response = make_request(session, url)
        response_data = parse_response(response)
        if not is_not_found(response_data, not_found_data):
            response_data['not_found'] = False
            response_data['is_scannable_directory'] = is_scannable_directory(response_data)
            results.append(response_data)

    return results


def get_not_found_type(target, session):
    response = request_missing_resource(target, session)
    not_found_data = {'status_code': response.status_code, 'params': {}}

    if response.status_code in [301, 302]:
        # some servers will append the requested resource to the end of the not found page path as a parameter
        redirect_path = response.headers['location'].rstrip(response.url.split('/')[-1])
        not_found_data['params']['redirect_path'] = redirect_path
    elif response.status_code == 200:
        response2 = request_missing_resource(target, session, rand_len=10)
        response3 = request_missing_resource(target, session, rand_len=20)
        size = len(response.content)
        size2 = len(response2.content)
        size3 = len(response3.content)
        if is_within_ten_percent(size, size2, size3):
            not_found_data['params']['size_upper_range'] = max(size, size2, size3)
            not_found_data['params']['size_lower_range'] = min(size, size2, size3)
        else:
            # TODO handle this exception
            raise Exception("Cannot determine not found condition")

    return not_found_data


def request_missing_resource(target, session, rand_len=6):
    resource = rand_string(rand_len) + 'thisdoesnotexisthere' + rand_string(rand_len)
    url = urljoin(target, resource)
    return make_request(session, url)


def make_request(session, url):
    return session.get(url, allow_redirects=False)

def parse_response(response):
    redirect_path = None
    if 'location' in response.headers:
        redirect_path = response.headers['location']
    return {'requested_path': response.url, 'status_code': response.status_code, 'size': len(response.content),
            'redirect_path': redirect_path}


def save_target_record(scan_id,target_id, results):
    counter = 0
    found_content_positions = []
    insert_values = ""
    if len(results):
        for result in results:
            if not result['not_found']:
                if result['status_code'] == 200:
                    found_content_positions.append(counter)
                # (id,url,code,size)
                insert_values += "({0},{1},'{2}',{3},{4},{5},{6}),".format(
                    scan_id,
                    target_id,
                    result['requested_path'],
                    result['status_code'],
                    result['size'],
                    result['not_found'],
                    result['is_scannable_directory'])
            counter += 1
        insert_values = insert_values.rstrip(',')
        database.create_resource_record(insert_values)
        last_insert_id = database.get_last_insert_id()
        print(last_insert_id)

        for position in found_content_positions:
            results[position]["resource_id"] = (last_insert_id - len(found_content_positions)) + (position -1)

    return results

def queue_recursive_scans(project_id, target_record, protocol, port, results):
    for result in results:
        if result['is_scannable_directory']:
            if result['status_code'] in [302, 301]:
                path = result['redirect_path']
            else:
                path = urlparse(result['requested_path']).path
            queue_scan(project_id, target_record, protocol, port, path)

def queue_content_screenshot(project_id,target_record,results):
    for result in results:
        print("screenshot")
        print(result)
        if result['status_code'] == 200:
            queue_screenshot(project_id, target_record['scan_id'], target_record['id'], result["resource_id"], result['requested_path'])

def queue_screenshot(project_id, scan_id, target_id, resource_id, url):
    arn = os.environ["ContentDiscoveredArn"]
    message = {
        'project_id': project_id,
        'scan_id': scan_id,
        'target_id': target_id,
        'url': url,
        'resource_id': resource_id
    }

    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')

def queue_scan(project_id, target_record, protocol, port, starting_path):
    arn = os.environ["ValidatedTargetsArn"]
    message = {
        'project_id': project_id,
        'target_record': target_record,
        'scan_type': "content",
        'additional_params': {"starting_path": starting_path, "protocol": protocol, "port": port}
    }

    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')


def rand_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def is_within_ten_percent(num1, num2, num3):
    return (.9 * num1) <= num2 <= (1.1 * num1) and (.9 * num1) <= num3 <= (1.1 * num1)


def is_not_found(response_data, not_found_params):
    if response_data['status_code'] != not_found_params['status_code']:
        return False
    if response_data['status_code'] in [404, 500]:
        return True
    if response_data['status_code'] in [301, 302]:
        return response_data['redirect_path'].rstrip(response_data['requested_path'].split('/')[-1]) == \
               not_found_params['params']['redirect_path']
    if response_data['status_code'] == 200:
        return not_found_params['params']['size_lower_range'] <= response_data['size'] <= not_found_params['params'][
            'size_upper_range']


def is_scannable_directory(response_data):
    if response_data['not_found']:
        return response_data['status_code'] in [302, 301] and (
                    response_data['redirect_path'] and response_data['redirect_path'].endswith('/'))
    else:
        return response_data['status_code'] == 200 and response_data['requested_path'].endswith('/')