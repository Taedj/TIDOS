const test = require("node:test");
const assert = require("node:assert");
const deepEqual = require("../deepEqual.js");

test("primitives", () => {
  assert.ok(deepEqual(NaN, NaN));
  assert.ok(deepEqual(0, -0));
  assert.ok(!deepEqual(1, "1"));
  assert.ok(!deepEqual(null, undefined));
  assert.ok(!deepEqual(null, {}));
});

test("objects and arrays", () => {
  assert.ok(deepEqual({ a: 1, b: [1, { c: 2 }] }, { b: [1, { c: 2 }], a: 1 }));
  assert.ok(!deepEqual({ a: undefined }, {}));
  assert.ok(!deepEqual([], {}));
  assert.ok(!deepEqual([1, 2], [2, 1]));
  class P { constructor() { this.x = 1; } }
  assert.ok(!deepEqual(new P(), { x: 1 }));
  assert.ok(deepEqual(new P(), new P()));
});

test("dates, regexps", () => {
  assert.ok(deepEqual(new Date(5), new Date(5)));
  assert.ok(!deepEqual(new Date(5), new Date(6)));
  assert.ok(deepEqual(/a+/gi, /a+/gi));
  assert.ok(!deepEqual(/a+/g, /a+/i));
});

test("maps and sets", () => {
  assert.ok(deepEqual(new Map([["k", { v: [1] }]]), new Map([["k", { v: [1] }]])));
  assert.ok(!deepEqual(new Map([["k", 1]]), new Map([["k", 2]])));
  assert.ok(deepEqual(new Set([{ a: 1 }, 2]), new Set([2, { a: 1 }])));
  assert.ok(!deepEqual(new Set([1, 2]), new Set([1, 3])));
  assert.ok(!deepEqual(new Set([1]), [1]));
});

test("cycles", () => {
  const a = { name: "a" }; a.self = a;
  const b = { name: "a" }; b.self = b;
  assert.ok(deepEqual(a, b));
  const c = { name: "c" }; c.self = c;
  assert.ok(!deepEqual(a, c));
});
