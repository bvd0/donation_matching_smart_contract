# SPDX-License-Identifier: AGPL-3.0-only
# (c) 2025

import argparse
import datetime
import pprint

import web3
from web3 import Web3


def datetime_to_iso(dt):
	return dt.isoformat(sep='_', timespec='seconds').replace('+00:00', 'Z')


def get_y_or_n_from_input(msg):
	while True:
		match t1 := input(msg + ' (y/n): ').strip():
			case 'n':
				return False
			case 'y':
				return True
			case _:
				print(f'Error: {t1!r} is not recognized.')


def get_wei_amount_from_eth_input(msg, is_0_ok):
	while True:
		try:
			eth_amount = Web3.to_wei(t1 := input(msg), 'ether')
		except Exception as e:
			print(f'Error: {e!r} (input was {t1!r})')
		else:
			if 0 < eth_amount or is_0_ok and eth_amount == 0:
				return eth_amount
			else:
				print(f'Error: The amount {eth_amount} needs to be greater than 0.')


def print_matchers(matchers):
	print(f'index | {'donation address':^42} |{'match amount':^14}|{'ETH available':^{4+1+18+5}}| {'deadline (UTC)':^20} | withdrawable')
	for i, m in matchers:
		funds, matcher_addr, donate_addr, match_mul, deadline, withdrawable_before_deadline = m
		match_amount = match_mul / 2**10
		deadline = datetime.datetime.fromtimestamp(deadline, datetime.UTC)

		print(f'{i:>5} | {donate_addr} |{match_amount: 13.10f} |{Web3.from_wei(funds, 'ether'): 23.18f} ETH | {datetime_to_iso(deadline)} | {withdrawable_before_deadline}')


def call_contract(w3, contract_fn, deposit_amount):
	print('Sending request to contract...')
	try:
		transaction_receipt = w3.eth.wait_for_transaction_receipt(contract_fn.transact({'value': deposit_amount}))
	except web3.exceptions.Web3Exception as e:
		print(f'Error: {e}')
	else:
		print('Completed successfully.')
		print('\nTransaction receipt:')
		pprint.pp(dict(transaction_receipt))


def main():
	parser0 = argparse.ArgumentParser(allow_abbrev=False, description='')

	parser0.add_argument('--deploy-input', metavar='PATH', help='Read abi and then contract_address (separated by a newline) from the file at %(metavar)s.')
	parser0.add_argument('--abi', help='(Overwrites abi in --deploy-input.)')
	parser0.add_argument('--contract-address', metavar='HEX', help='(Overwrites contract_address in --deploy-input.)')
	parser0.add_argument('--host', default='localhost', metavar='ADDRESS', help='The host to connect to. Default: %(default)s')
	parser0.add_argument('--port', type=int, default=8545, metavar='NUMBER', help='The port number to use. Default: %(default)s')
	parser0.add_argument('--account-index', type=int, default=0, metavar='NUMBER', help='The index of the account to use. Default: %(default)s')

	args0 = parser0.parse_args()

	w3 = Web3(Web3.HTTPProvider(f'http://{args0.host}:{args0.port}'))
	w3.eth.default_account = w3.eth.accounts[args0.account_index]
	if args0.deploy_input is not None:
		with open(args0.deploy_input, 'r') as f:
			if args0.abi is None:
				args0.abi = f.readline().strip()
			else:
				f.readline()
			if args0.contract_address is None:
				args0.contract_address = f.readline().strip()
	contract = w3.eth.contract(abi=args0.abi, address=args0.contract_address)


	while True:
		print(
			'\n'
			' ~~~~ Main Menu ~~~~ \n'
			'\n'
			'[d]: donate\n'
			'[m]: deposit matching funds\n'
			'[w]: withdraw matching funds\n'
			'[l]: list all matchers\n'
			'[q]: quit\n'
			'\n'
		)
		match mode := input('Want do you want to do?: ').strip():
			case 'd':
				matchers = contract.functions.get_matchers().call()
				print_matchers(enumerate(matchers))

				while True:
					try:
						index = int(t1 := input('Select an index (or q to cancel): ').strip())
						funds, matcher_addr, donate_addr, match_mul, deadline, withdrawable_before_deadline = matchers[index]
					except (ValueError, IndexError) as e:
						if t1 == 'q':
							break
						print(f'Error: {e!r}')
					else:
						if deadline < datetime.datetime.now(datetime.UTC).timestamp():
							print(f'Error: The deadline has passed for {index=}.')
						elif funds == 0:
							print(f'Error: There are no funds left for {index=}.')
						else:
							break
				if t1 == 'q':
					continue

				print(f'The maximum amount of the donation that can be matched is {Web3.from_wei(funds / (match_mul / 2**10), 'ether')}.')

				donate_amount = get_wei_amount_from_eth_input('Amount to donate in ETH: ', False)
				allowed_slippage = get_wei_amount_from_eth_input('Allowed slippage in ETH (How much ETH is allowed to be unmatched?): ', True)

				print(
					'\n'
					'Is this correct?\n'
					f'Index:\t{index}\n'
					f'Donation address:\t{donate_addr}\n'
					f'Matcher\'s address:\t{matcher_addr}\n'
					f'Donation amount:\t{Web3.from_wei(donate_amount, 'ether')} ETH\n'
					f'Matched amount: \t{Web3.from_wei(t1 := donate_amount * match_mul / 2**10, 'ether')} ETH\n'
					f'Total donation: \t{Web3.from_wei(donate_amount + t1, 'ether')} ETH\n'
					f'Allowed slippage:\t{Web3.from_wei(allowed_slippage, 'ether')} ETH\n'
					f'Matched amount with max slippage:\t{Web3.from_wei(t2 := max(0, t1 - allowed_slippage), 'ether')} ETH\n'
					f'Total donation with max slippage:\t{Web3.from_wei(donate_amount + t2, 'ether')} ETH\n'
					'\n'
				)

				if get_y_or_n_from_input('y: confirm, n: cancel '):
					call_contract(w3, contract.functions.donate(index, allowed_slippage), donate_amount)
				else:
					print('Canceled.')

			case 'm':
				print('Leave blank to select the default.')
				while True:
					donate_address = input('donate address: ').strip()
					if Web3.is_checksum_address(donate_address):
						break
					else:
						if Web3.is_address(donate_address):
							print(f'Error: {donate_address!r} address checksum (EIP-55) is invalid.')
						else:
							print(f'Error: {donate_address!r} is not a valid address.')

				while True:
					try:
						match_mul_float = float(input('Match amount (0 < match_amount < 64) (default: 1): ').strip() or 1.0) * 2**10
					except ValueError as e:
						print(f'Error: {e!r}')
					else:
						match_mul = int(match_mul_float)
						if not match_mul_float.is_integer():
							print(f'(Note: The match amount is changed to {match_mul / 2**10} because it has to be a multiple of 1/1024.)')
						if 0x0 < match_mul < 0x10000:
							break
						else:
							print(f'Error: The match amount {match_mul / 2**10} is out of range.')

				while True:
					try:
						t1 = input('Deadline (up to 367 days from now) in ISO 8601 format, or in number of days from now by prepending \'+\' (default: now + 30 days): ').strip()
						if t1 == '':
							deadline = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
						elif t1[0] == '+':
							deadline = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=float(t1))
						else:
							deadline = datetime.datetime.fromisoformat(t1)
					except ValueError as e:
						print(f'Error: {e!r}')
					else:
						if 0 < deadline.timestamp() < datetime.datetime.now(datetime.UTC).timestamp() + 60 * 60 * 24 * 367:
							break
						else:
							print(f'Error: The deadline {datetime_to_iso(deadline)} is out of range.')

				withdrawable_before_deadline = get_y_or_n_from_input('Should the funds be withdrawable before the deadline?')

				deposit_amount = get_wei_amount_from_eth_input('Amount to deposit in ETH: ', False)

				print(
					'\n'
					'Is this correct?\n'
					f'Donation address:\t{donate_address}\n'
					f'Match amount:\t{match_mul / 2**10}\n'
					f'Deadline:\t{datetime_to_iso(deadline)}\n'
					f'Funds are withdrawable before deadline:\t{withdrawable_before_deadline}\n'
					f'Deposit amount:\t{Web3.from_wei(deposit_amount, 'ether')} ETH\n'
					'\n'
				)

				if get_y_or_n_from_input('y: confirm, n: cancel '):
					call_contract(w3, contract.functions.deposit_matching_funds(
						donate_address, match_mul, int(deadline.timestamp()), withdrawable_before_deadline
					), deposit_amount)
				else:
					print('Canceled.')

			case 'w':
				print_matchers(
					tuple((i, o)
					for i, o in enumerate(contract.functions.get_matchers().call())
					if 0 < o[0] and o[1] == w3.eth.default_account)
				)

				while True:
					try:
						index = int(t1 := input('Select an index (or q to cancel): ').strip())
						break
					except ValueError as e:
						if t1 == 'q':
							break
						print(f'Error: {e!r}')
				if t1 == 'q':
					continue

				if get_y_or_n_from_input(f'Withdraw index {index}?'):
					call_contract(w3, contract.functions.withdraw_matching_funds(index), 0)
				else:
					print('Canceled.')

			case 'l':
				print_matchers(enumerate(contract.functions.get_matchers().call()))

			case 'q':
				print('exiting...')
				return

			case _:
				print(f'{mode=!r} is not recognized.')


if __name__ == '__main__':
	main()
