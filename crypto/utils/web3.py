from typing import Any, Iterable, Union, cast

from web3 import Web3
from web3.contract import ContractFunction, ACCEPTABLE_EMPTY_STRINGS
from web3._utils.abi import abi_to_signature, get_abi_input_types, get_abi_input_names, get_abi_output_types, map_abi_data
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
from web3.types import ABIFunction
from eth_typing.evm import AnyAddress
from eth_typing.encoding import HexStr
from hexbytes.main import HexBytes

from bscscan.utils.conversions import Conversions

from decimal import Decimal

def web3_http(rpc_provider: str) -> Web3:
  return Web3(Web3.HTTPProvider(rpc_provider))

def from_wei(value: Union[str, int], decimals: int = 18) -> Decimal:
  return Conversions.to_ticker_unit(int(value), decimals)

def to_wei(value: Union[str, int], decimals: int = 18) -> Decimal:
  return Conversions.to_smallest_unit(int(value), decimals)

def to_int(value: Union[int, HexStr]) -> int:
  if isinstance(value, int):
    return value
  try:
    return Web3.toInt(hexstr=value)
  except ValueError:
    return None

def to_float(value: Union[int, HexStr]) -> int:
  try:
    return from_wei(to_int(value))
  except ValueError:
    return None

def to_bool(value: Union[int, HexStr]) -> int:
  try:
    return bool(to_int(value))
  except ValueError:
    return None

def to_text(value: HexStr) -> int:
  try:
    return Web3.toText(hexstr=value)
  except ValueError:
    return None

def to_json(value: dict) -> str:
  return Web3.toJSON(value)

def same_address(address1: AnyAddress, address2: AnyAddress) -> bool:
  return HexBytes(address1) == HexBytes(address2)

def is_zero_address(address: AnyAddress) -> bool:
  return to_int(address) == 0

def is_empty(data: str) -> bool:
  return data in ACCEPTABLE_EMPTY_STRINGS

def hexbytes_to_address(hexbytes: HexBytes) -> str:
  return HexBytes(hexbytes.hex()[-40:]).hex()

def iterable_types(types: str) -> tuple[str]:
  return types.lstrip('(').rstrip(')').split(',')

def get_abi_output_names(abi: ABIFunction) -> list[str]:
  if 'outputs' not in abi and abi['type'] == 'fallback':
    return []
  else:
    return [arg['name'] for arg in abi['outputs']]

def function_signature(f: ContractFunction) -> str:
  return abi_to_signature(f.abi) if f.abi else str(f.function_identifier)

def function_info(f: ContractFunction) -> str:
  def arg_str(arg) -> str:
    return f'{arg[0]}: {arg[1]}' if arg[0] else arg[1]
  def get_abi_inputs() -> list[str]:
    input_names = get_abi_input_names(f.abi)
    input_types = get_abi_input_types(f.abi)
    return list(map(arg_str, zip(input_names, input_types)))
  def get_abi_outputs() -> list[str]:
    output_names = get_abi_output_names(f.abi)
    output_types = get_abi_output_types(f.abi)
    return list(map(arg_str, zip(output_names, output_types)))
  abi_inputs = get_abi_inputs()
  abi_outputs = get_abi_outputs()
  fn_input_args = ', '.join(abi_inputs)
  fn_output_args = ', '.join(abi_outputs)
  if len(abi_outputs) > 1:
    fn_output_args = f'[{fn_output_args}]'
  if len(abi_outputs) > 0:
    fn_output_args = ' -> ' + fn_output_args
  return "{fn_name}({fn_input_args}){fn_output_args}".format(
      fn_name=f.abi['name'],
      fn_input_args=fn_input_args,
      fn_output_args=fn_output_args
    )

def decode_data(web3: Web3, data: HexStr, types: Iterable[str]) -> Union[Any, tuple[Any]]:
  data = HexBytes(data)
  decoded = web3.codec.decode_abi(types, cast(HexBytes, data))
  normalized = map_abi_data(BASE_RETURN_NORMALIZERS, types, decoded)
  return tuple(normalized)
