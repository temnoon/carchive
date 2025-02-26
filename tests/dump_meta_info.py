# tests/dump_meta_info.py
from carchive.database.session import get_session
from carchive.database.models import Message

def dump_meta_info(limit=10):
    with get_session() as session:
        messages = session.query(Message).limit(limit).all()
        for msg in messages:
            print("Message ID:", msg.id)
            print("Content:", msg.content[:100] + "..." if msg.content else "None")
            print("Meta Info:", msg.meta_info)
            print("-" * 40)

if __name__ == "__main__":
    dump_meta_info(limit=50)
