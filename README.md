# Telethon Secret Chat

This is a secret chat plugin for Telethon.

## Installation

You can install the package from the built wheel (in `dist/`):

```bash
pip install dist/telethon_secret_chat-0.2.4-py3-none-any.whl
```

## Examples

You can find example scripts in the `examples/` directory.

### Basic Usage

Here is a simple example of how to use the secret chat manager.

```python
from telethon import TelegramClient, events
from telethon_secret_chat import SecretChatManager

api_id = 12345
api_hash = 'your_api_hash'

client = TelegramClient('anon', api_id, api_hash)

# Initialize the SecretChatManager
# auto_accept=True will automatically accept secret chat requests
manager = SecretChatManager(client, auto_accept=True)

async def main():
    await client.start()
    
    # You can start a secret chat
    # await manager.start_secret_chat(user_id)
    
    print("Client is running...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    with client:
        client.loop.run_until_complete(main())
```

## Features

- End-to-End Encryption
- Support for images, video, audio
- Auto-accept secret chats

## License

MIT
