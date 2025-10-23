from jinja2 import Template
import toml
import argparse

def render_agent_card(template_path, output_path, **kwargs):
    """Render a Jinja2 template into a TOML agent card and save it."""
    with open(template_path, "r") as f:
        template = Template(f.read())

    rendered = template.render(**kwargs)

    # Validate TOML
    try:
        parsed = toml.loads(rendered)
        print(f"✓ Generated valid TOML with {len(parsed)} sections")
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Generated invalid TOML: {exc}") from exc

    with open(output_path, "w") as f:
        f.write(rendered)

    return output_path

parser = argparse.ArgumentParser()
parser.add_argument(
    "--agent-name",
    default="[ALFWorld] Green Agent",
    help="Name of the agent to display on the agent card.",
)
parser.add_argument(
    "--task-id",
    default="cleanliness-v0",
    help="Task ID that the agent is designed to solve.",
)
parser.add_argument(
    "--template",
    default="agent_card.toml.j2",
    help="Path to the Jinja2 template file.",
)
parser.add_argument(
    "--host",
    default="0.0.0.0",
    help="Hostname where the agent will listen.",
)
parser.add_argument(
    "--output",
    default="agent_card_clean.toml",
    help="Output filename for the generated agent card.",
)
parser.add_argument(
    "--port",
    type=int,
    default=8000,
    help="Port number to run the agent server on.",
)

if __name__ == "__main__":
    args = parser.parse_args()

    render_agent_card(
        args.template,
        args.output,
        agent_name=args.agent_name,
        task_id=args.task_id,
        host=args.host,
        port=args.port,
    )
    print(
        f"Generated {args.output} with agent_name={args.agent_name}, "
        f"task_id={args.task_id}, host={args.host}, port={args.port}"
    )
