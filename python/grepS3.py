import boto3
import re

def get_s3_client( profile_name='default', region_name='us-gov-west-1', **kwargs ):

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
    expand_folders = True
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
    if 'Contents' in response.keys():
        objects = response['Contents']
    else:
        print("No matching S3 Objects found! ")
        return namelist
    
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

def grepS3( s3_bucket, search_term, pattern, Folder, S3Client ):

    if search_term == '--listonly':
        op = ''
    else:
        op = 'Searching'

    regexp = re.compile( search_term )

    for objname in get_namelist_by_S3pattern( s3_bucket, pattern, Folder=folder, S3Client=s3_client ):
        print (f"{op} 's3://{objname}' ...")
        if op == 'Searching':
            response = s3_client.get_object(
                Bucket = s3_bucket,
                Key = objname[objname.find('/')+1:]
            )
            body = response['Body'].read().decode()

            for n, line in enumerate(body.split('\n')):
                if re.search(regexp, line):
                    print( f'  line {n}: {line}')

    print('DONE!')
    return 0


import sys
usage = """
usage: python grepS3.py search_term S3_folder S3_filter(opt)
    arguments: 
        search_term = sys.argv[1]   # regular expression to search within files ( "--listonly" to only list S3 file names)
        s3_folder   = sys.argv[2]   # S3 folder/key prefix to select files
        s3_filter   = sys.argv[3]   # regular expression to filter file selection (optional)        
"""
if len(sys.argv) < 3:
    print( usage )
    sys.exit()

# get command line arguments ...
search_term = sys.argv[1]     # regular expression to search within files ( "" to list S3 files only)
s3_folder   = sys.argv[2]     # S3 folder/key prefix to select files
if len(sys.argv) == 4:
    s3_filter = sys.argv[3]   # regular expression to filter file selection (optional)
else:
    s3_filter = '.'

# get environment variables ...
import os
if 'GREPS3_BUCKET' in os.environ.keys():
    bucket = os.environ['GREPS3_BUCKET']
    print( f"Default Bucket '{bucket}'")
else:
    print( "NOTE: Environment Variable 'GREPS3_BUCKET' not found.   s3_folder args must use URI format 's3://{bucket}/{folder}'")

if 'GREPS3_ROLEARN' in os.environ.keys():
    s3_client = get_s3_client( "default", "us-gov-west-1", **{"CrossAccountRoleArn" : os.environ['GREPS3_ROLEARN']} ) 
else:
    print( "NOTE: Environment Variable 'GREPS3_ROLEARN' not found.   S3 Client will default to EC2 Service Role permissions." )
    s3_client = get_s3_client()

# get bucket & folder from S3 URI format (if applicable)
folder = s3_folder
if folder.startswith('s3://'):
    folder = folder[5:]
    bucket = folder[:folder.find('/')]
    folder = folder[folder.find('/')+1:]

grepS3( bucket, search_term, s3_filter, Folder=folder, S3Client=s3_client )

