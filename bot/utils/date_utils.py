from datetime import datetime
def is_next_day(timestamp: int) -> bool:
    if len(str(timestamp)) > 10:
        timestamp = int(str(timestamp)[0:10])
    then = datetime.utcfromtimestamp(timestamp)
    now = datetime.utcnow()
    return now.date() > then.date() and now.time().hour > 10