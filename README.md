# Squish MCP Server

Squish Model Context Protocol (MCP) server enables AI agents to run and create [Squish](https://www.qt.io/quality-assurance/squish) ([documentation](https://doc.qt.io/squish/)) test scripts and test suites and analyze the results.

[Demo video of Squish MCP in action](https://youtu.be/ZCPqsOfUlMA)

## Requirements

- [**uv**](https://docs.astral.sh/uv/) — Python package manager (also takes care of the correct Python version)
- [**Squish**](https://www.qt.io/quality-assurance/squish) (version 9.0 or later)
- [**GitHub Copilot** (VS Code Extension)](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) (version 0.40 or later)

Tested on Windows 11, macOS, and Ubuntu 22.04.

### Known Limitations

- **Supported AUTs.** Only Qt Widgets and QML-based applications are currently tested.
- **Real names should be enabled.** Without enabling [real names](https://doc.qt.io/squish/glossary.html#real-name-or-realname), the performance gains provided by Squish MCP are severely reduced. To enable real name generation, modify the snapshot filter file at `<path-to-squish>/etc/qt_snapshot_filter.xml` and change `<realname exclude="yes"/>` to `<realname exclude="no"/>`.
- **Avoid spaces in paths.** VS Code has issues with spaces in file paths, which can cause otherwise correct configurations to fail. See [vscode#214931](https://github.com/microsoft/vscode/issues/214931).

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
3. Configure the MCP server in VS Code. The exact configuration entry will vary depending on your agent. For GitHub Copilot in VS Code, it may look like this (`.vscode/mcp.json` in your working directory):
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
   *MCP configuration documentation for [VS Code (GitHub Copilot)](https://code.visualstudio.com/docs/copilot/customization/mcp-servers)*

<details>
<summary>Using Other Agents</summary>

While this project is primarily tested with GitHub Copilot in VS Code, MCP is an open standard and other agents should work as well. Some alternatives:

- **Claude Code** — See the [Claude Code MCP documentation](https://docs.claude.com/en/docs/claude-code/mcp) for configuration details.
- **GitHub Copilot CLI** — The [Copilot CLI](https://github.com/features/copilot/cli) gives you more control over the agent from a terminal.
</details>

<details>
<summary>Starting the Server over HTTP</summary>

By default the server is started as a subprocess by the VS Code extension (stdio transport). Alternatively, you can start the server manually over HTTP for more control over the underlying process.

Start the server in a terminal:
```bash
SQUISH_PREFIX=<path-to-squish> uv run --directory <path-to-squish-mcp> squish_mcp --transport http --host localhost --port 8000
```

Then configure the MCP client to connect to it:
```json
{
    "servers": {
        "Squish-MCP": {
            "url": "http://localhost:8000/mcp",
            "type": "http"
        }
    }
}
```
</details>


## Usage

Once your MCP server is configured and recognized by your agent, you are ready to start prompting. Most of the MCP tools operate in the context of a single test suite and accept the `test_suite_path` argument (a concrete `suite_*` directory path).

## Example Usage

The examples below use the addressbook application bundled with Squish, found at `<path-to-squish>/examples/qt/addressbook/addressbook`.

### Execute a Test Case / Test Suite

You can ask the agent to run either a full test suite or an individual test case. The agent will automatically determine paths and execute the appropriate Squish commands.

> [!tip] Example prompt
> Run all Squish tests for the addressbook

The agent will locate the relevant tests and execute all it can relate to the addressbook. It may ask for clarifications if needed.

### Generate Test Cases

You can ask the agent to generate Squish test cases for your application under test (AUT).

> [!tip] Example prompt
> Create a new test suite for the addressbook application `<path-to-squish>/examples/qt/addressbook/addressbook`. Add a test to the suite that adds a contact in the addressbook and verifies its presence in the table.

The agent will create a test case and determine how to address individual objects (e.g. the add-button) in the application. It may reach out to the user, run intermediate test cases to programmatically scan the application's objects, or use existing test cases as reference.

If you already have Squish test cases available, you can reference them in the prompt to match the style and improve the quality of the generated test case.

### Generate a BDD Test Case

Squish has its own implementation and structure for running BDD tests. Squish MCP is aware of this structure and can produce both feature files and step function implementations.

> [!tip] Example prompt (assumes a generated test case from the prior steps)
> Convert the test case tst_add_contact into a BDD test

Squish MCP will create both `test.py` and `test.feature` files with proper BDD structure, including step definitions and feature file format.

<details>
<summary>Generate Object Map (advanced)</summary>

The MCP server offers a tool to generate an object map from a given [object snapshot](https://doc.qt.io/squish/saveobjectsnapshot-function.html), which needs to be prepared beforehand. It serves as a helper for the agent when generating test cases to produce correct object references, but can also be used directly.
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
