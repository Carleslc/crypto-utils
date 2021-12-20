from typing import Any, Callable, Union, Iterable

import os

from time import sleep
from decimal import Decimal

from dotenv import load_dotenv

from bscscan import BscScan

from web3.types import ABI
from web3.contract import Contract, ContractFunction, ContractFunctions
from web3.exceptions import ContractLogicError
from eth_typing.evm import ChecksumAddress
from eth_typing.encoding import HexStr

from crypto.utils.web3 import web3_http, from_wei, is_empty, is_zero_address, hexbytes_to_address, function_signature, function_info, get_abi_output_names, decode_data
from crypto.utils.error import error

# BSCScan API
# https://docs.bscscan.com/
# https://docs.bscscan.com/support/rate-limits
# Limits: 5 calls/second, up to 100.000 calls/day
MAX_BSC_SCAN_API_CALLS_PER_SECOND = 5

def _ratelimit(max_calls_per_second: int = MAX_BSC_SCAN_API_CALLS_PER_SECOND):
  sleep(1/max_calls_per_second)

def ratelimit(f):
  def decorator(*args, **kwargs):
    _ratelimit()
    return f(*args, **kwargs)
  return decorator

class BinanceSmartChain:

  MAIN_NET = 'https://bsc-dataseed.binance.org'

  _IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'

  def __init__(self, api_key: str, address: str, debug=False):
    # https://web3py.readthedocs.io/en/stable/web3.main.html#web3-api
    self._web3 = web3_http(BinanceSmartChain.MAIN_NET)
    # https://bscscan-python.pankotsias.com/ 
    self._scan = BscScan(api_key, asynchronous=False, debug=debug)
    self._address = self._implementation = self.checksum(address)
    self._debug = debug
    self._contract = None
    self._info = None
    self.error = None
  
  @property
  def contract(self) -> Contract:
    return self._contract
  
  @property
  def address(self) -> ChecksumAddress:
    return self._address
  
  @property
  def abi(self) -> ABI:
    return self.get_contract_abi()
  
  @property
  def info(self):
    return self.get_contract_info()[0]
  
  @property
  def source(self) -> str:
    return self.info['SourceCode']
  
  @property
  def name(self) -> str:
    return self.info['ContractName']
  
  @property
  def is_proxy(self) -> bool:
    return self._is_proxy_address(self._address) or self.resolve_implementation()
  
  @property
  def is_contract(self) -> bool:
    return True if self._contract is not None else self._is_contract_address(self._address)
  
  @property
  def functions(self) -> ContractFunctions:
    return self.contract.functions if self.contract else None
  
  @ratelimit
  def get_bnb_balance(self) -> Decimal:
    return from_wei(self._scan.get_bnb_balance(self._address))

  def get_contract_abi(self) -> ABI:
    if self._contract:
      return self._contract.abi
    # https://docs.bscscan.com/api-endpoints/contracts#get-contract-abi-for-verified-contract-source-codes
    # https://api.bscscan.com/api?module=contract&action=getabi&address=ADDRESS&apikey=
    # https://bscscan-python.pankotsias.com/bscscan.modules.html#bscscan.modules.contracts.Contracts.get_contract_abi
    _ratelimit()
    return self._scan.get_contract_abi(self._address)
  
  def get_contract_info(self) -> list:
    if self._info is None:
      # https://docs.bscscan.com/api-endpoints/contracts#get-contract-source-code-for-verified-contract-source-codes
      # https://api.bscscan.com/api?module=contract&action=getsourcecode&address=ADDRESS&apikey=
      # https://bscscan-python.pankotsias.com/bscscan.modules.html#bscscan.modules.contracts.Contracts.get_contract_source_code
      _ratelimit()
      self._info = self._scan.get_contract_source_code(self._address)
    return self._info

  @ratelimit
  def get_contract_circulating_supply(self) -> float:
    return float(self._scan.get_circulating_supply_by_contract_address(self._address))
  
  def list_functions(self, with_names: bool = True) -> list[str]:
    if not self.contract:
      return None
    f_info = function_info if with_names else function_signature
    return [f_info(f) for f in self.contract.all_functions()]
  
  def _is_contract_address(self, address: str) -> bool:
    return not is_empty(self._web3.eth.get_code(address))

  def _is_proxy_address(self, address: str) -> bool:
    if address == self._address:
      info = self.get_contract_info()
    else:
      _ratelimit()
      info = self._scan.get_contract_source_code(address)
    return info[0]['Proxy'] != '0'
  
  def resolve_implementation(self) -> ChecksumAddress:
    if self.contract:
      try:
        implementation = self.contract.get_function_by_signature('implementation()')().call()
      except (ValueError, ContractLogicError):
        implementation = hexbytes_to_address(self._web3.eth.get_storage_at(self._address, BinanceSmartChain._IMPLEMENTATION_SLOT))
        if is_zero_address(implementation):
          implementation = None
      if implementation:
        self._implementation = self.checksum(implementation)
        return self._implementation
    return None

  def resolve_proxy(self, override: bool = False) -> bool:
    self.error = None
    if self.resolve_implementation():
      try:
        if override:
          self._address = self._implementation
          self._contract = None
          self._info = None
          self._set_contract()
        else:
          _ratelimit()
          self._contract = self._get_contract(self._address, self._scan.get_contract_abi(self._implementation))
          self._add_methods(self._contract)
        return True
      except AssertionError as e:
        self.error = e
    return False

  def resolve_proxies(self, override: bool = False) -> bool:
    success = True
    while success:
      success = self.resolve_proxy(override)
    return success
  
  def decode_input(self, input: str) -> tuple[ContractFunction, dict]:
    if not self.contract:
      error = f': {self.error}' if self.error else ''
      raise ValueError(f'Cannot get contract{error}')
    return self.contract.decode_function_input(input)
  
  def decode_output(self, data: HexStr, types: Iterable[str]) -> tuple[Any]:
    return decode_data(self._web3, data, types)
  
  def _set_contract(self):
    if self._contract is None and self.is_contract:
      self._contract = self._get_contract(self._address)
      self._add_methods(self._contract)

  def _get_contract(self, address: str, abi: ABI = None) -> Contract:
    if abi is None:
      _ratelimit()
      abi = self._scan.get_contract_abi(address)
    return self._web3.eth.contract(address=address, abi=abi)
  
  def _add_methods(self, contract: Contract):
    for f in contract.all_functions():
      key = str(f.function_identifier)
      if hasattr(self, key):
        key = f'f_{key}'
      setattr(self, key, self.wrap_call(f))
  
  def call(self, f: ContractFunction, *call_args, **call_kwargs) -> Union[tuple, dict, Any]:
    results = f.call(*call_args, **call_kwargs)
    if type(results) is not tuple:
      results = (results)
    output_names = get_abi_output_names(f.abi)
    if len(output_names) != len(results):
      return results
    return dict(zip(output_names, results))
  
  @ratelimit
  def proxy_call(self, data: str, to: str = None) -> str:
    return self._scan.get_proxy_call(to=to or self._address, data=data)

  def __contains__(self, f: str) -> bool:
    return f in self.functions if self.functions else False

  def __call__(self, f: Union[str, ContractFunction], *args, **kwargs) -> Any:
    f = self[f] if type(f) is str else self.wrap_call(f)
    return f(*args, **kwargs)
  
  def __getitem__(self, f: str) -> Callable:
    return getattr(self, f)

  def __enter__(self):
    self._scan.__enter__()
    self._set_contract()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self._scan.__exit__(exc_type, exc_val, exc_tb)
  
  def checksum(self, address: str) -> ChecksumAddress:
    return self._web3.toChecksumAddress(address)
  
  def wrap_call(self, f: ContractFunction, *call_args, **call_kwargs) -> Callable:
    def call(*args, **kwargs):
      f_bound = f(*args, **kwargs)
      if self._debug:
        print(f_bound.selector, f_bound)
      return f_bound.call(*call_args, **call_kwargs)
    call.__qualname__ = str(f.function_identifier)
    return call

BSC_CLIENT = None

def bsc_client(address: str, api_key: str = None, dotenv_path: str = None, debug: bool = False) -> BinanceSmartChain:
  global BSC_CLIENT

  if not BSC_CLIENT:
    print(f"Loading {BinanceSmartChain.__name__} API...")

    if api_key is None:
      load_dotenv(dotenv_path)

      api_key = os.getenv('BSCSCAN_API_KEY')

    if not api_key:
      error("Missing BSCSCAN_API_KEY (.env)")
    
    BSC_CLIENT = lambda address, debug: BinanceSmartChain(api_key, address, debug=debug)

  return BSC_CLIENT(address, debug)
