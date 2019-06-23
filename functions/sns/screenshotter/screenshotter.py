import boto3
import json
import subprocess
import hashlib
import os
import sys
from urllib.parse import urlparse
import error_handler
import database


def lambda_handler(event, context):
    print(event)
    message = json.loads(event['Records'][0]["Sns"]["Message"])
    project_id = message['project_id']
    scan_id = message['scan_id']
    target_id = message['target_id']
    resource_id = message['resource_id']
    url = message['url']
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    width = "1200"
    height = "1024"
    timeout = "5"

    try:
        cmd = [
            "./phantomjs/phantomjs_linux-x86_64",
            "--debug=yes", "--ignore-ssl-errors=true",
            "./phantomjs/screenshot.js",
            url,
            "/tmp/"+url_hash + ".png",
            width,
            height,
            timeout
        ]

        results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        print(results.stdout.read())
        thumbnail_path = create_thumbnail("/tmp/"+url_hash + ".png", url_hash)
        project_record = database.getProject(project_id)
        target_record = database.get_target_record(target_id)
        bucket = os.environ['CoreBucketRef']
        file_name = '/tmp/' + url_hash + ".png"
        key_name = url_hash + '.png'
        thumbnail_key_name = url_hash + '-320.png'
        target = target_record["host"] if target_record["host"] else target_record["ip"]
        obj_path = "{0}/{1}/{2}/{3}".format(project_record["name"], target, urlparse(url).path.rstrip('/').strip('/'), key_name)
        thumbnail_obj_path = "{0}/{1}/{2}/{3}".format(project_record["name"], target, urlparse(url).path.rstrip('/').strip('/'), thumbnail_key_name)
        s3 = boto3.client('s3')
        print(os.listdir('/tmp'))
        print(file_name)
        s3.upload_file(file_name, bucket, obj_path)
        s3.upload_file(thumbnail_path, bucket, thumbnail_obj_path)

        database.create_screenshot_record(project_id, scan_id, target_id, resource_id, obj_path,thumbnail_obj_path)

    except Exception as e:
        error_handler.handleError(e)

def create_thumbnail(path, url_hash):
    thumbnail_path = "/tmp/{0}-320".format(url_hash)
    cmd = ["convert", "-crop", "375x500+0x0", "-thumbnail", "375x500", "-background","white", "-alpha", "remove", path, thumbnail_path]
    results = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    print(results.stdout.read())

    return thumbnail_path
