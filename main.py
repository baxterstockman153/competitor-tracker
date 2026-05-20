import typer

from app.config import load_config
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.services.generate_diff_report import generate_report
from app.services.scrape_company import scrape_company

app = typer.Typer(help="Local competitor hiring tracker MVP")


@app.command()
def scrape(config_path: str = "competitors.yaml") -> None:
    """Scrape all configured companies and persist snapshots."""
    Base.metadata.create_all(bind=engine)
    config = load_config(config_path)

    with SessionLocal() as session:
        for company in config.companies:
            scrape_company(session, company)
    typer.echo("Scrape completed.")


@app.command()
def report() -> None:
    """Generate a simple diff report from stored snapshots."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        typer.echo(generate_report(session))


if __name__ == "__main__":
    app()
