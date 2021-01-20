import json
import boto3
import time
from datetime import datetime, timezone
from random import randint

TABLE_DB1_NAME = 'DB1'
TABLE_DB2_NAME = 'DB2'
S3_BUCKET_NAME = 'assignment2-fall2020-faces'

def store_visitor(visitor):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
    table = dynamodb.Table(TABLE_DB2_NAME)

    item = {}
    item['faceId'] = visitor['faceId']
    item['name'] = visitor['name']
    item['phoneNumber'] = visitor['phoneNumber']
    item['photos'] = {
    	"objectKey": visitor['objectKey'],
    	"bucket": S3_BUCKET_NAME,
    	"createdTimestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    }
    print(item)	
    response = table.put_item(Item = item)
    return response

def put_passcode_dynamoDB(passcode):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
    table = dynamodb.Table(TABLE_DB1_NAME)
    current_time = int(time.time())
    expireTime = current_time + 300
    item = {
        'passcodes': str(passcode),
        'ttl': expireTime
    }
    table.put_item(Item = item)
    print(item)
    
def query_danymoDB_DB2(dynamodb, faceId):
	response = dynamodb.get_item(
		TableName=TABLE_DB2_NAME,
		Key={
			'faceId': {
				'S': faceId
			},
		}
	)
	return response

def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)

def make_and_store_opt(n):
	passcode = random_with_N_digits(n)
	put_passcode_dynamoDB(passcode)
	return passcode 


def send_opt_sns(sns, passcode, visitor):
	# send sns messgae to visitor
	name = visitor['Item']['name']['S']
	faceId = visitor['Item']['faceId']['S']
	phone_number = visitor['Item']['phoneNumber']['S']
	
	sns_message = 'Hello ' + name + ', here is your OPT: '
	sns_message += str(passcode) + '\n'+ 'Please click the following link to access:\n'
	sns_message += f'http://assignment2-fall2020.s3-website-us-east-1.amazonaws.com/?faceId={faceId}'

	response = (sns_message, phone_number)
	
	print(response)
	response = sns.publish(
	    PhoneNumber = phone_number,
	    Message=sns_message,
	)
	
	return response
    
def lambda_handler(event, context):
    # TODO implement
    ACCESS_HEADERS = {
                "Access-Control-Allow-Headers" : "Content-Type",
                "Access-Control-Allow-Origin" : "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"}
                
    received = event['body']
    if received == None:
        return {
            'statusCode': 200,
            'headers': ACCESS_HEADERS,
            'body': json.dumps(f'Hello from lambda0 None')
        }

    received = received.replace("\'","\"")
    body = json.loads(received)
    print(type(body))
    print(body)
    message = body['message']
    print(event)
    dynamodb = boto3.client('dynamodb')
    sns = boto3.client('sns')
    print(message)
    response = store_visitor(message)
    print(response)
    
    visitor = query_danymoDB_DB2(dynamodb, message['faceId'])
    new_OPT = make_and_store_opt(4)
    sns_response = send_opt_sns(sns, new_OPT, visitor)
    print(response)
    
    return {
        'statusCode': 200,
        'headers': ACCESS_HEADERS,
        'body': json.dumps('Successful submission')
    }
