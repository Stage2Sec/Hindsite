import json
from time import sleep
import boto3
import socket
import urllib.request
import ssl
import os
import error_handler
import database

def lambda_handler(event, context):
    print(event)
    message = json.loads(event['Records'][0]["Sns"]["Message"])
    project_id = message['project_id']
    target_record = message['target_record']
    scan_id = target_record['scan_id']
    target_id = target_record['id']
    ports = message['scan_list']
    task_number = message['task_number']
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

        results = scan_target(target, ports)
        for result in results:
            if result['status'] == 'open':
                if result['protocol'] in ['http','https']:
                    pass
                    # queue_http_content_scan(project_id, target_record, result['protocol'], result['port'])
        record_results(scan_id,target_record['id'], results)
        database.unlock_task_record(task_queue_id)
    except Exception as e:
        error_handler.handleError(e)

def scan_target(target, ports):
    results = []

    for port in ports:
        port = int(port)

        port_status = get_port_status(target,port)
        if port_status == 'open':
            protocol,banner = get_port_data(target,port)
        else:
            protocol = get_default_port_protocol(port)
            banner = ''

        results.append({'port': port,'status':port_status,'protocol':protocol,'banner':banner})

    return results

def get_port_status(target,port):
    try:
        s = get_socket_connection(target,port)
        s.close()
        return 'open'
    except socket.timeout as e:
        return 'filtered'
    except ConnectionRefusedError:
        return 'closed'

def get_port_data(target,port):
    protocol = get_port_protocol(target,port)
    banner = get_port_banner(target,port,protocol)

    return protocol,banner

def get_port_protocol(target,port):
    protocol_functions = {'http': is_http, 'https': is_https}
    for protocol in protocol_functions:
        try:
            if protocol_functions[protocol](target,port):
                return protocol
        except Exception as e:
            print('protocol exception')
            print(e)
    return get_default_port_protocol(port)

def get_port_banner(target,port,protocol):
    banner_functions = {'http': get_http_banner, 'https': get_https_banner,'unknown': get_default_banner}
    try:
        return banner_functions[protocol](target,port)
    except Exception as e:
        print(e)
        return ''

def get_default_banner(target,port):
    s = get_socket_connection(target, port)
    banner = s.recv(4096)
    s.close()
    return banner

def get_http_banner(target,port):
    return str(urllib.request.urlopen("http://{0}:{1}".format(target, port)).headers)

def get_https_banner(target,port):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.urlopen("https://{0}:{1}".format(target,port), context=ctx).headers()

def get_socket_connection(target,port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(5)
    s.connect((target,port))

    return s

def get_default_port_protocol(port):
    try:
        return str(socket.getservbyport(port)) + '?'
    except OSError:
        return 'unknown'

def is_http(target,port):
    s = get_socket_connection(target, port)
    s.sendall(bytes("GET / HTTP/1.1\r\n\r\n", 'utf8'))
    response = s.recv(4096)
    s.close()
    return response.startswith(b'HTTP')

def is_https(target,port):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    urllib.request.urlopen("https://{0}:{1}".format(target, port), context=ctx).read()
    return True


def record_results(scan_id,target_id, results):
    insert_values = ""
    for result in results:
        insert_values += "({0},{1},{2},'{3}','{4}','{5}'),".format(
            scan_id,
            target_id,
            result['port'],
            result['status'],
            result['protocol'],
            result['banner'])
    insert_values = insert_values.rstrip(',')
    return database.create_port_record(insert_values)

def queue_http_content_scan(project_id, target_record, protocol, port):
    arn = os.environ["ValidatedTargetsArn"]
    message = {
        'project_id': project_id,
        'target_record': target_record,
        'scan_type': "content",
        'additional_params': {"starting_path": "/", "protocol": protocol, "port": port}
    }

    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')
