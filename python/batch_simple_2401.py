# Common Function library for DDMAP SIMPLE File Processing
# aws s3 cp batch_simple.py s3://wc2h-dtl-prd-code/common/batch_simple.py

import json
import os
import boto3
from datetime import datetime, timedelta

if 'AWS_DEFAULT_REGION' not in os.environ.keys():
    os.environ['AWS_DEFAULT_REGION'] = 'us-gov-west-1'

### <<< DynDB Batch table functions ...
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

if 'DynDbBatchTable' not in os.environ.keys():
    os.environ['DynDbBatchTable'] = 'dtl-prd-SMPL0-batch'

dynDb_client = boto3.client('dynamodb')
dynDb_resource = boto3.resource('dynamodb')

def dynamo_obj_to_python_obj(dynamo_obj: dict) -> dict:
    deserializer = TypeDeserializer()
    return {
        k: deserializer.deserialize(v) 
        for k, v in dynamo_obj.items()
    }  
  
def python_obj_to_dynamo_obj(python_obj: dict) -> dict:
    serializer = TypeSerializer()
    return {
        k: serializer.serialize(v)
        for k, v in python_obj.items()
    }

def get_batch( batch_id, object_id='', tablename = os.environ['DynDbBatchTable'] ):
    if object_id == '':
        object_id = batch_id
    
    resp = dynDb_client.query(
            ExpressionAttributeValues = { ':b' : { 'S': batch_id }, },
            KeyConditionExpression = 'BatchId = :b',
            TableName = tablename
        )

    batch_record = {}
    batch_items = []
    for item_dyn in resp['Items']:
        item_py = dynamo_obj_to_python_obj(item_dyn)
        if item_py['BatchId'] == item_py['ObjectId']:
            batch_record = item_py
        else:
            batch_items.append(item_py)

    batch = {
        "Batch" : batch_record,
        "BatchObjects" : batch_items
    }
    return batch

def put_batch( item, tablename = os.environ['DynDbBatchTable'] ):
    dynDb_table = dynDb_resource.Table( tablename )
    
    expiry = datetime.now() + timedelta(days=32)
    item['Expiry'] = str(expiry.timestamp())  # ToDo must store as top-level Number
    
    resp = dynDb_table.put_item (
        Item = item )
    
    return resp


def check_batch_status(batch_id, display=True):

    batch = get_batch( batch_id )
    batch_rec = batch['Batch']

    status = []
    batch_rec['Status'] = "PENDING"
    batch_count=0
    
    for item in batch['BatchObjects']:
        
        item['Status'] = 'COMPLETED'
        for subitem in item.keys():
            if subitem.startswith('Step-'):
                if item[subitem]['Status'] != 'COMPLETED':
                    item['Status'] = item[subitem]['Status']
        com.put_batch(item)
                    
        status.append( item['Status'])
        batch_count += 1
        
    file_counts = { 'BATCH' : batch_count }
    set = {*status}
    for item in set:
        file_counts.update( { item : status.count(item) } )

    if 'FAILED' in file_counts.keys() or 'INVALID' in file_counts.keys():
        batch_status = 'FAILED'
    elif 'INGESTED' in file_counts.keys():
        batch_status = 'PARTIAL'
    elif 'PENDING' in file_counts.keys() or 'RUNNING' in file_counts.keys():
        batch_status = 'RUNNING'
    else:
        batch_status = 'SUCCEEDED'

    batch_rec.update ({
        'Status' : batch_status,
        'FileCounts' : json.dumps(file_counts)
    })
    com.put_batch(batch_rec)

    return {
        "BatchId" : batch_id,
        "Status"  : batch_status,
        "FileCounts" : json.dumps(file_counts)
    }



### ... end DynDB Batch table functions >>>

### <<< Glue Catalog functions ...
import awswrangler as wr

def set_glue_db_and_table( glue_dbname, glue_table_name, glue_table_path, glue_coltypes, partition_cnt=1 ):
    # Create Glue Database and/or Table if not found
    if glue_dbname in wr.catalog.databases().values:
        print(f"Existing Glue Database: {glue_dbname}")
    else:
        wr.catalog.create_database(glue_dbname) #ToDo Description, Location, pkcols, etc
        print(f"Created Glue Database: {glue_dbname}")
    
    glue_tables = wr.catalog.tables(database=glue_dbname, limit=1000)
    if glue_table_name  in glue_tables['Table'].tolist():
        print(f"Existing Glue Table: {glue_table_name}" )
    else:
        partition_types={}
        for i in range(partition_cnt):
            partition_types.update ({ f"partition_{int(i)}" : 'string' })
            
        wr.catalog.create_parquet_table(
            database=glue_dbname,
            table=glue_table_name,
            path=glue_table_path,
            partitions_types=partition_types,
            compression='snappy',
            description='Auto-generated by ingest',
            #parameters={'source': meta_source },
            #columns_comments={'col0': 'Column 0.', 'col1': 'Column 1.', 'col2': 'Partition.'},
            columns_types=glue_coltypes
        )    
        print(f"Created Glue Table: {glue_table_name}" )

def add_glue_partition( glue_dbname, glue_tablename, s3_outpath, partition ):
    # Catalog as Glue Partition
    # if glue table exists : else first create table ...
    wr.catalog.add_parquet_partitions(
        database = glue_dbname,
        table=glue_tablename,
        partitions_values = { s3_outpath: [ partition ] }
    )
    msg = f"Created Glue Partition: '{partition}' in Database.Table: '{glue_dbname}.{glue_tablename}'"
    print( msg )
    return msg


def set_glue_table_partitions( glue_dbname, glue_tablename, partition_s3url, partition_cnt=1, mode='append', pattern='.' ):
    '''
    Mangage Glue Table Partitions based on S3 Folder URL(s)
        partition_s3url = S3 URL that contains the data set
        partition_count = number of partition subfolders from end of partition_s3url
            e.g., 
            partition_s3url = 's3://wc2h-dtl-prd-datalake/DQRESULT/xstg_afacctbal/D230925.EVALRULES/'
            partition_count = 2
            partition_vals  = ['xstg_afacctbal', 'D230925.EVALRULES']
        mode = [append|replace|refresh]
            - append  -- add partition_url to existing list of partitions 
            - replace -- delete existing partitions and replace with partition_url only
            - refresh -- delete existing partitions and replace with query of S3 subfolders by RegEx pattern
        pattern = pattern of subfolder names for refresh
            [Unload|Delta|Delete|Full]
        
    '''
    folder = partition_s3url.replace('s3://','')
    s = folder[:-1].split('/')
    table_subfolder = '/'.join(s[1:len(s)-partition_cnt])
    partitions_values = {
        partition_s3url : s[-partition_cnt:]
    }
    s3_bucket = s[0]
    #print(s3_bucket,table_subfolder,partitions_values)
    
    if mode in ('replace', 'refresh'): # first delete partitions we will replace/refresh
        ex_partitions = wr.catalog.get_partitions(
            database = glue_dbname, 
            table = glue_tablename )

        partitions_2delete = []
        for k,v in ex_partitions.items():
            partitions_2delete.append(v)

        wr.catalog.delete_partitions(
            database = glue_dbname, 
            table = glue_tablename, 
            partitions_values = partitions_2delete)

    if mode == 'refresh':  # find folders that comprise the refreshed set of partitions
        s3_folders = get_namelist_by_S3pattern( 
            s3_bucket, 
            pattern,              # e.g., 'Unload|Delta', 'Unload.D230531', 'Delta.D2306', etc. (default '.'=all)
            Folder = table_subfolder )

        partitions_values = {}
        for folder in s3_folders:
            s = folder[:-1].split('/')
            partitions_values[f"s3://{folder}"] = s[-partition_cnt:]

    # add the new set of partitions
    print(partitions_values)
    
    wr.catalog.add_parquet_partitions(
        database = glue_dbname, 
        table = glue_tablename, 
        partitions_values=partitions_values)
    
    msg = f'Set Partitions for {glue_dbname}.{glue_tablename}, {mode}:\n{partitions_values}'
    print( msg )
    return msg

'''
e.g.,
for glue_tablename in tablenames['Table'].to_list():
    partition_s3url = f's3://{parms["S3Datalake"]["Bucket"]}/{parms["S3Datalake"]["Output"]}/{glue_tablename}'
    if glue_tablename.startswith('xstg'):
        set_glue_table_partitions( parms["GlueDatabaseName"], glue_tablename, partition_s3url, mode='refresh', pattern='.' )
    #break

'''
    
### ... end Glue Catalog functions >>>

### <<< Redshift functions ...
def get_redshift_table_metadata( table_name, schemaname = 'dw', glue_redshift_connector = 'dtl-prd-redshift-fsdatalake' ):
    sql = f"""
    select trim(ddl) from admin.v_generate_tbl_ddl 
     where tablename = '{table_name.lower()}'
       and schemaname = '{schemaname}'
       and seq between 100000000 and 299999998;"""
    
    con = wr.redshift.connect( glue_redshift_connector )
    
    df_rsmeta = wr.redshift.read_sql_query(
        sql=sql,
        con=con
    )
    rs_ddl = {}
    pkcols = None

    for ddl in list(df_rsmeta['btrim']):
        ddl = ddl.replace('\t,','').replace('"','')   #.replace(',','')
        if 'PRIMARY KEY' in ddl:
            pkcols = ddl[ddl.find('(')+1:-1].replace(' ','').split(',')
        else:
            rs_ddl[ ddl.split()[0] ] = ddl.split()[1]
            
    return rs_ddl, pkcols


def redshift_type_convert( ddl_type ):
    # 
    ddl_type = ddl_type.lower()
    spark_type = ''
    glue_type = ''
    
    if ddl_type in ('bigint', 'int', 'integer', 'smallint', 'date', 'timestamp','string'): # boolean
        glue_type = ddl_type
        spark_type = ddl_type
    if ddl_type == 'bigint':
        spark_type = 'long'
    if ddl_type == 'integer': 
        glue_type = 'int'
        spark_type = 'int'
    if ddl_type == 'smallint': # INT2, 2-byte signed
        spark_type = 'short'
    #if ddl_type == 'timestamp': 
    #    spark_type = 'datetime64[ns]'
    if ddl_type.startswith('double'):
            spark_type = 'double'
            glue_type  = 'double'
    if ddl_type.startswith('numeric') or ddl_type.startswith('decimal'):
        if ddl_type.endswith(',0)'):
            spark_type = 'long'
            glue_type  = 'bigint'
        else:
            #spark_type = 'double'
            #glue_type  = 'double'
            spark_type  = ddl_type.replace('numeric','decimal')
            glue_type  = ddl_type.replace('numeric','decimal')
    if 'char' in ddl_type: # char(n), varchar(n):
        spark_type = 'string'
        glue_type  = 'string'
    if not spark_type:
        print(f"Warning -- Unsupported Redshift type: {ddl_type}, default to 'string'")
        spark_type = 'string'
        glue_type  = 'string'
        
    return spark_type, glue_type

### ... end Redshift functions >>>

### <<< S3 Functions ...
def get_namelist_by_S3pattern( s3_bucket, pattern, **kwargs):

    """
    Loop thru all_objects and return a namelist (list of strings) matching the RegEx pattern

    Parameters
    ----------
    pattern : str
        RegEx pattern by which to filter S3 Object names.

    ExpandFolders : True | False (default)
        When True, namelist returns all files including 'partial' ones created by Redshift UNLOAD, EMR, and DUDE Split_S3_Object
        When False, namelist returns 'prefix' up to the last '/'

    PrintList : True | False (default)
        When True, 'pretty print' list of S3 objects with human-formatted object size and last mod date.
        NOTE: Prints ALL matching objects, even when ExpandFolders=False to return folders only.
    """
    import re
    import boto3
    
    pattern = re.compile( pattern )
    namelist = list()
    expand_folders = False
    print_list = False
    format_str = "{:<70}\t{:<12}\t{}"
    s3_client = boto3.client('s3')

    for k,v in kwargs.items():
        if k=='ExpandFolders':
            expand_folders = v
        elif k=='PrintList':
            print_list = v
        elif k=="Folder":
            folder = v
        elif k=="S3Client": # override
            s3_client = v

    response = s3_client.list_objects_v2(
        Bucket = s3_bucket,
        Prefix = folder
    )
    objects = response['Contents']
    #return response

    while 'NextContinuationToken' in response:
        response = s3_client.list_objects_v2(
            Bucket = s3_bucket,
            Prefix = folder,
            ContinuationToken=response['NextContinuationToken']
        )
        objects.extend(response['Contents'])

    for object in objects:
        object_key = object['Key']
        if pattern.search( object['Key'] ):
            if not expand_folders:
                suffix = object_key[object_key.rfind('/'):]
                object_key = object_key[:object_key.rfind('/')+1] # ... truncate to folder name only
            
            namelist.append( s3_bucket + '/' + object_key )
 
    nameset = {*namelist}  # convert to unique set of object and/or folder names
    namelist = [*nameset]
    namelist.sort()

    return namelist

def get_s3_client( profile_name='default', region_name='us_gov_west_1', **kwargs ):

    print(kwargs)

    session = boto3.Session(profile_name=profile_name, region_name=region_name)

    s3_client = session.client('s3')

    if "CrossAccountRoleArn" in kwargs.keys():
        # create a Security Token Service client
        # ref: https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html
        sts_client=session.client('sts')

        # Call the assume_role method of the STSConnection object,
        # passing the Role ARN and a session name
        assumed_role_object = sts_client.assume_role(
            RoleArn = kwargs['CrossAccountRoleArn'],
            RoleSessionName = "CrossAccountRole"
        )
        # From the response that contains the assumed role, get the temporary 
        # credentials that can be used to make subsequent API calls
        credentials = assumed_role_object['Credentials']
        #print(json.dumps(credentials, default=str))

        s3_client = session.client(
            's3',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
        )
        print(f"Assumed Role for S3 Client: {kwargs['CrossAccountRoleArn']}")

    elif "SsmParmNameArn" in kwargs.keys(): 
        print( "Get Credentials from Simple System Manager (SSM) ...")
        arn = kwargs['SsmParmNameArn']
        parm_name = arn[arn.find('parameter/')+10:]

        ssm = boto3.client('ssm')
        resp = ssm.get_parameter(
            Name= parm_name,
            WithDecryption=True
        )
        parms = resp['Parameter']['Value']
        parms = json.loads(parms.replace("\'",""))

        # create 'remote' session for TROR bucket access
        boto3_remote = boto3.Session(
            aws_access_key_id = parms['AccessKeyId'],
            aws_secret_access_key = parms['SecretAccessKey'],
            region_name = 'us-east-1'
        )

        s3_client = boto3_remote.client('s3')
        print(boto3_remote, s3_client)

    elif "SecretsMgrArn" in kwargs.keys(): # ToDo
        print( "Get Credentials from Secrets Manager not implemented -- using default session")

    return s3_client

def get_s3_object( objname, s3_client=boto3.client('s3')):
    import uuid
    tempfile = f"./tmp/{str(uuid.uuid1())}"

    #print(f"GET S3 Object {objname} into {tempfile}")

    from pathlib import Path
    Path("./tmp").mkdir(parents=True, exist_ok=True)

    objname = objname.replace('s3://','')
    bucket_name = objname[:objname.find('/')]
    object_key  = objname[objname.find('/')+1:]

    with open(tempfile, 'wb') as data:
        s3_client.download_fileobj(bucket_name, object_key, data)

    return tempfile

def put_s3_object( objname, tempfile, s3_client=boto3.client('s3') ):
    #print(f"PUT S3 Object {objname} from {tempfile}") 

    objname = objname.replace('s3://','')
    bucket_name = objname[:objname.find('/')]
    object_key  = objname[objname.find('/')+1:]

    with open(tempfile, 'rb') as data:
        s3_client.upload_fileobj(data, bucket_name, object_key )

    os.remove(tempfile)

    return

    

def delete_s3_object( objname, s3_client=boto3.client('s3')):
    #5'9print(f"DELETE S3 Object {objname}") 

    objname = objname.replace('s3://','')
    bucket_name = objname[:objname.find('/')]
    object_key  = objname[objname.find('/')+1:]

    return s3_client.delete_object(Bucket = bucket_name, Key = object_key )


def get_virt_mem():
    import psutil
    size = psutil.virtual_memory().available

    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1

    return 'Virtual Memory Available {0:.3g} '.format(size) + power_labels[n]



