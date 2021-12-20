import json

def pretty(o: any) -> str:
  return json.dumps(o, indent=2, default=str)
