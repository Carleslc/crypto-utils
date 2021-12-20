import math

def try_float(f: str) -> float:
  try:
    if ',' in f:
      f = f.replace(',', '.')
    return float(f)
  except ValueError:
    return math.nan

def is_nan(f: float) -> bool:
  return math.isnan(f)
