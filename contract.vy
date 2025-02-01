# SPDX-License-Identifier: AGPL-3.0-only
# (c) 2025


struct Matcher:
	funds: uint256
	matcher_addr: address

	donate_addr: address
	match_mul: uint16
	deadline: uint64
	withdrawable_before_deadline: bool

matchers: public(DynArray[Matcher, 2**24])


@external
@view
def get_matchers() -> DynArray[Matcher, 2**24]:
	return self.matchers


@external
@payable
def deposit_matching_funds(
	donate_addr: address,
	match_mul: uint16,
	deadline: uint64,
	withdrawable_before_deadline: bool
):
	assert 0 < match_mul, 'match_mul == 0'
	if not withdrawable_before_deadline:
		assert convert(deadline, uint256) < unsafe_add(block.timestamp, 60 * 60 * 24 * 368), 'the deadline is out of range'

	self.matchers.append(Matcher(
		funds=msg.value,
		matcher_addr=msg.sender,
		donate_addr=donate_addr,
		match_mul=match_mul,
		deadline=deadline,
		withdrawable_before_deadline=withdrawable_before_deadline,
	))


@external
def withdraw_matching_funds(index: uint24):
	m: Matcher = self.matchers[index]
	assert m.matcher_addr == msg.sender, 'the sender is not the matcher'
	if not m.withdrawable_before_deadline:
		assert convert(m.deadline, uint256) < block.timestamp, 'funds cannot be withdrawed yet'

	send(msg.sender, m.funds)
	m.funds = 0
	self.matchers[index] = m


@external
@payable
def update_matching_funds(index: uint24, deadline: uint64):
	m: Matcher = self.matchers[index]
	assert m.matcher_addr == msg.sender, 'the sender is not the matcher'

	if m.withdrawable_before_deadline or (m.deadline < deadline and convert(deadline, uint256) < unsafe_add(block.timestamp, 60 * 60 * 24 * 368)):
		m.deadline = deadline
	else:
		assert deadline == 0, 'the deadline is out of range'

	m.funds += msg.value
	self.matchers[index] = m


@external
@payable
def donate(index: uint24, allowed_slippage: uint256):
	m: Matcher = self.matchers[index]

	assert block.timestamp < convert(m.deadline, uint256), 'matcher expired'
	donate_amount: uint256 = msg.value
	match_amount: uint256 = donate_amount * convert(m.match_mul, uint256) // 2**10

	if m.funds < match_amount:
		slippage: uint256 = match_amount - m.funds
		assert slippage <= allowed_slippage, 'slipped too much'
		match_amount = m.funds
	m.funds -= match_amount

	self.matchers[index] = m

	send(m.donate_addr, donate_amount + match_amount)
