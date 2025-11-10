"""
Agent Logger - Verbose logging for multi-agent hype cycle pipeline.

Features:
- Colored terminal output (rich library)
- Structured JSON logs for FastAPI UI
- Agent-specific log methods
- LLM prompt/response capture
- Timing and performance metrics
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.progress import Progress
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("[WARN] rich library not installed. Install with: pip install rich")
    print("[WARN] Falling back to basic print statements")


class LogLevel(Enum):
    """Logging verbosity levels."""
    SILENT = 0   # No output
    NORMAL = 1   # Final results only
    VERBOSE = 2  # Agent inputs/outputs
    DEBUG = 3    # LLM prompts, graph queries, timing


class AgentLogger:
    """Logger for multi-agent pipeline with terminal + JSON output."""

    def __init__(self, level: LogLevel = LogLevel.NORMAL, log_file: Optional[Path] = None):
        """
        Initialize logger.

        Args:
            level: Logging verbosity level
            log_file: Optional path to save structured JSON logs
        """
        self.level = level
        self.log_file = log_file
        self.logs: List[Dict[str, Any]] = []  # In-memory structured logs for UI

        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

    def log_pipeline_start(self, tech_count: int, enable_tavily: bool, **kwargs):
        """Log pipeline initialization."""
        if self.level.value >= LogLevel.NORMAL.value:
            if self.console:
                self.console.print(f"\n[bold cyan]═══ Pipeline Started ═══[/bold cyan]")
                self.console.print(f"Technologies to analyze: [bold]{tech_count}[/bold]")
                self.console.print(f"Tavily real-time search: [bold]{'enabled' if enable_tavily else 'disabled'}[/bold]")

                # Show additional config
                for key, val in kwargs.items():
                    self.console.print(f"{key.replace('_', ' ').title()}: [bold]{val}[/bold]")
            else:
                print(f"\n=== Pipeline Started ===")
                print(f"Technologies to analyze: {tech_count}")
                print(f"Tavily real-time search: {'enabled' if enable_tavily else 'disabled'}")
                for key, val in kwargs.items():
                    print(f"{key.replace('_', ' ').title()}: {val}")

        self._append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "pipeline_start",
            "tech_count": tech_count,
            "enable_tavily": enable_tavily,
            **kwargs
        })

    def log_agent_start(self, agent_name: str, tech_id: str, inputs: Optional[Dict[str, Any]] = None):
        """Log agent execution start."""
        if self.level.value >= LogLevel.VERBOSE.value:
            if self.console:
                self.console.print(f"\n[bold yellow]→ {agent_name}[/bold yellow] | [cyan]{tech_id}[/cyan]")
            else:
                print(f"\n→ {agent_name} | {tech_id}")

            if self.level.value >= LogLevel.DEBUG.value and inputs:
                # Show key inputs
                for key, val in inputs.items():
                    if key.startswith("_"):  # Skip internal fields
                        continue
                    if isinstance(val, (int, float, str, bool)):
                        if self.console:
                            self.console.print(f"  [dim]{key}:[/dim] {val}")
                        else:
                            print(f"  {key}: {val}")

        # Structured log
        self._append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "agent_start",
            "agent": agent_name,
            "tech_id": tech_id,
            "inputs": inputs if self.level == LogLevel.DEBUG and inputs else {},
        })

    def log_llm_call(self, agent_name: str, prompt: str, response: Any, model: str, tech_id: str = ""):
        """Log LLM prompt and response."""
        if self.level.value >= LogLevel.DEBUG.value:
            if self.console:
                # Truncate very long prompts
                display_prompt = prompt[:800] + "..." if len(prompt) > 800 else prompt

                self.console.print(Panel(
                    Syntax(display_prompt, "markdown", theme="monokai"),
                    title=f"[cyan]{agent_name} - LLM Prompt ({model})[/cyan]",
                    expand=False
                ))

                # Format response
                response_str = str(response)
                if len(response_str) > 500:
                    response_str = response_str[:500] + "..."

                self.console.print(Panel(
                    response_str,
                    title=f"[green]{agent_name} - LLM Response[/green]",
                    expand=False
                ))
            else:
                print(f"\n[LLM PROMPT - {agent_name}]")
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
                print(f"\n[LLM RESPONSE - {agent_name}]")
                print(str(response)[:500])

        # Structured log (full prompt for debugging)
        self._append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "llm_call",
            "agent": agent_name,
            "tech_id": tech_id,
            "model": model,
            "prompt": prompt,
            "response": str(response),
        })

    def log_agent_output(self, agent_name: str, tech_id: str, outputs: Dict[str, Any]):
        """Log agent execution completion."""
        if self.level.value >= LogLevel.VERBOSE.value:
            if self.console:
                self.console.print(f"[bold green]✓ {agent_name}[/bold green] | [cyan]{tech_id}[/cyan]")
            else:
                print(f"✓ {agent_name} | {tech_id}")

            # Show key outputs
            key_fields = self._get_key_fields_for_agent(agent_name)
            for field in key_fields:
                if field in outputs:
                    val = outputs[field]
                    if isinstance(val, float):
                        display_val = f"{val:.1f}"
                    elif isinstance(val, str) and len(val) < 100:
                        display_val = val
                    elif isinstance(val, str):
                        display_val = val[:97] + "..."
                    else:
                        display_val = str(val)

                    if self.console:
                        self.console.print(f"  [dim]{field}:[/dim] {display_val}")
                    else:
                        print(f"  {field}: {display_val}")

        # Structured log
        self._append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "agent_complete",
            "agent": agent_name,
            "tech_id": tech_id,
            "outputs": outputs,
        })

    def log_technology_complete(self, tech_id: str, final_state: Dict[str, Any]):
        """Log single technology analysis completion."""
        if self.level.value >= LogLevel.NORMAL.value:
            if self.console:
                table = Table(title=f"[bold]{tech_id.replace('_', ' ').title()}[/bold] - Analysis Complete")
                table.add_column("Metric", style="cyan", no_wrap=True)
                table.add_column("Value", style="green")

                # Display phase with proper casing
                phase_display = final_state.get("hype_cycle_phase", "unknown")
                if phase_display == "innovation_trigger":
                    phase_display = "Innovation Trigger"
                elif phase_display == "peak":
                    phase_display = "Peak of Inflated Expectations"
                elif phase_display == "trough":
                    phase_display = "Trough of Disillusionment"
                elif phase_display == "slope":
                    phase_display = "Slope of Enlightenment"
                elif phase_display == "plateau":
                    phase_display = "Plateau of Productivity"

                table.add_row("Phase", phase_display)
                table.add_row("Innovation", f"{final_state.get('innovation_score', 0):.1f}/100")
                table.add_row("Adoption", f"{final_state.get('adoption_score', 0):.1f}/100")
                table.add_row("Narrative", f"{final_state.get('narrative_score', 0):.1f}/100")
                table.add_row("Risk", f"{final_state.get('risk_score', 0):.1f}/100")
                table.add_row("Hype", f"{final_state.get('hype_score', 0):.1f}/100")
                table.add_row("Chart X", f"{final_state.get('chart_x', 0):.3f}")

                self.console.print(table)

                # Show executive summary if available
                if final_state.get("executive_summary"):
                    summary = final_state["executive_summary"]
                    if len(summary) > 300:
                        summary = summary[:297] + "..."
                    self.console.print(f"\n[italic]{summary}[/italic]\n")
            else:
                print(f"\n=== {tech_id.replace('_', ' ').title()} - Analysis Complete ===")
                print(f"Phase: {final_state.get('hype_cycle_phase', 'unknown')}")
                print(f"Innovation: {final_state.get('innovation_score', 0):.1f}/100")
                print(f"Adoption: {final_state.get('adoption_score', 0):.1f}/100")
                print(f"Narrative: {final_state.get('narrative_score', 0):.1f}/100")
                print(f"Risk: {final_state.get('risk_score', 0):.1f}/100")
                print(f"Hype: {final_state.get('hype_score', 0):.1f}/100")
                print(f"Chart X: {final_state.get('chart_x', 0):.3f}")

                if final_state.get("executive_summary"):
                    print(f"\n{final_state['executive_summary'][:300]}\n")

    def log_pipeline_complete(self, tech_count: int, duration_seconds: float):
        """Log pipeline completion."""
        if self.level.value >= LogLevel.NORMAL.value:
            if self.console:
                self.console.print(f"\n[bold green]═══ Pipeline Complete ═══[/bold green]")
                self.console.print(f"Analyzed [bold]{tech_count}[/bold] technologies in [bold]{duration_seconds:.1f}s[/bold]")
                if tech_count > 0:
                    self.console.print(f"Average: [bold]{duration_seconds/tech_count:.2f}s[/bold] per technology")
            else:
                print(f"\n=== Pipeline Complete ===")
                print(f"Analyzed {tech_count} technologies in {duration_seconds:.1f}s")
                if tech_count > 0:
                    print(f"Average: {duration_seconds/tech_count:.2f}s per technology")

        # Save structured logs to file
        if self.log_file:
            self._save_logs()

    def _get_key_fields_for_agent(self, agent_name: str) -> List[str]:
        """Get key output fields to display per agent."""
        field_map = {
            "tech_discovery": ["tech_count", "community_distribution"],
            "innovation_scorer": ["innovation_score", "innovation_reasoning"],
            "adoption_scorer": ["adoption_score", "adoption_reasoning"],
            "narrative_scorer": ["narrative_score", "narrative_reasoning", "freshness_score"],
            "risk_scorer": ["risk_score", "risk_reasoning"],
            "hype_scorer": ["hype_score", "layer_divergence"],
            "phase_detector": ["hype_cycle_phase", "phase_confidence"],
            "llm_analyst": ["executive_summary", "key_insight"],
            "ensemble": ["chart_x", "chart_y", "weighted_score"],
            "chart_generator": ["phase"],
            "evidence_compiler": ["evidence_count"],
            "validator": ["validation_status", "validation_errors"],
        }
        return field_map.get(agent_name, [])

    def _append_log(self, log_entry: Dict[str, Any]):
        """Append structured log entry."""
        self.logs.append(log_entry)

    def _save_logs(self):
        """Save structured logs to JSON file."""
        try:
            with open(self.log_file, "w") as f:
                json.dump(self.logs, f, indent=2)

            if self.level.value >= LogLevel.NORMAL.value:
                if self.console:
                    self.console.print(f"[dim]Structured logs saved to {self.log_file}[/dim]")
                else:
                    print(f"Structured logs saved to {self.log_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save logs: {e}")

    def get_logs(self) -> List[Dict[str, Any]]:
        """Get in-memory structured logs (for FastAPI streaming)."""
        return self.logs
