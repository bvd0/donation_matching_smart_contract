# SPDX-License-Identifier: AGPL-3.0-only
# (c) 2025

from web3 import Web3


def main():
	w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
	w3.eth.default_account = w3.eth.accounts[0]

	abi = input()
	bytecode = input()

	print(
		abi,
		w3.eth.wait_for_transaction_receipt(
			w3.eth.contract(abi=abi, bytecode=bytecode).constructor().transact()
		).contractAddress,
		sep='\n',
	)


if __name__ == '__main__':
	main()
