import boto3
import os
from dotenv import load_dotenv

load_dotenv()

sns_client = boto3.client(
    'sns',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='eu-central-1'
)

def send_test_sms(phone_number, message):
    response = sns_client.publish(
        PhoneNumber=phone_number,
        Message=message,
        MessageAttributes={
            'AWS.SNS.SMS.SenderID': {
                'DataType': 'String',
                'StringValue': 'TestApp'
            },
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }
        }
    )
    return response

if __name__ == "__main__":
    response = send_test_sms('+919039469979', 'Hello, this is a test SMS from AWS SNS!')
    print(response)
