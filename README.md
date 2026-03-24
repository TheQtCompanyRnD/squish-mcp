# Squish MCP Server

Squish Model Context Protocol (MCP) server enables AI agents to run and create [Squish](https://www.qt.io/quality-assurance/squish) ([documentation](https://doc.qt.io/squish/)) test scripts and test suites and analyze the results.

[Demo video of Squish MCP in action](https://youtu.be/ZCPqsOfUlMA)

## Requirements

- [**uv**](https://docs.astral.sh/uv/) - Python package manager, takes care of the correct Python version as well.
- [**Squish**](https://www.qt.io/quality-assurance/squish)
- [**GitHub Copilot**](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) - tested agent (Version => 0.40)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd squish-mcp
   ```
2. Install Python dependencies:
   ```bash
   uv sync
   ```
3. Configure the MCP server. The exact configuration entry will vary depending on your agent. For GitHub Copilot in VS Code, it may look like this (`.vscode/mcp.json` in your working directory):
   ```json
   {
       "servers": {
           "SquishMCP": {
               "command": "uv",
               "args": ["run", "--directory", "<path-to-squish-mcp>", "squish_mcp"],
               "env": {
                   "SQUISH_PREFIX": "<path-to-squish>",
               }
           }
       }
   }
   ```
   *MCP configuration documentation for [VS Code (GitHub Copilot)](https://code.visualstudio.com/docs/copilot/customization/mcp-servers) and [Claude Code](https://docs.claude.com/en/docs/claude-code/mcp).*

## Usage

Once your MCP server is configured and recognized by your agent, you are ready to start prompting. Most of the MCP tools operate in the context of a single test suite and accept the `test_suite_path` argument (a concrete `suite_*` directory path).

## Examples

<details>
<summary>Generate Test Cases</summary>
You can ask the agent to generate Squish test cases for your application under test (AUT). If you already have some Squish test cases available, you can reference them in the prompt to match the style and improve the quality of the generated test case.

> [!tip] Example prompt
> I'd like to make a new test in the suite_regression test suite. Launch the application, navigate to the 'Vehicle page'. One by one select the four indicators at the top of the page, and toggle them on then off. After toggling each one, take a screenshot verification point of the 3D car model on this page. Allow a brief delay after the toggle to let an animation play out.

> [!tip] Example prompt
> Make a new test case. After launching the application, navigate to the Media Tab. Go through all the 'tracks' in the music playlist dialog and select them. Verify each selected track on this page, is also present on the Vehicle page in the media player component there. Repeat for all tracks.
</details>

<details>
<summary>Execute a Test Case/Test Suite</summary>
You can ask the agent to run either a full test suite, or individual test case.

> [!tip] Example prompt
> Run the Squish test suite in this directory

> [!tip] Example prompt
> Execute the tst_login test case

> [!tip] Example prompt
> Run all Squish tests from suite_regression

The agent will automatically determine paths and execute the appropriate Squish commands using Squish MCP.
</details>

<details>
<summary>Generate Object Map</summary>

> [!note]
> This feature is currently only supported for Qt Widgets and QML-based applications.

This tool generates an object map from a given [object snapshot](https://doc.qt.io/squish/saveobjectsnapshot-function.html) which needs to be prepared beforehand. For more accurate results, the snapshot should also contain the [real names](https://doc.qt.io/squish/glossary.html#real-name-or-realname) of objects. To enable real name generation, modify the snapshot filter file at `<path-to-squish>/etc/qt_snapshot_filter.xml` and change `<realname exclude="yes"/>` to `<realname exclude="no"/>`.

> [!tip] Example prompt
> Create object map for all snapshots in /path/to/dir. Ensure the object maps are in alignment with current object reference naming patterns and scripting conventions

> [!tip] Example prompt
> Generate object map for the snapshot file: /path/to/snapshot.xml for the LoginPage
</details>

<details>
<summary>Generate a BDD Test Case</summary>
Squish has its own implementation and structure for running BDD tests. Squish MCP is aware of this structure and can produce both feature files and step function implementations.

> [!tip] Example prompt
> Convert my exists tst_happy_path_1 into a BDD test

Squish MCP will create both `test.py` and `test.feature` files with proper BDD structure, including step definitions and feature file format.
</details>

## Configuration

### SQUISH-RULES.yaml

For adding general "rules of thumb" for the LLM to follow, you can customize project-specific patterns and conventions:

```yaml
memories:
  requested_patterns:
    - pattern: "user asks for a screenshot verification"
      context: "Use the verify_image() function from global scripts"
    - pattern: "BDD step function with variable input"
      context: "Use |any| notation for variable parameters"
    - pattern: "Any time you, the LLM/ the AI agent, aren't sure of what to do in a test script"
      context: "Add a 'TODO: *' comment where you explain what needs to be done in a missing area."
```

You can use [`SQUISH-RULES.yaml.example`](src/squish_mcp/server/tools/analysis/SQUISH-RULES.yaml.example) for reference and create your own `SQUISH-RULES.yaml` in the `src/squish_mcp/server/tools/analysis` directory.

### Environment variables

- `SQUISH_GLOBAL_SCRIPTS`: Directory storing scripts available for all Squish test cases, see [Squish documentation](https://doc.qt.io/squish/global-scripts-view.html) for more information.

## High-Level Architecture Overview

<img src="squishmcp.png" width="708" height="549">

## License

See the [LICENSE](LICENSE) file for details.
