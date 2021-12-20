#!/usr/bin/python3
# -*- coding: utf-8 -*-

from crypto.api.bsc import BinanceSmartChain, bsc_client

import argparse

def set_args():
  global args
  parser = argparse.ArgumentParser()
  parser.description = "Get information about a BSC address."
  parser.add_argument("address", help="contract address")
  parser.add_argument("--input", help="decode some input")
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
    print('\nDecoded Input:', address.decode_input(input))
  except ValueError as e:
    print('\nCannot decode Input:', e)

def main():
  set_args()

  try:
    with bsc_client(args.address) as address:
      print_info_address(address)
      
      if args.input:
        print_decoded_input(address, args.input)
  except ValueError as e:
    print(f'Error: {e}')

if __name__ == "__main__":
  main()
