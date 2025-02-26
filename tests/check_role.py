from carchive.database.session import get_session
from carchive.database.models import Message

with get_session() as session:
    messages = session.query(Message).limit(5).all()
    for msg in messages:
        print(msg.id, msg.meta_info)
