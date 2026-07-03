from __future__ import annotations

import sys

import typer

from .cli_core import register_core_commands
from .cli_extra import register_extra_commands
from .cli_fleet import register_fleet_commands
from .cli_okf import register_okf_commands
from .cli_pack import register_pack_commands
from .cli_reflect import register_reflect_commands
from .cli_task import register_task_commands


app = typer.Typer(
    add_completion=False,
    help="Generate and safely update AGENTS.md/RUNBOOK.md",
    invoke_without_command=True,
    no_args_is_help=True,
)
task_app = typer.Typer(
    add_completion=False,
    help="Manage proof-loop task artifacts under docs/ai/tasks/.",
)
okf_app = typer.Typer(
    add_completion=False,
    help="Export Open Knowledge Format bundles from repo AI artifacts.",
)
reflect_app = typer.Typer(
    add_completion=False,
    help="Experimental local reflection over agent session transcripts.",
)
fleet_app = typer.Typer(
    add_completion=False,
    help="Read-only team/fleet scans across many repositories.",
)
app.add_typer(task_app, name="task")
app.add_typer(okf_app, name="okf")
app.add_typer(reflect_app, name="reflect")
app.add_typer(fleet_app, name="fleet")
register_core_commands(app)
register_pack_commands(app)
register_task_commands(task_app)
register_okf_commands(okf_app)
register_reflect_commands(reflect_app)
register_fleet_commands(fleet_app)
register_extra_commands(app)


def main(argv: list[str] | None = None) -> None:
    app(prog_name="agentsgen")


if __name__ == "__main__":
    main(sys.argv[1:])
