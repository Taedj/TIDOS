async function loadUser(db, id) {
  const row = await db.find(id);
  if (!row) throw new Error("not found");
  return { id: row.id, name: row.name };
}

async function loadAll(db, ids) {
  return Promise.all(ids.map((id) => loadUser(db, id)));
}

module.exports = { loadUser, loadAll };
