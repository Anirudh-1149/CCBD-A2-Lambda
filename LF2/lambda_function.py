import json
import os

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import base64
import random

REGION = 'us-east-1'
HOST = 'search-photos-sprxtx43pjj4g6j4co4lhgtivq.us-east-1.es.amazonaws.com'
INDEX = 'photos'


def lambda_handler(event, context):
    print('test')
    if not ('queryStringParameters' in event) :
        return {}
    searchInput = event['queryStringParameters']['q']
    response = disambiguate(searchInput)
    return response


def disambiguate(searchText):
    lexClient = boto3.client('lexv2-runtime')
    bot_Id = 'OPJAKKFGGH'
    botAlias_Id = 'TSTALIASID'
    
    lex_response = lexClient.recognize_text(
        botId = bot_Id,
        botAliasId = botAlias_Id,
        localeId='en_US',
        sessionId=('testuser' + str(random.randint(1, 1000))),
        text=searchText)
    birds = False
    trees = False
    print(lex_response['sessionState']['intent'])
    if 'slots' in lex_response['sessionState']['intent']:
        if 'bird' in lex_response['sessionState']['intent']['slots'] and lex_response['sessionState']['intent']['slots']['bird'] is not None:
            birds = True
            
        if 'tree' in lex_response['sessionState']['intent']['slots'] and lex_response['sessionState']['intent']['slots']['tree'] is not None:
            trees = True
    photos = []
    if birds : 
        bird_photos = query("dog")
        for photo in bird_photos:
            print(photo)
            photos.append(photo)
    if trees:
        tree_photos = query("cat")
        for photo in tree_photos : 
            photos.append(photo)
    
    Images = []
    s3_client = boto3.client('s3')
    # photos.append({'objectKey':'EldenRing.png'})
    # photos.append({'objectKey': 'image_1.jpeg'})
    print(photos)
    for photo in photos:
        photo_name = photo['objectKey']
        s3_response = s3_client.get_object(Bucket='pawa-b2-ccbd', Key=photo_name)
        print  (s3_response['Body'].read())
        image_base64 = base64.b64encode(s3_response['Body'].read()).decode('utf-8')
        Image = {
            'name' : photo_name,
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
    q = {'size': 10, 'query': {'multi_match': {'query': term, "fields":['labels']}}}
    # q = {"size": 3, "query": {"match_all": {}}}

    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
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
