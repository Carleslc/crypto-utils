from datetime import datetime

def datetime_from_ms(ms: int) -> datetime:
  return datetime.fromtimestamp(ms/1000)

def datetime_from_timestamp(timestamp: int) -> datetime:
  return datetime.fromtimestamp(timestamp)
