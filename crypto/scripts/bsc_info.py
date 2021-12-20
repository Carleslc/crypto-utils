#!/usr/bin/python3
# -*- coding: utf-8 -*-

from crypto.api.bsc import BinanceSmartChain, bsc_client
from crypto.utils.web3 import function_signature, to_int, to_float, to_bool, to_text, iterable_types
from crypto.utils.error import error

import argparse

def set_args():
  global args
  parser = argparse.ArgumentParser()
  parser.description = "Get information about a BSC address."
  parser.add_argument("address", help="contract address")
  parser.add_argument("--input", help="decode some input")
  parser.add_argument("--data", help="make a proxy call with selector and arguments encoded as hex data e.g. 0xeb91d37e", type=str)
  parser.add_argument("--types", help="data output types for the proxy call, e.g. --types (uint256,bool,bytes,string,address[])", type=str)
  args = parser.parse_args()

def print_info_functions(contract: BinanceSmartChain, functions: list[str]):
  for function in functions:
    if function in contract:
      print(f'\n{contract(function)}')

def print_info_contract(contract: BinanceSmartChain):
  if contract.name:
    print(f'\n{contract.name}')

  print_info_functions(contract, ['description'])

  if contract.error:
    print(f'\n{contract.error}')
  
  def print_list_functions():
    functions = contract.list_functions()
    if functions:
      print('\n' + '\n'.join(functions))

  is_proxy = contract.is_proxy
  
  if is_proxy:
    print('\n[Proxy]')
    print_list_functions()
    print('\n[Implementation]')
    contract.resolve_proxy(override=True)
    print_info_address(contract)
  else:
    print_list_functions()

def print_info_address(address: BinanceSmartChain):
  if address.is_contract:
    print(f'\n[Contract] {address.address}')
  else:
    print(f'\n{address.address}')

  balance = address.get_bnb_balance()

  if balance.is_zero():
    balance = 0

  print(f'\nBalance: {balance} BNB')

  if address.is_contract:
    print_info_contract(address)

def print_decoded_input(address: BinanceSmartChain, input: str):
  try:
    decoded_function, decoded_args = address.decode_input(input)
    print('\nDecoded Input:\n')
    print(function_signature(decoded_function))
    print(decoded_args)
  except ValueError as e:
    print('\nCannot decode Input:', e)

def print_proxy_call(address: BinanceSmartChain, input_data: str, types: str = None):
  output_data = address.proxy_call(input_data)
  print(f'\nProxy Call ({input_data}):')
  print('hex', output_data)
  if types:
    original_types = iterable_types(types)
    types_tuple = iterable_types(types.replace('float', 'uint256'))
    decoded_output = address.decode_output(output_data, types_tuple)
    for original_type, value in zip(original_types, decoded_output):
      if original_type == 'float':
        value = to_float(value)
      print(original_type, value)
  else:
    print('int', to_int(output_data))
    print('float', to_float(output_data))
    print('bool', to_bool(output_data))
    print('text', to_text(output_data))

def main():
  set_args()

  try:
    with bsc_client(args.address) as address:
      if args.data:
        print_proxy_call(address, args.data, args.types)
      
      print_info_address(address)
      
      if args.input:
        print_decoded_input(address, args.input)
  except ValueError as e:
    error(e)

if __name__ == "__main__":
  main()
