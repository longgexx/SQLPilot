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
                # Diagnosis
                if "diagnosis" in result:
                    console.print(Panel(JSON.from_data(result["diagnosis"]), title="[blue]Diagnosis[/blue]"))
                
                # Optimized SQL
                console.print(Panel(result.get("optimized_sql", "N/A"), title="[green]Optimized SQL[/green]"))
                
                # Validation
                if "validation" in result:
                    console.print(Panel(JSON.from_data(result["validation"]), title="[yellow]Validation Results[/yellow]"))
                
                # Explanation
                console.print(Panel(result.get("explanation", ""), title="Explanation"))
                
                confidence = result.get("confidence", "UNKNOWN")
                color = "green" if confidence == "HIGH" else "yellow" if confidence == "MEDIUM" else "red"
                console.print(f"Confidence: [{color}]{confidence}[/{color}]")

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
