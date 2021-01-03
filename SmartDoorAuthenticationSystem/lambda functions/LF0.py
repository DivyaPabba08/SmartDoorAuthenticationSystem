import json
import boto3
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ACCESS_HEADERS = {
                "Access-Control-Allow-Headers" : "Content-Type",
                "Access-Control-Allow-Origin" : "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"}
TABLE_DB1_NAME = 'DB1'
TABLE_DB2_NAME = 'DB2'
TABLE_DUP_CHECK = 'hw2-LF1-check-duplicate'

def query_danymoDB_DB1(dynamodb, otp, faceId):
    is_grant = False
    response = dynamodb.get_item(
        TableName=TABLE_DB1_NAME,
		Key={
			'passcodes': {
                'S': otp
			},
		}
    )
    if 'Item' in response:
        ttl=response['Item']['ttl']['N']
        current_time = int(time.time())
        print("ttl:", ttl)
        if current_time <=  int(ttl):
            is_grant = True
        response = dynamodb.delete_item(
            TableName=TABLE_DB1_NAME,
            Key={
                'passcodes': {
                    'S': otp
                },
            }
        )
        response = dynamodb.delete_item(
            TableName=TABLE_DUP_CHECK,
            Key={
                'face_id': {
                    'S': faceId
                },
            }
        )
    return is_grant

def query_danymoDB_DB2(dynamodb, faceId):
    a=dynamodb.get_item(
        TableName = TABLE_DB2_NAME,
        Key={'faceId':{'S': faceId},}
    )
    return a

def lambda_handler(event, context):
    '''
    return {
            'statusCode': 200,
            'headers': ACCESS_HEADERS,
            'body': json.dumps(f'Hello from lambda0')
        }
    '''

    # TODO implement
    received = event['body']
    if received == None:
        return {
            'statusCode': 200,
            'headers': ACCESS_HEADERS,
            'body': json.dumps(f'Hello from lambda0 None')
        }
    
    received = received.replace("\'","\"")
    body = json.loads(received)
    faceId = body['message']['faceId']
    otp = body['message']['otp']
    dynamodb = boto3.client('dynamodb')
    
    visitor = query_danymoDB_DB2(dynamodb, faceId)
    
    print(visitor)
    if 'Item' not in visitor:
        return {
            'statusCode': 200,
            'headers': ACCESS_HEADERS,
            'body': json.dumps(f'User Not Found')
        }
    visitor_name = visitor['Item']['name']['S']
    
    is_granted = query_danymoDB_DB1(dynamodb, otp, faceId)
    
    if (is_granted):
        return {
            'statusCode': 200,
            'headers': ACCESS_HEADERS,
            'body': json.dumps(f'Hello {visitor_name}, welcome!')
        }
    
    return {
        'statusCode': 200,
        'headers': ACCESS_HEADERS,
        'body': json.dumps('Sorry, your OTP is not valid')
    }
