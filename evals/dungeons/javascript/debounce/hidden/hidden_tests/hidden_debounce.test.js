const test = require("node:test");
const assert = require("node:assert");
const debounce = require("../debounce.js");

test("trailing call with latest args and this", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  const obj = { tag: "o", run: debounce(function (x) { calls.push([this && this.tag, x]); }, 100) };
  obj.run(1); t.mock.timers.tick(50); obj.run(2); t.mock.timers.tick(99);
  assert.deepStrictEqual(calls, []);
  t.mock.timers.tick(1);
  assert.deepStrictEqual(calls, [["o", 2]]);
});

test("leading", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  const d = debounce((x) => calls.push(x), 100, { leading: true });
  d("a");
  assert.deepStrictEqual(calls, ["a"]);
  t.mock.timers.tick(150);
  assert.deepStrictEqual(calls, ["a"]);            // no trailing call: nothing else happened
  d("b"); d("c"); t.mock.timers.tick(100);
  assert.deepStrictEqual(calls, ["a", "b", "c"]);  // new burst: leading b, trailing c
});

test("cancel", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  const d = debounce((x) => calls.push(x), 100);
  d(1); d.cancel(); t.mock.timers.tick(500);
  assert.deepStrictEqual(calls, []);
});
