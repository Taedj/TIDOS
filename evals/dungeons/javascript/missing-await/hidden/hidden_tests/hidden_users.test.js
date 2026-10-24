const test = require("node:test");
const assert = require("node:assert");
const { loadUser, loadAll } = require("../users.js");

function makeDb(delays) {
  const rows = { 1: { id: 1, name: "Lina" }, 2: { id: 2, name: "Omar" }, 3: { id: 3, name: "Sara" } };
  let active = 0, maxActive = 0;
  return {
    stats: () => maxActive,
    find: (id) => new Promise((resolve) => {
      active++; maxActive = Math.max(maxActive, active);
      setTimeout(() => { active--; resolve(rows[id] || null); }, delays[id] ?? 5);
    }),
  };
}

test("loadUser resolves and rejects", async () => {
  const db = makeDb({});
  assert.deepStrictEqual(await loadUser(db, 2), { id: 2, name: "Omar" });
  await assert.rejects(loadUser(db, 99), /not found/);
});

test("loadAll is concurrent and ordered", async () => {
  const db = makeDb({ 1: 30, 2: 5, 3: 15 });
  const users = await loadAll(db, [1, 2, 3]);
  assert.deepStrictEqual(users.map((u) => u.name), ["Lina", "Omar", "Sara"]);
  assert.strictEqual(db.stats(), 3);
});
