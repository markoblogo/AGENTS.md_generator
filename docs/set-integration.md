# agentsgen and SET

The supported pair is agentsgen 0.5.0 and SET 0.3.0. Both remain independent packages.

- agentsgen owns detection, marker-safe rendering, command checks, and repo artifacts.
- [SET](https://github.com/markoblogo/SET#quick-start) owns workflow presets and planning exports.

Start locally with agentsgen. Commit reviewed config and docs, then add its read-only
PR guard. Use SET when you need generation steps or a workflow proposal.
SET does not automatically commit or push the generated files.

SET defaults to agentsgen v0.5.0. A development ref is an explicit override;
review and test the pair before changing that override.

For a repo-local planner, install `abvx-set==0.3.0` and use
`set-plan-config-apply --config .set.json --format json --export-dir .set-plan`.
The format and a minimal config are in the SET README.
