from datetime import datetime, timezone

import typer

from app.config import load_config
from app.db.models import Base, ScrapeRun
from app.db.session import SessionLocal, engine
from app.services.generate_diff_report import generate_report
from app.services.generate_jobs_report import generate_jobs_report
from app.services.generate_stats_report import generate_stats_report
from app.services.generate_weekly_report import generate_weekly_report
from app.services.scrape_company import scrape_company

app = typer.Typer(help="Local competitor hiring tracker MVP")


@app.command()
def scrape(config_path: str = "competitors.yaml") -> None:
    """Scrape all configured companies and persist snapshots."""
    Base.metadata.create_all(bind=engine)
    config = load_config(config_path)

    with SessionLocal() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        scrape_run = ScrapeRun(started_at=now)
        session.add(scrape_run)
        session.flush()

        for company in config.companies:
            try:
                scrape_company(session, company, scrape_run)
                typer.echo(f"  ✓ {company.name}")
            except Exception as e:
                typer.echo(f"  ✗ {company.name}: {e}", err=True)

        scrape_run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()
    typer.echo("Scrape completed.")


@app.command()
def report() -> None:
    """Generate a simple diff report from stored snapshots."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        typer.echo(generate_report(session))


@app.command()
def jobs(
    function: str | None = typer.Option(None, "--function", "-f", help="Filter by function tag (e.g. Eng, Product, Clinical)"),
    domain: str | None = typer.Option(None, "--domain", "-d", help="Filter by domain tag (e.g. prior_auth, fhir, hipaa)"),
    group_by: str = typer.Option("company", "--group-by", "-g", help="Group by: company, function, or domain"),
) -> None:
    """Browse active job postings with optional filters and grouping."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        typer.echo(generate_jobs_report(session, function_filter=function, domain_filter=domain, group_by=group_by))


@app.command()
def weekly(
    output: str = typer.Option("text", "--output", "-o", help="Output format: text or markdown"),
) -> None:
    """Generate a weekly competitor hiring summary report."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        typer.echo(generate_weekly_report(session, output_format=output))


@app.command()
def stats() -> None:
    """Show summary statistics for the latest scrape run."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        typer.echo(generate_stats_report(session))


if __name__ == "__main__":
    app()
