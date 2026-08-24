from telegram_client import client


def parse_telegram_link(link):
    parts = link.rstrip("/").split("/")

    if len(parts) < 2:
        raise ValueError("Invalid Telegram link")

    message_id = int(parts[-1])
    username = parts[-2]

    return username, message_id


async def main():
    print("Telegram client started!")

    link = input("Telegram message link: ")

    try:
        username, message_id = parse_telegram_link(link)

        entity = await client.get_entity(username)
        message = await client.get_messages(entity, ids=message_id)

        if not message:
            print("Message not found.")
            return

        if not message.media:
            print("This message has no downloadable media.")
            return

        print("Downloading...")

        path = await message.download_media("downloads")

        print(f"Downloaded successfully:")
        print(path)

    except Exception as e:
        print(f"Error: {e}")


with client:
    client.loop.run_until_complete(main())
