import json
from datetime import datetime
import base64
import boto3
from random import randint
import sys
sys.path.insert(1, '/opt')
import cv2
import time
from random import randint


TABLE_DB1_NAME = 'DB1'
TABLE_DB2_NAME = 'DB2'
TABLE_DUP_CHECK = 'hw2-LF1-check-duplicate'
S3_BUCKET_NAME = 'assignment2-fall2020-faces'
OWNER_PHONE_NUMBER = '' 


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

def create_dynamoDB_DB1():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
    dynamodb.create_table(
                            TableName=TABLE_DB1_NAME,
                            KeySchema=[
                                {
                                    'AttributeName': 'passcodes',
                                    'KeyType': 'HASH' 
                                },
                            ],
                            AttributeDefinitions=[
                                {
                                    'AttributeName': 'passcodes',
                                    'AttributeType': 'S'
                                },
                            ],
                            ProvisionedThroughput={
                                'ReadCapacityUnits': 10,
                                'WriteCapacityUnits': 10
                            }
                        )
    time.sleep(10)
    print("After waiting 10s")

def put_visitor_dynamoDB(item):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
    table = dynamodb.Table(TABLE_DB2_NAME)
    table.put_item(Item = item)
    print(item) 


def make_visitors():
    visitors = []
    visitor = {
        'faceId': 'zz2374',
        'name': 'Ziyi Zhu',
        'phoneNumber': ''
    }
    visitors.append(visitor)
    visitor = {
        'faceId': 'sw3504',
        'name': 'Sitong Wang',
        'phoneNumber': ''
    }
    visitors.append(visitor)
    return visitors
    
def store_visitors():
    visitors = make_visitors()
    for visitor in visitors:
        put_visitor_dynamoDB(visitor)
        
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


def create_dynamoDB_DB2():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1') 
    dynamodb.create_table(
                            TableName=TABLE_DB2_NAME,
                            KeySchema=[
                                {
                                    'AttributeName': 'faceId',
                                    'KeyType': 'HASH' 
                                },
                            ],
                            AttributeDefinitions=[
                                {
                                    'AttributeName': 'faceId',
                                    'AttributeType': 'S'
                                },
                            ],
                            ProvisionedThroughput={
                                'ReadCapacityUnits': 10,
                                'WriteCapacityUnits': 10
                            }
                        )
    time.sleep(10)
    print("After waiting 10s")

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

def send_sns_to_owner(sns, event):
    s3 = boto3.resource('s3')
    faceId = event['faceId']
    objectKey = event['objectKey']
    object_acl = s3.ObjectAcl(S3_BUCKET_NAME, objectKey)
    response = object_acl.put(ACL='public-read')
    print(response)
    sns_message = 'Hello, please see the visitor picture:\n'
    #https://assignment2-fall2020-faces.s3.amazonaws.com/aws.jpg
    sns_message += f'https://assignment2-fall2020-faces.s3.amazonaws.com/{objectKey}\n'
    sns_message += 'If you approve this visitor to access, please click the following link:\n'
    sns_message += f'http://assignment2.2-fall2020.s3-website-us-east-1.amazonaws.com/?fileName={objectKey}&faceId={faceId}\n'

    response = (sns_message, OWNER_PHONE_NUMBER)
    
    print(response)
    response = sns.publish(
        PhoneNumber = OWNER_PHONE_NUMBER,
        Message=sns_message,
    )
    
    return response



def get_visitor_photo(fragment_number):
    client = boto3.client('kinesisvideo')
    response = client.get_data_endpoint(
        StreamName='6998-hw2',
        APIName='GET_MEDIA')
    #print("Kinesis Video response for endpoint ", response)
    endpoint = response.get('DataEndpoint', None)
    #print("endpoint %s" % endpoint)
    stream_size = response['ResponseMetadata']['HTTPHeaders']['content-length']

    # use the above endpoint to fetch stream from the GET_MEDIA API of kinesis
    if endpoint is not None:
        client2 = boto3.client('kinesis-video-media', endpoint_url=endpoint,region_name='us-east-1')
        response = client2.get_media(
            StreamName='6998-hw2',
            StartSelector={
                'StartSelectorType': 'NOW',
            }
        )
        print("Response from GET_MEDIA ", response)
        
        # our S# Bucket
        s3 = boto3.client('s3')
        bucket = 'assignment2-fall2020-faces'
        
        
        uid = str(response['ResponseMetadata']['RequestId'])
        image_name = str(uid + ".jpg")
        print('image_name:',image_name)
        name = str("/tmp/" + uid)
        video_path = str(name + ".webm")
        print("video_path",video_path)
        stream_processed = False #to check if stream has been processed so that we can return accordingly
        
        print('Going to try and get stream')
        # open a temp file as write in binary
        with open(video_path, 'wb') as f:
            print("entered file")
            while True:
                try:
                    #print("entered try")
                    stream = response['Payload'] # botocore.response.StreamingBody object of 16 MB read size
                    #print("stream",stream)
                    #print("hih")
                except:
                    stream = None
                if stream is None: #retry to read the fragment
                    #print('stream is None')
                    continue
                else:
                    
                    #print("entered else")
                    # stream.set_socket_timeout(10000)
                    #print("read")
                    l=stream.read(1024*16384)
                    #print("l",l)
                    f.write(l)
                    stream_processed = True
                    print("stream_processed")
                    
                    response = s3.upload_file(video_path, bucket, video_path)
                    # print("response",response)

                    # write the frame to a temp file
                    
                    
                    cap = cv2.VideoCapture(video_path)
                    ret, frame = cap.read()
                    # print("frame",frame)
                    image_path = str(name + ".jpg")
                    cv2.imwrite(image_path, frame)
                    
                    # upload the temp image to s3
                    s3.upload_file(image_path, bucket, image_name)
                    cap.release()
                    # s3.put_object(Bucket=bucket, Body=frame, Key=image_name, ContentType="image/jpeg")
                    print("Image Uploaded Successfully!updated")
                    
                    url = "https://" + str(bucket) + ".s3.amazonaws.com/" + image_name
                    print("URL of the image uploaded (updated)", url)
                    break
        
        if stream_processed:
            return url, image_name
        else:
            return None, None

def get_face_id_from_photo(photo_name):
    
    client=boto3.client('rekognition')
    collection_id='faceCollection'
    bucket = 'assignment2-fall2020-faces'
    
    response=client.index_faces(CollectionId=collection_id,
                                Image={'S3Object':{'Bucket':bucket,'Name':photo_name}},
                                ExternalImageId=photo_name,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])
    # print ('Results for ' + photo) 
    # print('Faces indexed:')
    #print(response)
    face_ids = []
    for faceRecord in response['FaceRecords']:
      face_ids.append(faceRecord['Face']['FaceId'])

    if len(face_ids) >= 1:
        return face_ids[0]
    else:
        return None

def is_timer_valid(faceid, ttltimer=30):
    dynamodb = boto3.client('dynamodb')
    # table for checking whether to execute LF1
    dup_table = boto3.resource('dynamodb').Table('hw2-LF1-check-duplicate') 
  
  
    # check if there is a face ID in event
    # if no face ID, assign as UNKNOWN
    #faceid = matchedfaces[0]['Face']['FaceId'] if len(matchedfaces) else 'UNKNOWN'

    # early exit
    # check if faceid/UNKNOWN is seen in last ttltimer seconds
    seenItem = dynamodb.get_item(
        TableName='hw2-LF1-check-duplicate',
        Key={
            'face_id': {
            'S': faceid
        },
      }
    )
    current_time = int(time.time())
    if 'Item' not in seenItem:
        print(f"ADD {faceid} to DYNAMODB")
        print('################', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        dup_table.put_item(Item = {'face_id': faceid, 'TTL': str(current_time)})
        return True
    
    if 'Item' in seenItem and current_time - int(seenItem['Item']['TTL']['S']) > ttltimer : 
        print(f"ADD {faceid} to DYNAMODB")
        print('################', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        dup_table.put_item(Item = {'face_id': faceid, 'TTL': str(current_time)})
        return True
  
    print('###EVENT SKIPPING EXECUTION DUE TO ID SEEN IN LAST ', ttltimer, ' SECONDS')
    return False

def lambda_handler(event, context):
    # TODO implement
    payload = base64.b64decode(event['Records'][0]["kinesis"]["data"])
    face_search_response = json.loads(payload.decode('UTF-8')).get('FaceSearchResponse')
    print("#"*80, payload)
    
    #print ('The given face doesn\'t match any response.(updated)', face_search_response)
    
    if not face_search_response: 
        return
    matchedfaces = face_search_response[0]["MatchedFaces"]
    faceId = matchedfaces[0]['Face']['FaceId'] if len(matchedfaces) else 'UNKNOWN'
    if faceId == "UNKNOWN":
        if not is_timer_valid(faceId, 30):
            print("Timer Not Valid (Unknown): ", faceId)
            return
        input_information = json.loads(payload.decode('UTF-8')).get('InputInformation')
        kinesis_video = input_information.get('KinesisVideo')
        fragment_number = kinesis_video.get('FragmentNumber')
        print("fragment_number:", fragment_number,"updated")
        photo_link, photo_name = get_visitor_photo(str(fragment_number))
        print("#"*80, "photo_link: ", photo_link)
        print("#"*80, "photo_name: ", photo_name)
        if photo_link is not None and photo_name is not None:
            face_id = get_face_id_from_photo(photo_name)
            print("face id extracted updated", face_id)
            print("photo link extracted updated", photo_link)
        print("face_search_response updated:", face_search_response)
        print('END TIME', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
        return

    if not is_timer_valid(faceId, 300):
        print("Timer Not Valid (Known): ", faceId)
        return    
    info = {}
    info['faceId'] = faceId
    info['objectKey'] = matchedfaces[0]['Face']['ExternalImageId']
    dynamodb = boto3.client('dynamodb') 
    sns = boto3.client('sns')
    visitor = query_danymoDB_DB2(dynamodb, faceId)
    print(visitor)
    if 'Item' not in visitor:
        # WP2
        print("Process new visitor and send SNS to owner")
        sns_response = send_sns_to_owner(sns, info)
        return
    print("Process old visitor and send OTP to visitor")
    new_OPT = make_and_store_opt(4)
    sns_response = send_opt_sns(sns, new_OPT, visitor)
    print(sns_response)
    print('END TIME', datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))  
    return     





# def lambda_handler(event, context):
#   # create_dynamoDB_DB2()
#   # store_visitors()
#   # code = str(random_with_N_digits(4))
#   # put_passcode_dynamoDB(code)
#   # print(event)
#   print("event",event)
#   dynamodb = boto3.client('dynamodb')
#   # table for checking whether to execute LF1
#   dup_table = boto3.resource('dynamodb').Table(TABLE_DUP_CHECK) 
#   matchedfaces = event['MatchedFaces']
        
#   # early exit 1
#   # check if lambda was invoked in the last 30 seconds
#   current_time = int(time.time())
#   lastInvoke = dynamodb.get_item(
#       TableName=TABLE_DUP_CHECK,
#       Key={
#           'face_id': {
#               'S': 'LASTINVOKE'
#           },
#       }
#   )
#   # if LF1 triggered in the last 5 seconds, ignore triggerkeys
#   if 'Item' in lastInvoke and current_time <= float(lastInvoke['Item']['TTL']['S']):
#       print('###EVENT\nSKIPPING EXECUTION DUE TO LAST EVENT WAS < 5 SECONDS AGO')
#       return '###EVENT\nSKIPPING EXECUTION DUE TO LAST EVENT WAS < 5 SECONDS AGO'
#   # if triggering LF1, reset lastinvoked timer
#   else: 
#       expireTime = current_time + 5
#       item = {
#           'face_id': 'LASTINVOKE',
#           'TTL': str(expireTime)
#       }
#       dup_table.put_item(Item = item)
        
#   # # TEST
#   # item = {
#   #   'face_id': 'TEST_EVENT',
#   #   'TTL': json.dumps(event)
#   # }
#   # dup_table.put_item(Item = item)    
#   # return
    
#   # check if there is a face ID in event
#   if len(matchedfaces):
#       print(matchedfaces)
#       faceid = matchedfaces[0]['Face']['FaceId']
        
#       # early exit 2
#       # check if faceid is seen in last 30 seconds
#       seenItem = dynamodb.get_item(
#           TableName=TABLE_DUP_CHECK,
#           Key={
#               'face_id': {
#                   'S': faceid
#               },
#           }
#       )
#       if 'Item' in seenItem and current_time <= float(seenItem['Item']['TTL']['S']): 
#           print('###EVENT\nSKIPPING EXECUTION DUE TO ID SEEN IN LAST 30 SECONDS')
#           return '###EVENT\nSKIPPING EXECUTION DUE TO ID SEEN IN LAST 30 SECONDS'
#       else: 
#           expireTime = current_time + 30
#           item = {
#               'face_id': faceid,
#               'TTL': str(expireTime)
#           }
#           dup_table.put_item(Item = item)
    
#   # no face ID in event
#   else:
#       return
#   return
#   # TODO: handle if no face_id is in event (new face), need to access image and add image to S3
#   # TODO: create image snippet from video stream
#   #
#   # if no faceid, insert image to collection, check back in 5 seconds
#   expireTime = current_time + 5
#   item = {
#       'face_id': 'LASTINVOKE',
#       'TTL': str(expireTime)
#   }
#   dup_table.put_item(Item = item)
