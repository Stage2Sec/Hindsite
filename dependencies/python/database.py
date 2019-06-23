import boto3
import os


def executeQuery(sqlStatement, secretArn=None, resourceArn=None, setDatabase=True):
    print(sqlStatement)
    print(secretArn)
    print(resourceArn)
    secretArn = secretArn if secretArn else os.environ['DbSecret']
    resourceArn = resourceArn if resourceArn else os.environ['DbEndpoint']

    client = boto3.client('rds-data')

    if setDatabase:
        response = client.execute_statement(
            secretArn = secretArn,
            resourceArn = resourceArn,
            database = 'hs',
            includeResultMetadata=True,
            sql = sqlStatement
        )
    else:
        response = client.execute_statement(
            secretArn=secretArn,
            resourceArn=resourceArn,
            includeResultMetadata=True,
            sql=sqlStatement
        )

    return formatResponse(response)

def formatResponse(response):
    if 'records' in response:
        return formatResponseRecords(response)
    elif len(response['generatedFields']):
        print(response)
        return formatCreateResponse(response)


def formatCreateResponse(response):
    return {"id": response['generatedFields'][0]['longValue']}

def formatResponseRecords(response):
    records = response['records']
    formattedRecords = []
    columns = response['columnMetadata']

    for record in records:
        row = {}
        for fieldIndex in range(0,len(record)):
            row[columns[fieldIndex]['label']] = list(record[fieldIndex].values())[0]
        formattedRecords.append(row)

    return formattedRecords

def getProject(projectId):
    projectRecord = executeQuery("select * from projects where id = {0}".format(projectId))

    return projectRecord[0] if (len(projectRecord)) else projectRecord

def getScanStats(projectId):
    latest_scan = executeQuery("""
            select s1.* from scans s1
            where s1.project_id = {0}
            and s1.created_at = (
              SELECT MAX(s2.created_at)
              FROM scans s2
              WHERE s2.project_id = {0}
            )
        """.format(projectId))
    if len(latest_scan):
        latest_scan = latest_scan[0]
        ports_content = executeQuery("""
                select COUNT(DISTINCT p.id) as port_num, COUNT(DISTINCT r.id) as found_content_num from scans s
                join ports p on p.scan_id = s.id
                join resources r on r.scan_id = s.id
                where s.id = {0}
                and r.is_not_found = 0
                """.format(latest_scan["id"]))

        ports_content = ports_content[0] if len(ports_content) else ports_content

        latest_scan["port_num"] = ports_content["port_num"]
        latest_scan["found_content_num"] = ports_content["found_content_num"]
    else:
        latest_scan = []

    return latest_scan

def getProjectScans(projectId):
    return executeQuery("select * from scans where project_id = {0} order by created_at desc".format(projectId))

def getProjects():
    return executeQuery("select id,name from projects")

def getScanResults(scanId):
    portResults =  executeQuery("""
            select p.id,p.target_id,t.ip,t.host,p.port,p.protocol,p.status,p.banner,p.scan_id 
            from ports p 
            join targets t on t.id = p.target_id
            where p.scan_id = {0}""".format(scanId))

    contentResults = executeQuery("""
            select r.id,r.target_id,t.ip,t.host,r.url,r.code,r.size,r.is_not_found,r.scan_id,r.is_directory,ss.obj_path as screenshot_link,ss.thumbnail from resources r 
            join targets t on t.id = r.target_id
            left join screenshots ss on ss.resource_id = r.id
            where r.scan_id = {0}""".format(scanId))

    return {
        "port_scan_results": portResults,
        "content_scan_results": contentResults
    }

def getScanTargets(scanId):
    return executeQuery("""
            select t.*,s.selected_scans from targets t
            join scans s on s.id = t.scan_id
            where t.scan_id = {0}""".format(scanId))

def getTaskLock(project_id, target_id, task_number):
    scan_task_type = "content_scan"
    return executeQuery(
        "INSERT INTO scan_task_queue(project_id, target_id, task_number,task_type,is_locked) VALUES({0},{1},{2},'{3}',{4})".format(
            project_id,
            target_id,
            task_number,
            scan_task_type,
            False
        ))

def at_max_concurrent_connections(project_id, target_id, task_number):
    result = executeQuery(
        "SELECT COUNT(*) from scan_task_queue WHERE project_id = {0} and target_id = {1} and task_number = {2}".format(
            project_id,
            target_id,
            task_number
        ))

    return result[0]["COUNT(*)"] > 50

def unlock_task_record(task_queue_id):
    return executeQuery("UPDATE scan_task_queue SET is_locked = 0 WHERE id = {0}".format(task_queue_id['id']))

def getProjectScanTargets(projectId, scanId):
    return executeQuery(
        "SELECT id,project_id,scan_id,host,ip,is_valid from targets WHERE project_id = {0} and scan_id = {1}".format(
            projectId, scanId))

def createProject(projectName):
    return executeQuery("INSERT INTO projects(name) VALUES('{0}')".format(projectName))

def get_target_record(targetId):
    return executeQuery("select * from targets where id = {0}".format(targetId))

def create_screenshot_record(conn,cur,project_id, scan_id, target_id, resource_id, obj_path,thumbnail_path):
    return executeQuery("INSERT INTO screenshots(project_id, scan_id, target_id,resource_id,obj_path,thumbnail) VALUES({0},{1}, {2},{3},'{4}','{5}')".format(project_id,scan_id,target_id,resource_id,obj_path,thumbnail_path))

def write_scan(project_id,selected_scans,status):
    flag = get_scan_bit_flag(selected_scans)
    return executeQuery("INSERT INTO scans(project_id,selected_scans,status) VALUES ({0},{1},'{2}')".format(project_id, flag,status))

def write_project_targets(project_id, scan_id, valid_targets):
    targets_insert_values = ""
    print(project_id)
    print(scan_id)
    print(valid_targets)
    for target in valid_targets:
        if target['is_valid']:
            targets_insert_values += "({0},{1},'{2}','{3}',{4},'{5}'),".format(project_id, scan_id, target['host'], target['ip'], True,"")
        else:
            targets_insert_values += "({0},{1},'{2}','{3}',{4},'{5}'),".format(project_id, scan_id, target['host'], target['ip'], False, target['error_message'])
    targets_insert_values = targets_insert_values.rstrip(',')
    print(targets_insert_values)
    return executeQuery("INSERT INTO targets(project_id,scan_id,host,ip,is_valid,error_message) VALUES {0}".format(targets_insert_values))

def assert_valid_project_id(project_id):
    results = executeQuery("select * from projects where id = {0}".format(project_id))
    assert(results[0]["id"] == project_id)

def mark_target_invalid(targetRecord):
    return executeQuery("UPDATE targets SET is_valid = 0 WHERE id = {0}".format(targetRecord['id']))

def create_resource_record(insert_values):
    print(insert_values)
    return executeQuery(
        "INSERT INTO resources(scan_id, target_id, url, code, size, is_not_found, is_directory) VALUES {0}".format(
            insert_values))

def create_port_record(insert_values):
    print(insert_values)
    return executeQuery(
        "INSERT INTO ports(scan_id, target_id, port, status, protocol,banner) VALUES {0}".format(insert_values))

def get_last_insert_id():
    return executeQuery("select last_insert_id()")

def fixResults(results):
    fixed_results = []

    for result in results:
        d = result['created_at']
        d = d.isoformat()
        result['created_at'] = d
        fixed_results.append(result)

    return fixed_results

def get_scan_bit_flag(scans):
    port_scan_bit = 1
    content_scan_bit = 2
    flag = 0
    if 'port' in scans:
        flag = flag | port_scan_bit
    if 'content' in scans:
        flag = flag | content_scan_bit

    return flag