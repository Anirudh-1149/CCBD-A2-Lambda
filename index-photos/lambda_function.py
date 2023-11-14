import json
import logging
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

REGION = 'us-east-1'
HOST = os.environ.get('OSDOMAINEP')
INDEX = 'photosv5'



def lambda_handler(event, context):
    print('testing code pipeline')
    print(event)
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_name = event['Records'][0]['s3']['object']['key']
    logger.debug("[Bucket]: {}".format(bucket_name))
    logger.debug("[Object]: {}".format(object_name))

    session = boto3.Session()
    rek_client = session.client('rekognition')
    
    s3_client = boto3.client('s3')
    s3_resp = s3_client.head_object(Bucket = bucket_name, Key = object_name)
    
    print(s3_resp['Metadata'])
    
    if 'customlabels' in s3_resp['Metadata']:
        cust_labels = s3_resp['Metadata']['customlabels'].split(',')
    else:
        cust_labels = []

    rek_response = rek_client.detect_labels(Image={'S3Object': {'Bucket': bucket_name, 'Name': object_name}}, MaxLabels=12)
    print(rek_response)
    logger.debug("[Rekognition response]: {}".format(rek_response))
    labels = []
    for label in rek_response['Labels']:
        labels.append(label['Name'])
    
    labels.extend(cust_labels)
    logger.debug("[Custom Image Labels]: {}".format(cust_labels))

    logger.debug("[Extracted Image Labels]: {}".format(labels))

    logger.debug("Image Labels Extracted Successfully!")

    os_client = OpenSearch(
        hosts=[{'host': HOST, 'port': 443}],
        http_auth=('master', 'Columbia@123'),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    if INDEX in os_client.indices.get_alias("*"):
        logger.debug('index: {} is in the domain'.format(INDEX))
    else:
        logger.debug('index: {} is not in the domain. Trying to create the index.'.format(INDEX))
        index_creation_response = os_client.indices.create(INDEX)
        logger.debug('Response from creating index: {}'.format(index_creation_response))

    document = {}
    document['objectKey'] = object_name
    document['bucket'] = bucket_name
    document['createdTimestamp'] = event['Records'][0]['eventTime']
    document['labels'] = labels

    document_index_response = os_client.index(
        index=INDEX,
        body=document,
        id=document['objectKey'],
        refresh=True
    )

    logger.debug("document indexing response: {}".format(document_index_response))

    lfr = "Image Labels Extracted Successfully and document indexed to opensearch"
        

    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            'Content-Type': 'application/json'
        },
        'body': json.dumps(lfr)
    }
    
