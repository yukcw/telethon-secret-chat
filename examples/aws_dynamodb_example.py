from dotenv import load_dotenv
import os
import base64
import boto3
import time
import mimetypes
import asyncio
from datetime import datetime, timedelta

from boto3.dynamodb.conditions import Key, Attr
from telethon import TelegramClient
from telethon.sessions.sqlite import SQLiteSession
from telethon_secret_chat import SecretChatManager
from telethon_secret_chat.secret_chat_manager import SecretChatManager
from telethon_secret_chat.secret_sechma.secretTL import DecryptedMessageMediaPhoto, DecryptedMessageMediaDocument
from telethon_secret_chat.storage.sqlite import SecretSQLiteSession
from telethon_secret_chat.storage.dynamodb import SecretDynamoDBSession

#  Read from examples/.env
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))
#   App API ID and Hash
print("Script started, creating client...")
TELEGRAM_APP_API_ID=os.getenv('TELEGRAM_APP_API_ID')
TELEGRAM_APP_API_HASH=os.getenv('TELEGRAM_APP_API_HASH')

AWS_REGION="ap-east-1"
#  AWS Credentials
AWS_ACCESS_KEY_ID=os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY=os.getenv('AWS_SECRET_ACCESS_KEY')

#   Config
os.chdir("/tmp")
api_id = TELEGRAM_APP_API_ID
api_hash = TELEGRAM_APP_API_HASH

s3 = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
s3_bucket_name_for_session_file = os.getenv('S3_BUCKET_NAME')
dynamodb = boto3.resource(
    'dynamodb',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
chat_history_table = dynamodb.Table('TelegramSecretChatHistory')

#   Session file
session_file_path = os.path.join(os.getcwd(), 'telegram_client.session')
if not os.path.exists(session_file_path):
    file_name = os.path.basename(session_file_path)
    #   Download the session file from S3 bucket if it exists in the bucket
    try:
        s3.head_object(Bucket=s3_bucket_name_for_session_file, Key=file_name)
        s3.download_file(s3_bucket_name_for_session_file, file_name, session_file_path)
    except Exception as e:
        print(f"Session file {session_file_path} does not exist in S3 bucket.")

client = TelegramClient(session='telegram_client', api_id=api_id, api_hash=api_hash)

#   Phone numbers
from_phone = os.getenv('FROM_PHONE_NUMBER')
to_phone = os.getenv('TO_PHONE_NUMBER')  # target's username or phone number

"""
Helper Functions
"""
def get_auth_code():
    print('Wait for auth code')
    time.sleep(10)
    dynamodb_table = dynamodb.Table('TelegramAuthCode')
    response = dynamodb_table.query(
        KeyConditionExpression=Key('phone').eq(from_phone) & Key('created').gt(int((datetime.now() - timedelta(minutes=1)).timestamp())),
    )
    code = response.get('Items')[0]['code'] if response.get('Items') else None
    if code is None:
        # Sleep for 10 seconds and try again
        print('No code found, sleep for 10 seconds and try again')
        time.sleep(10)
        return get_auth_code()
    return code

async def save_chat_history(event):
    print('========== save_chat_history(event) ===========')
    print(type(event))
    print(event)
    if event.decrypted_event:
        print('=== event.decrypted_event ===')
        print(event.decrypted_event)
        # If event.decrypted_event has attribute "message"
        if hasattr(event.decrypted_event, 'message'):
            # Convert datetime to Number
            print('Save chat history to DynamoDB')
            file = bytes()
            if hasattr(event.decrypted_event, 'media') and event.decrypted_event.media is not None:
                print('Download', type(event.decrypted_event.media))
                file = await manager.download_secret_media(message=event.decrypted_event, file=event.message.file)
                # Get the file extension
                extension = ''
                if hasattr(event.decrypted_event.media, 'mime_type'):
                    extension = mimetypes.guess_extension(event.decrypted_event.media.mime_type)
                elif isinstance(event.decrypted_event.media, DecryptedMessageMediaPhoto):
                    extension = '.jpg'
                else:
                    print('Unknown media type')
                    extension = '.bin'
                # Save the file to local storage
                with open(f'{datetime.now().strftime("%Y%m%d%H%M%S")}{extension}', 'wb') as f:
                    f.write(file)
                
            entities = []
            # Convert the TypeMessageEntity classes to a dictionary
            # Example: class=MessageEntityBold, offset=0, length=4
            # entities = {'class': MessageEntityBold, 'offset':0, 'length':4}
            if hasattr(event.decrypted_event, 'entities') and event.decrypted_event.entities is not None:
                for entity in event.decrypted_event.entities:
                    entities.append({
                        'class': type(entity).__name__,
                        'offset': entity.offset,
                        'length': entity.length
                    })
            chat_history_table.put_item(
                Item={
                    'chat_id': event.message.chat_id,
                    'date': int(event.message.date.timestamp()),
                    'message': event.decrypted_event.message,
                    # Base64 encode the file
                    'file': base64.b64encode(file).decode('utf-8') if file and len(file) < 300000 else None,
                    'file_extension': extension if file else None,
                    'random_id': event.decrypted_event.random_id,
                    'ttl': event.decrypted_event.ttl,
                    'entities': entities,
                    'via_bot_name': event.decrypted_event.via_bot_name,
                    'reply_to_random_id': event.decrypted_event.reply_to_random_id,
                    'grouped_id': event.decrypted_event.grouped_id,
                }
            )


async def replier(event):
    # all events are encrypted by default
    print('========== replier(event) ===========')
    print(type(event))
    print(event)
    if event.decrypted_event.message:
        print(event.decrypted_event)
        print('=== reply() ===')
        await event.mark_read(event.decrypted_event.message)
        await event.reply(f"**Received**") # parse_mode is markdown by default
        await event.reply(f"{event.decrypted_event.message}") # parse_mode is markdown by default

async def new_chat(chat, created_by_me):
    if created_by_me:
        print("User {} has accepted our secret chat request".format(chat))
    else:
        print("We have accepted the secret chat request of {}".format(chat))

async def save_session_file(delay=25):
    print('Sleep until save_session_file') 
    await asyncio.sleep(delay)  # await tells the loop this task is "busy"
    print('save_session_file') 
    file_name = os.path.basename(session_file_path)
    s3.upload_file(session_file_path, s3_bucket_name_for_session_file, file_name)

async def main(start_new_chat=False, manager=None):
    #   Get the recipient user
    recipient_user = await client.get_input_entity(to_phone)
    print(f"Recipient user: {recipient_user}")
    if start_new_chat:
        secret_chat = await manager.start_secret_chat(peer=recipient_user)
        print(f"Secret chat started {secret_chat}")
    else:
        chats = manager.session.list_chats()
        for chat in chats:
            try:
                await manager.notify_layer(chat)
                await manager.send_secret_message(chat.id, "Hello from the secret chat!", ttl=0, reply_to_id=None)
            except Exception as e:
                print(f"Error notifying layer: {e}")
                # manager.session.remove_secret_chat_by_id(chat.id)
                continue
  
"""
Entrypoint Handler
"""
def lambda_handler(event, context):
  client.start(phone=from_phone, code_callback=get_auth_code)

  # sqlite_connection = sqlite3.connect('secret_chat.db')
  # sqlite_session = SecretSQLiteSession(sqlite_connection)
  # manager = SecretChatManager(client, auto_accept=True, session=sqlite_session,
  #                             new_chat_created=new_chat)  # automatically accept new secret chats
  dynamo_db_session = SecretDynamoDBSession(
      region_name=AWS_REGION,
      access_key_id=AWS_ACCESS_KEY_ID,
      secret_access_key=AWS_SECRET_ACCESS_KEY,
      table_name='TelegramSecretChats'
  )
  manager = SecretChatManager(client, auto_accept=True, session=dynamo_db_session,
                              new_chat_created=new_chat)  # automatically accept new secret chats
  manager.add_secret_event_handler(func=replier)  # we can specify the type of the event
  manager.add_secret_event_handler(func=save_chat_history)  # we can specify the type of the event

  with client:
      # Check if event (JSON) has key "phone" and "message"
        if event and 'phone' in event and 'message' in event:
            #   Start a new secret chat
            client.loop.run_until_complete(main(start_new_chat=True, manager=manager))
        else:
            #   Continue the existing secret chat
            print('Continue the existing secret chat')
        client.loop.run_until_complete(main(start_new_chat=False, manager=manager))
        client.loop.create_task(save_session_file())
        client.run_until_disconnected()

if __name__ == "__main__":
    lambda_handler(None, None)