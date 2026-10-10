# Privacy

The `gh-settings` and `acg-release` plugins contain instructions only.
The `automation` plugin also includes a read-only local analyzer for user-supplied
portfolio snapshots. It reads the selected input and writes its analysis to
standard output; it does not query or change a scheduler.

The plugins have no telemetry, network client, bundled credentials, app, MCP
server, or hook. ACG Box does not receive user data through these plugins.

When Codex uses a plugin, tool access remains subject to the user request,
repository instructions, and active Codex environment. Keep private task records
and analysis output outside public repositories.

Report a privacy concern through the `acg-box/agentry` repository issue tracker.
