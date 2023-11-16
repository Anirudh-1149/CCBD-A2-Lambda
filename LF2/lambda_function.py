import json
import os

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import base64
import random
from collections import namedtuple

Pair = namedtuple("Pair", ["name", "bucket"])

REGION = 'us-east-1'
HOST = os.environ.get('OSDOMAINEP')
INDEX = 'photosv5'
BOTID = os.environ.get('BOTID')
BOTALIASID = os.environ.get('BOTALIASID')


def lambda_handler(event, context):
    print('testing demo')
    if not ('queryStringParameters' in event) :
        return {}
    searchInput = event['queryStringParameters']['q']
    response = disambiguate(searchInput)
    return response


def disambiguate(searchText):
    lexClient = boto3.client('lexv2-runtime')
    bot_Id = BOTID
    botAlias_Id = BOTALIASID
    
    lex_response = lexClient.recognize_text(
        botId = bot_Id,
        botAliasId = botAlias_Id,
        localeId='en_US',
        sessionId=('testuser' + str(random.randint(1, 1000))),
        text=searchText)
    
    labels = set()
    if 'slots' in lex_response['sessionState']['intent']:
        if 'dog' in lex_response['sessionState']['intent']['slots'] and lex_response['sessionState']['intent']['slots']['dog'] is not None and 'interpretedValue' in lex_response['sessionState']['intent']['slots']['dog']['value']:
            labels.update(lex_response['sessionState']['intent']['slots']['dog']['value']['interpretedValue'].split())
            print(lex_response['sessionState']['intent']['slots']['dog']['value']['interpretedValue'])
            
        if 'cat' in lex_response['sessionState']['intent']['slots'] and lex_response['sessionState']['intent']['slots']['cat'] is not None and 'interpretedValue' in lex_response['sessionState']['intent']['slots']['cat']['value']:
            labels.update(lex_response['sessionState']['intent']['slots']['cat']['value']['interpretedValue'].split())
            print(lex_response['sessionState']['intent']['slots']['cat']['value']['interpretedValue'].split())

    photos = set()
    labels = list(labels)
    labels = labels[:2]
    
    final_labels = []
    for label in labels :
        if label[-1] == 's' or label[-1] == 'S' :
            final_labels.append(label[:-1])
        final_labels.append(label)
            
    for label in final_labels :
        for photo in query(label) :
            print(photo)
            photos.add(Pair(photo['objectKey'], photo['bucket']))
            
    Images = []
    s3_client = boto3.client('s3')
    photos = list(photos)
    for photo in photos[:4]:
        s3_response = s3_client.get_object(Bucket=photo.bucket, Key=photo.name)
        image_read = s3_response['Body'].read()
        print(image_read)
        base64_encode = base64.b64encode(image_read)
        print(base64_encode)
        utf8_decode = base64_encode.decode('utf-8')
        print(utf8_decode)
        image_base64 = utf8_decode
        Image = {
            'name' : photo.name,
            'data' : image_base64
        }
        Images.append(json.dumps(Image))
        
    Images_stringed = ','.join(Images)
    Images_stringed = '[' + Images_stringed + ']'
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": Images_stringed
    }
        
    print(response)
    return response
    
        
        


def query(term):
    print(term)
    q = {'size': 10, 'query': {'multi_match': {'query': term, "fields":['labels']}}}
    # q = {"size": 10, "query": {"match_all": {}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=('master', 'Columbia@123'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)

    res = client.search(index=INDEX, body=q)
    print(res)

    hits = res['hits']['hits']
    results = []
    for hit in hits:
        results.append(hit['_source'])

    return results


def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

