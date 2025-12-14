import asyncio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON
from typing import Optional
from pathlib import Path

from sqlpilot.core.config import settings
from sqlpilot.database.mysql import MySQLAdapter
from sqlpilot.core.tools import AgentTools
from sqlpilot.core.llm import LLMService
from sqlpilot.core.agent import SQLAgent

app = typer.Typer()
console = Console()

@app.command()
def optimize(
    sql: Optional[str] = typer.Option(None, "--sql", help="SQL query to optimize"),
    file: Optional[Path] = typer.Option(None, "--file", help="Path to file containing SQL"),
    database: str = typer.Option("mysql", "--database", help="Database type (mysql/postgresql)"),
    verbose: bool = typer.Option(False, "--verbose", help="Show verbose output"),
):
    """
    Optimize a SQL query using LLM Agent.
    """
    if file:
        if not file.exists():
            console.print(f"[red]File {file} not found[/red]")
            raise typer.Exit(code=1)
        sql = file.read_text().strip()
    
    if not sql:
        console.print("[red]Please provide SQL via --sql or --file[/red]")
        raise typer.Exit(code=1)

    async def run_optimization():
        # Setup (MVP: Only MySQL for now)
        if database != "mysql":
             console.print("[yellow]Only MySQL is currently supported in CLI (P0 requirement).[/yellow]")
        
        # Initialize components
        # Note: In a real app we might want to override settings based on CLI args (e.g. LLM provider)
        if not settings.shadow_database.mysql:
             console.print("[red]MySQL configuration missing in settings[/red]")
             raise typer.Exit(code=1)
            
        db = MySQLAdapter(settings.shadow_database.mysql)
        # Verify connection
        try:
            await db.connect()
        except Exception as e:
            console.print(f"[red]Failed to connect to database: {e}[/red]")
            return

        try:
            tools = AgentTools(db, settings)
            llm = LLMService(settings.llm)
            agent = SQLAgent(llm, tools)
            
            with console.status("[bold green]Agent working...[/bold green]"):
                result = await agent.optimize(sql, database)
            
            # Formatted Output
            if "error" in result:
                console.print(Panel(result["error"], title="[red]Error[/red]"))
                if verbose and "raw_content" in result:
                    console.print(result["raw_content"])
            else:
                from rich.table import Table
                from rich.columns import Columns
                from rich.markdown import Markdown
                from rich.syntax import Syntax
                from rich.text import Text
                
                # --- Header ---
                console.print(f"\n[bold blue]SQLPilot Optimization Report[/bold blue] (Target: {database})")
                
                # --- SQL Comparison ---
                grid = Table.grid(expand=True, padding=1)
                grid.add_column(justify="left", ratio=1)
                grid.add_column(justify="left", ratio=1)
                
                orig_sql = Syntax(result.get("original_sql", sql), "sql", theme="monokai", line_numbers=True)
                opt_sql_text = result.get("optimized_sql", "N/A")
                opt_sql_syntax = Syntax(opt_sql_text, "sql", theme="monokai", line_numbers=True)
                
                grid.add_row(
                    Panel(orig_sql, title="[yellow]Original SQL[/yellow]", border_style="yellow"),
                    Panel(opt_sql_syntax, title="[green]Optimized SQL[/green]", border_style="green")
                )
                console.print(grid)
                
                # --- Diagnosis & Explanation ---
                if "diagnosis" in result:
                    diag = result["diagnosis"]
                    diag_table = Table(show_header=True, header_style="bold magenta")
                    diag_table.add_column("Root Cause", style="dim")
                    diag_table.add_column("Bottlenecks")
                    
                    bottlenecks = "\n".join([f"• {b}" for b in diag.get("bottlenecks", [])])
                    diag_table.add_row(diag.get("root_cause", "Unknown"), bottlenecks)
                    
                    console.print(Panel(diag_table, title="Diagnosis"))
                
                # Explanation (Markdown)
                explanation = result.get("explanation", "")
                if explanation:
                    console.print(Panel(Markdown(explanation), title="Analysis"))
                
                # --- Validation ---
                if "validation" in result:
                    val = result["validation"]
                    val_table = Table(title="Validation Results", expand=True)
                    val_table.add_column("Check", justify="right", style="cyan", no_wrap=True)
                    val_table.add_column("Status", justify="center")
                    val_table.add_column("Details")
                    
                    # Semantic
                    sem = val.get("semantic_check", {})
                    sem_status = f"[green]{sem.get('status')}[/green]" if sem.get('status') == 'passed' else f"[red]{sem.get('status')}[/red]"
                    val_table.add_row("Semantic", sem_status, sem.get("details", ""))
                    
                    # Performance
                    perf = val.get("performance_check", {})
                    perf_status = "[green]passed[/green]" if perf.get("status") == "passed" else f"[red]{perf.get('status')}[/red]"
                    
                    orig_ms = perf.get("original_time_ms", 0)
                    opt_ms = perf.get("optimized_time_ms", 0)
                    ratio = perf.get("improvement_ratio", 0)
                    
                    perf_details = f"Original: {orig_ms:.2f}ms -> Optimized: {opt_ms:.2f}ms (Ratio: {ratio:.2f})"
                    val_table.add_row("Performance", perf_status, perf_details)
                    
                    # Boundary
                    bound = val.get("boundary_tests", {})
                    bound_status = bound.get("status")
                    if bound_status:
                        val_table.add_row("Boundary Tests", bound_status, f"Run: {bound.get('tests_run', 0)}")
                        
                    console.print(val_table)

                # --- Final Verdict ---
                confidence = result.get("confidence", "UNKNOWN")
                rec = result.get("recommendation", "manual_review")
                
                conf_color = "green" if confidence == "HIGH" else "yellow" if confidence == "MEDIUM" else "red"
                rec_color = "green" if rec == "auto_apply" else "yellow" if rec == "manual_review" else "red"
                
                console.print(f"\nFinal Verdict: Confidence [{conf_color}]{confidence}[/{conf_color}] | Recommendation: [{rec_color}]{rec.upper()}[/{rec_color}]\n")

        finally:
            await db.close()

    asyncio.run(run_optimization())

@app.command()
def config():
    """
    Show current configuration.
    """
    console.print(settings.model_dump())

@app.command()
def health():
    """
    Check health of components.
    """
    async def run_check():
        # Check DB
        status = {"database": "unknown", "llm": "unknown"}
        if settings.shadow_database.mysql:
            try:
                db = MySQLAdapter(settings.shadow_database.mysql)
                await db.connect()
                ver = await db.get_version()
                await db.close()
                status["database"] = f"ok (MySQL {ver})"
            except Exception as e:
                status["database"] = f"failed ({e})"
        else:
            status["database"] = "not_configured"
            
        # Check LLM (basic client init check)
        try:
             LLMService(settings.llm)
             status["llm"] = "ok (initialized)"
        except Exception as e:
             status["llm"] = f"failed ({e})"

        console.print(JSON.from_data(status))

    asyncio.run(run_check())

if __name__ == "__main__":
    app()
