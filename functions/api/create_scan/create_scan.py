import ipaddress
import socket
import os
import sys
import re
import json
import boto3
import error_handler
import database


def lambda_handler(event, context):
    print(event)
    bodyData = json.loads(event['body'])
    project_id = bodyData['projectId']
    scan_types = bodyData['scanTypes']
    targets = bodyData['targets']
    print(targets)
    validated_targets = []
    error = False
    error_data = {}

    try:
        database.assert_valid_project_id(project_id)
        assert_valid_scan_types(scan_types)
        status = "initializing"
        scan_id = database.write_scan(project_id,scan_types,status)["id"]
        for target in targets:
            ip = get_host_ip(target)
            if is_valid_ip_address(target):
                validated_targets.append({"host": "","ip":target,"is_valid": True})
            elif is_valid_cidr(target):
                for ip in ipaddress.ip_network(target):
                    ip = str(ip)
                    if not ip.endswith(".0"):
                        validated_targets.append({"host": "", "ip": ip,"is_valid": True})
            elif ip != target and is_valid_hostname(target):
                validated_targets.append({"host": target, "ip": ip,"is_valid": True})
            else:
                validated_targets.append({"host": target, "ip": "","is_valid": False, "error_message": "If an IP address was provided, it is either invalid or private."})

        database.write_project_targets(project_id, scan_id, validated_targets)
        execute_scan(project_id, scan_id)


    except Exception as e:
        error_handler.handleError(e)

    return {
        "validated_targets": validated_targets,
        "error": error,
        "error_data": error_data
    }


def assert_valid_scan_types(scan_types):
    print(scan_types)
    assert isinstance(scan_types['ports'],bool)
    assert isinstance(scan_types['content'],bool)

def is_valid_ip_address(ip):
    try:
        assert(ipaddress.ip_address(ip).is_global == True)
        return True
    except:
        return False

def is_valid_cidr(cidr):
    try:
        assert ipaddress.ip_network(cidr).is_global == True
        return True
    except:
        return False

def get_host_ip(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        return ""

def is_valid_hostname(hostname):
    try:
        parts = list(filter(None,hostname.split('.')))
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        assert (len(hostname) < 255)
        assert(len(parts) > 1)
        assert(all(allowed.match(x) for x in parts))
        return True
    except AssertionError as e:
        return False

def execute_scan(project_id, scan_id):
    arn = os.environ["ScanExecutedArn"]
    message = {"project_id": project_id, "scan_id": scan_id}
    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')