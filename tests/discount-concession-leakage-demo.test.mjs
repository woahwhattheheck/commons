import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyDiscount, parseMoneyToMinor, STATES } from '../discount-concession-leakage-demo.js';

const c = (referenceUnitMinor, billedUnitMinor, quantity = 1, authorityMode = 'none', authorizedUnitReductionMinor = null) =>
  classifyDiscount({ referenceUnitMinor, billedUnitMinor, quantity, authorityMode, authorizedUnitReductionMinor });

test('parses exact cents without float arithmetic', () => {
  assert.equal(parseMoneyToMinor('100'), 10000);
  assert.equal(parseMoneyToMinor('100.5'), 10050);
  assert.equal(parseMoneyToMinor('100.05'), 10005);
  assert.equal(parseMoneyToMinor('01.00'), null);
  assert.equal(parseMoneyToMinor('1.001'), null);
  assert.equal(parseMoneyToMinor('-1.00'), null);
});

test('full price', () => assert.equal(c(10000, 10000, 5).state, STATES.FULL_PRICE));
test('uplift', () => {
  const r = c(10000, 11000, 5);
  assert.equal(r.state, STATES.PRICE_UPLIFT_OBSERVED);
  assert.equal(r.discountReferenceMinor, 0);
});
test('unauthorized review', () => {
  const r = c(10000, 9000, 5);
  assert.equal(r.state, STATES.UNAUTHORIZED_DISCOUNT_REVIEW);
  assert.equal(r.discountReferenceMinor, 5000);
});
test('exact authority', () => assert.equal(c(10000, 9000, 5, 'exact').state, STATES.AUTHORIZED_DISCOUNT));
test('custom authority exact', () => assert.equal(c(10000, 9000, 5, 'custom', 1000).state, STATES.AUTHORIZED_DISCOUNT));
test('custom authority mismatch', () => assert.equal(c(10000, 9000, 5, 'custom', 500).state, STATES.DISCOUNT_VARIANCE_REVIEW));
test('invalid values fail closed', () => assert.equal(c(0, 1, 1).state, STATES.HOLD));
test('bool is not integer', () => assert.equal(classifyDiscount({referenceUnitMinor: 100, billedUnitMinor: 90, quantity: true}).state, STATES.HOLD));
test('safe arithmetic boundary', () => assert.equal(c(Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 2).state, STATES.HOLD));
