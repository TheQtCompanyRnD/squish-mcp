Squish test automation server for creating, analyzing, and running Squish suites and test cases.

General guidance:
- Most tools operate on one `suite_*` directory at a time.
- Infer the correct suite or `tst_*` case from workspace context.
- Pass absolute paths when required by a tool.
- Prefer these MCP tools over calling Squish CLI commands directly.
- Always consult Squish documentation via `analyze_squish_api_documentation` and read related files to ensure compatibility with the used Squish Version.

Recommended workflow:
- Before generating or editing tests, Review current suites and scripts in the working directory.
- Create suites and cases with `create_test_suite` and `create_test_case` instead of building the directory structure manually.
- After creating or changing a test, validate it with `run_test` and use the results to refine the suite or testcase.
- Each interaction will generally bring the AUT into a different state. This possibly invalidates previously collected object references (real names, etc.), you may have to get the new state by capturing the snapshot and the corresponding object map.

Squish-specific rules:
- In generated or updated test scripts, launch the AUT with `startApplication(<absolute path>)`, do not use AUT entries in `suite.conf`.
- When UI interactions need object references, add `saveObjectSnapshot(...)` at the relevant point in the script. The snapshot will be placed next to the test script.
- Then use `generate_page_objects_from_snapshot`.
- Reference generated objects via `import names` and `names.<EntryName>`. (You may use other package name, depending on how you generated the object map.)
- For BDD work, consult `analyze_bdd_documentation` and `analyze_bdd_context` before generating templates or cases.