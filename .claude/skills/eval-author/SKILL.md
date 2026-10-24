---
name: eval-author
description: Turn a fixed bug or finished task into a verified TIDOS dungeon (eval task) so the regression can never come back unnoticed. Use after fixing a real bug.
---

# Eval (dungeon) author
1. `python -I <TIDOS>/tidos_evals/__main__.py new --suite <lang> --name <bug-name> --source <buggy project copy>`
2. **Prompt**: describe the bug as the user reported it - no hints about the fix.
3. **Hidden tests** in `hidden/hidden_tests/`: the regression test (+ edge cases). The agent never sees them.
4. **Solution** in `solution/`: the fixed files, same paths as the fixture.
5. **Validate**: `... validate --task <bug-name>` must show fixture=fail, solution=pass.
6. Remove secrets and private data from the fixture (the privacy firewall checks contributions).

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
