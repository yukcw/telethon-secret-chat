from ..secret_methods import SecretChat
from .memory import SecretMemorySession
import base64
import boto3
import traceback
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import Binary
from telethon.tl.types import InputEncryptedChat

class SecretDynamoDBSession(SecretMemorySession):

    def __init__(self, region_name: str, access_key_id: str, secret_access_key: str, table_name: str, dynamodb: boto3.resource = None):
        super().__init__()
        self._region_name = region_name
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._dynamodb = dynamodb or boto3.resource(
            'dynamodb',
            region_name=self._region_name,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key
        )
        self._table = self._dynamodb.Table(table_name)

    def close(self):
        pass

    def save(self):
        pass

    def list_chats(self, temp=False):
        response = self._table.scan(
            FilterExpression=Attr('temp').eq(1 if temp else 0)
        )
        items = response.get('Items')
        chats = []
        for item in items:
            input_chat = InputEncryptedChat(chat_id=int(item['id']), access_hash=int(item['access_hash']))
            #   Convert the Decimal type of DynamoDB to int
            #   For auth_key, if it is of type Binary in DynamoDB, directly cast by bytes()
            #   If it is of type String, decode it from base64 to bytes
            if isinstance(item['auth_key'], Binary):
                auth_key = bytes(item['auth_key'])
            else:
                auth_key = base64.b64decode(item['auth_key'].encode('utf-8'))
            chats.append(SecretChat(
                input_chat=input_chat,
                session=self,
                id=int(item['id']),
                access_hash=int(item['access_hash']),
                auth_key=auth_key,
                admin=bool(item['admin']),
                user_id=int(item['user_id']),
                in_seq_no_x=int(item['in_seq_no_x']),
                out_seq_no_x=int(item['out_seq_no_x']),
                in_seq_no=int(item['in_seq_no']),
                out_seq_no=int(item['out_seq_no']),
                layer=int(item['layer']),
                ttl=int(item['ttl']),
                ttr=int(item['ttr']),
                updated=int(item['updated']),
                created=int(item['created']),
                mtproto=int(item['mtproto']),
                rekeying=(int(item['rekeying']), int(item.get('rekeying_exchange_id', 0))),
                is_temp=bool(item['temp'])
            ))
        return chats

    def delete(self):
        pass

    def save_chat(self, chat: SecretChat, temp=False):
        self._table.put_item(
            Item={
                'id': chat.id,
                'access_hash': chat.access_hash,
                'auth_key': chat.auth_key,
                'admin': 1 if chat.admin else 0,
                'user_id': chat.user_id,
                'in_seq_no_x': chat.in_seq_no_x,
                'out_seq_no_x': chat.out_seq_no_x,
                'in_seq_no': chat.in_seq_no,
                'out_seq_no': chat.out_seq_no,
                'layer': chat.layer,
                'ttl': chat.ttl,
                'ttr': chat.ttr,
                'updated': int(chat.updated),
                'created': int(chat.created),
                'mtproto': chat.mtproto,
                'temp': 1 if temp else 0,
                'rekeying': chat.rekeying[0],
                'rekeying_exchange_id': chat.rekeying[1] if len(chat.rekeying) > 1 else 0
            }
        )

    def get_temp_secret_chat_by_id(self, id) -> SecretChat:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(id),
            FilterExpression=Attr('temp').eq(1),
        )
        items = response.get('Items')
        if len(items) == 0:
            return None
        item = items[0]
        input_chat = InputEncryptedChat(chat_id=int(item['id']), access_hash=int(item['access_hash']))
        #   For auth_key, if it is of type Binary in DynamoDB, directly cast by bytes()
        #   If it is of type String, decode it from base64 to bytes
        if isinstance(item['auth_key'], Binary):
            auth_key = bytes(item['auth_key'])
        else:
            auth_key = base64.b64decode(item['auth_key'].encode('utf-8'))
        return SecretChat(
            input_chat=input_chat,
            session=self,
            id=int(item['id']),
            access_hash=int(item['access_hash']),
            auth_key=auth_key,
            admin=bool(item['admin']),
            user_id=int(item['user_id']),
            in_seq_no_x=int(item['in_seq_no_x']),
            out_seq_no_x=int(item['out_seq_no_x']),
            in_seq_no=int(item['in_seq_no']),
            out_seq_no=int(item['out_seq_no']),
            layer=int(item['layer']),
            ttl=int(item['ttl']),
            ttr=int(item['ttr']),
            updated=int(item['updated']),
            created=int(item['created']),
            mtproto=int(item['mtproto']),
            rekeying=(int(item['rekeying']), int(item['rekeying_exchange_id'])),
            is_temp=bool(item['temp'])
        )

    def get_secret_chat_by_id(self, id) -> SecretChat:
        response = self._table.query(
            KeyConditionExpression=Key('id').eq(id),
            FilterExpression=Attr('temp').eq(0),
        )
        items = response.get('Items')
        if len(items) == 0:
            return None
        item = items[0]
        input_chat = InputEncryptedChat(chat_id=int(item['id']), access_hash=int(item['access_hash']))
        #   For auth_key, if it is of type Binary in DynamoDB, directly cast by bytes()
        #   If it is of type String, decode it from base64 to bytes
        if isinstance(item['auth_key'], Binary):
            auth_key = bytes(item['auth_key'])
        else:
            auth_key = base64.b64decode(item['auth_key'].encode('utf-8'))
        return SecretChat(
            input_chat=input_chat,
            session=self,
            id=int(item['id']),
            access_hash=int(item['access_hash']),
            auth_key=auth_key,
            admin=bool(item['admin']),
            user_id=int(item['user_id']),
            in_seq_no_x=int(item['in_seq_no_x']),
            out_seq_no_x=int(item['out_seq_no_x']),
            in_seq_no=int(item['in_seq_no']),
            out_seq_no=int(item['out_seq_no']),
            layer=int(item['layer']),
            ttl=int(item['ttl']),
            ttr=int(item['ttr']),
            updated=int(item['updated']),
            created=int(item['created']),
            mtproto=int(item['mtproto']),
            rekeying=(int(item['rekeying']), int(item['rekeying_exchange_id'])),
            is_temp=bool(item['temp'])
        )

    def remove_secret_chat_by_id(self, id, temp=False) -> None:
        item = None
        if temp:
            item = self.get_temp_secret_chat_by_id(id)
        else:
            item = self.get_secret_chat_by_id(id)
        self._table.delete_item(
            Key={
                'id': item.id,
                'access_hash': item.access_hash
            }
        )
