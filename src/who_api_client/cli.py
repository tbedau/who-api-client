import getpass

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .client import WHOAPIClient
from .credentials import CredentialManager
from .exceptions import AuthenticationError, ConfigurationError

app = typer.Typer(
    name="who-api-client",
    help="A type-safe Python client for the WHO Classification of Tumours API",
    rich_markup_mode="rich",
)
console = Console()


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    A type-safe Python client for the WHO Classification of Tumours API.

    Content hierarchy: series → books → chapters → ancestors

    Typical workflow:
    1. who-api-client series     # List book series
    2. who-api-client books      # List individual books
    3. who-api-client chapters 48  # List chapters for book ID 48
    4. who-api-client ancestors 48 161  # Show ancestor chain for chapter 161
    5. who-api-client favourites  # Show your favourite chapters
    6. who-api-client search "adenocarcinoma"  # Search across content
    """
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command()
def series(
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """
    List all available WHO Classification of Tumours book series.

    Shows the high-level series groupings. Use 'books' command to see individual books.
    """
    try:
        with WHOAPIClient() as client:
            rprint("[bold blue]Fetching book series...[/bold blue]")

            # Get book series - authentication happens automatically via decorator
            book_series = client.get_book_series()

            rprint(f"[green]Found {book_series.count} book series![/green]")

            if format.lower() == "json":
                # Output as JSON
                console.print_json(book_series.model_dump_json())
            else:
                # Output as table
                table = Table(
                    title=f"WHO Classification of Tumours - Available Book Series ({book_series.count} total)",
                    show_header=True,
                    header_style="bold magenta",
                )

                table.add_column("Series", style="cyan", no_wrap=True)
                table.add_column("Books", style="yellow", justify="center")
                table.add_column("Book Titles", style="white")

                for series in book_series.series:
                    book_titles = ", ".join(
                        [book.bookTitle for book in series.books[:3]]
                    )
                    if len(series.books) > 3:
                        book_titles += f" ... (+{len(series.books) - 3} more)"

                    table.add_row(series.series, str(len(series.books)), book_titles)

                console.print(table)

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch book series: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def books(
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """
    List all available WHO Classification of Tumours books.

    Shows individual books with their details. Use 'chapters' command with a book ID to see chapters.
    """
    try:
        with WHOAPIClient() as client:
            rprint("[bold blue]Fetching all books...[/bold blue]")

            books = client.get_books()

            rprint(f"[green]Found {len(books)} books![/green]")

            if format.lower() == "json":
                # Output as JSON
                import json

                books_data = [book.model_dump() for book in books]
                console.print_json(json.dumps(books_data))
            else:
                # Output as table
                table = Table(
                    title=f"WHO Classification of Tumours - All Books ({len(books)} total)",
                    show_header=True,
                    header_style="bold magenta",
                )

                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Title", style="white")
                table.add_column("Series", style="yellow")
                table.add_column("Revision", style="green")
                table.add_column("Active", style="red", justify="center")

                for book in books:
                    table.add_row(
                        str(book.bookid),
                        book.bookTitle,
                        book.series,
                        book.revision,
                        "✓" if book.isActive else "✗",
                    )

                console.print(table)

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch books: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def chapters(
    book_id: int = typer.Argument(..., help="Book ID to fetch chapters for"),
    format: str = typer.Option(
        "tree", "--format", "-f", help="Output format: tree, table, json"
    ),
    max_depth: int = typer.Option(
        None, "--max-depth", "-d", help="Maximum depth to display (tree format only)"
    ),
):
    """
    List chapters for a specific book.

    Use 'books' command to find book IDs.
    """
    try:
        with WHOAPIClient() as client:
            rprint(f"[bold blue]Fetching chapters for book ID {book_id}...[/bold blue]")

            # Verify book exists
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            chapters = client.get_chapters(book_id)

            # Count total chapters
            total_chapters = 0

            def count_chapters(chapters):
                nonlocal total_chapters
                total_chapters += len(chapters)
                for chapter in chapters:
                    count_chapters(chapter.sub_chapters)

            count_chapters(chapters)

            rprint(
                f"[green]Found {len(chapters)} top-level chapters ({total_chapters} total) for '{book.bookTitle}'[/green]"
            )

            if format.lower() == "json":
                # Output as JSON
                import json

                chapters_data = [chapter.model_dump() for chapter in chapters]
                console.print_json(json.dumps(chapters_data))
            elif format.lower() == "table":
                # Flatten chapters for table display
                table = Table(
                    title=f"Chapters for '{book.bookTitle}' ({total_chapters} total)",
                    show_header=True,
                    header_style="bold magenta",
                )

                table.add_column("Number", style="cyan", no_wrap=True)
                table.add_column("Title", style="white")
                table.add_column("Level", style="yellow", justify="center")
                table.add_column("Position", style="green", justify="center")

                def add_chapters_to_table(chapters, depth=0):
                    for chapter in chapters:
                        if max_depth is None or depth < max_depth:
                            indent = "  " * depth
                            table.add_row(
                                chapter.chapterNumber,
                                f"{indent}{chapter.chapterTitle}",
                                str(chapter.chapterLevel),
                                str(chapter.chapterPosition),
                            )
                            add_chapters_to_table(chapter.sub_chapters, depth + 1)

                add_chapters_to_table(chapters)
                console.print(table)
            else:
                # Tree format (default)
                def print_chapters(chapters, indent=0):
                    for _i, chapter in enumerate(chapters):
                        if max_depth is None or indent < max_depth:
                            prefix = "  " * indent
                            if indent == 0:
                                icon = "📚"
                            elif len(chapter.sub_chapters) > 0:
                                icon = "📁"
                            else:
                                icon = "📄"

                            console.print(
                                f"{prefix}{icon} {chapter.chapterNumber} - {chapter.chapterTitle}"
                            )

                            if chapter.sub_chapters:
                                print_chapters(chapter.sub_chapters, indent + 1)

                print_chapters(chapters)

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch chapters: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def ancestors(
    book_id: int = typer.Argument(..., help="Book ID"),
    chapter_id: int = typer.Argument(..., help="Chapter ID to get ancestors for"),
    format: str = typer.Option(
        "tree", "--format", "-f", help="Output format: tree, table, json"
    ),
):
    """
    Show the ancestor chain for a specific chapter.

    Displays the hierarchical path from root to the specified chapter.
    Use 'books' command to find book IDs and 'chapters' command to find chapter IDs.
    """
    try:
        with WHOAPIClient() as client:
            rprint(
                f"[bold blue]Fetching ancestors for chapter {chapter_id} in book {book_id}...[/bold blue]"
            )

            # Verify book exists
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            ancestors = client.get_chapter_ancestors(book_id, chapter_id)

            if not ancestors:
                rprint(
                    f"[yellow]No ancestors found for chapter {chapter_id} (it may be a root chapter)[/yellow]"
                )
                raise typer.Exit(0)

            rprint(
                f"[green]Found {len(ancestors)} ancestors for chapter in '{book.bookTitle}'[/green]"
            )

            if format.lower() == "json":
                # Output as JSON
                import json

                ancestors_data = [ancestor.model_dump() for ancestor in ancestors]
                console.print_json(json.dumps(ancestors_data))
            elif format.lower() == "table":
                # Table format
                table = Table(
                    title=f"Ancestor Chain for Chapter {chapter_id} in '{book.bookTitle}'",
                    show_header=True,
                    header_style="bold magenta",
                )

                table.add_column("Level", style="cyan", justify="center")
                table.add_column("Number", style="yellow", no_wrap=True)
                table.add_column("Title", style="white")
                table.add_column("Position", style="green", justify="center")

                for ancestor in ancestors:
                    table.add_row(
                        str(ancestor.chapterLevel),
                        ancestor.chapterNumber,
                        ancestor.chapterTitle,
                        str(ancestor.chapterPosition),
                    )

                console.print(table)
            else:
                # Tree format (default)
                console.print(f"[bold]Ancestor chain for chapter {chapter_id}:[/bold]")
                for i, ancestor in enumerate(ancestors):
                    indent = "  " * i
                    if i == len(ancestors) - 1:
                        icon = "🎯"  # Target chapter
                    elif ancestor.chapterLevel == 1:
                        icon = "📚"  # Root level
                    else:
                        icon = "📁"  # Intermediate level

                    console.print(
                        f"{indent}{icon} {ancestor.chapterNumber} - {ancestor.chapterTitle}"
                    )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch ancestors: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def content(
    book_id: int = typer.Argument(..., help="Book ID"),
    chapter_id: int = typer.Argument(..., help="Chapter ID"),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, html, json"
    ),
    max_sections: int = typer.Option(
        None, "--max-sections", "-m", help="Maximum number of sections to display"
    ),
):
    """
    Display the content of a specific chapter.

    This retrieves the actual text content, including headings and paragraphs.
    Use 'chapters' command to find chapter IDs.
    """
    try:
        with WHOAPIClient() as client:
            rprint(
                f"[bold blue]Fetching content for chapter {chapter_id} in book {book_id}...[/bold blue]"
            )

            # Verify book and get title
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            # Get chapter ancestors for context
            try:
                ancestors = client.get_chapter_ancestors(book_id, chapter_id)
                chapter_title = (
                    ancestors[-1].chapterTitle if ancestors else "Unknown Chapter"
                )
            except Exception:
                chapter_title = f"Chapter {chapter_id}"

            content_sections = client.get_chapter_content(book_id, chapter_id)

            if not content_sections:
                rprint(f"[yellow]No content found for chapter {chapter_id}[/yellow]")
                raise typer.Exit(0)

            sections_to_show = (
                content_sections[:max_sections] if max_sections else content_sections
            )

            rprint(
                f"[green]Found {len(content_sections)} content sections for '{chapter_title}' in '{book.bookTitle}'[/green]"
            )

            if format.lower() == "json":
                # Output as JSON
                import json

                sections_data = [section.model_dump() for section in sections_to_show]
                console.print_json(json.dumps(sections_data))
            elif format.lower() == "html":
                # Output as HTML
                console.print(f"[bold]Content for: {chapter_title}[/bold]")
                console.print(f"[dim]Book: {book.bookTitle}[/dim]\n")

                for i, section in enumerate(sections_to_show):
                    if section.headingTitle:
                        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")
                        console.print(
                            f"[bold yellow]{section.headingTitle}[/bold yellow]"
                        )
                        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")

                    for contrib in section.contributions:
                        console.print(contrib.headingText)

                    if i < len(sections_to_show) - 1:
                        console.print()

                if max_sections and len(content_sections) > max_sections:
                    console.print(
                        f"\n[dim]... {len(content_sections) - max_sections} more sections[/dim]"
                    )
            else:
                # Text format (default) - strip HTML tags and decode entities
                import html
                import re

                console.print(f"[bold]Content for: {chapter_title}[/bold]")
                console.print(f"[dim]Book: {book.bookTitle}[/dim]\n")

                for i, section in enumerate(sections_to_show):
                    if section.headingTitle:
                        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")
                        console.print(
                            f"[bold yellow]{section.headingTitle}[/bold yellow]"
                        )
                        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")

                    for contrib in section.contributions:
                        # Strip HTML tags
                        clean_text = re.sub("<[^<]+?>", "", contrib.headingText).strip()
                        # Decode HTML entities (like &nbsp;, &ndash;, etc.)
                        clean_text = html.unescape(clean_text)
                        # Clean up extra whitespace and normalize spaces
                        clean_text = re.sub(r"\s+", " ", clean_text)
                        # Remove non-breaking spaces that might remain
                        clean_text = clean_text.replace("\u00a0", " ")
                        console.print(clean_text.strip())

                    if i < len(sections_to_show) - 1:
                        console.print()

                if max_sections and len(content_sections) > max_sections:
                    console.print(
                        f"\n[dim]... {len(content_sections) - max_sections} more sections[/dim]"
                    )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch content: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def attachments(
    book_id: int = typer.Argument(..., help="Book ID"),
    chapter_id: int = typer.Argument(..., help="Chapter ID"),
    format: str = typer.Option(
        "list", "--format", "-f", help="Output format: list, json"
    ),
    type_filter: str = typer.Option(
        None, "--type", "-t", help="Filter by type: figure, wsi, table, all"
    ),
):
    """
    List attachments (images, tables, WSI) for a specific chapter.

    Shows figures, whole slide images (WSI), tables, and other media associated with chapter content.
    Use 'chapters' command to find chapter IDs.
    """
    try:
        with WHOAPIClient() as client:
            rprint(
                f"[bold blue]Fetching attachments for chapter {chapter_id} in book {book_id}...[/bold blue]"
            )

            # Verify book and get title
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            # Get chapter ancestors for context
            try:
                ancestors = client.get_chapter_ancestors(book_id, chapter_id)
                chapter_title = (
                    ancestors[-1].chapterTitle if ancestors else "Unknown Chapter"
                )
            except Exception:
                chapter_title = f"Chapter {chapter_id}"

            attachments = client.get_attachments(book_id, chapter_id)

            if not attachments:
                rprint(
                    f"[yellow]No attachments found for chapter {chapter_id}[/yellow]"
                )
                raise typer.Exit(0)

            # Filter by type if specified
            if type_filter:
                if type_filter.lower() == "figure":
                    attachments = [a for a in attachments if a.is_figure]
                elif type_filter.lower() == "wsi":
                    attachments = [a for a in attachments if a.is_wsi]
                elif type_filter.lower() == "table":
                    attachments = [a for a in attachments if a.is_table]
                # "all" or any other value shows all attachments

            if not attachments:
                rprint(
                    f"[yellow]No {type_filter} attachments found for chapter {chapter_id}[/yellow]"
                )
                raise typer.Exit(0)

            # Count by type
            figures = [a for a in attachments if a.is_figure]
            wsi = [a for a in attachments if a.is_wsi]
            tables = [a for a in attachments if a.is_table]

            rprint(
                f"[green]Found {len(attachments)} attachments for '{chapter_title}' in '{book.bookTitle}'[/green]"
            )
            rprint(
                f"[dim]📷 {len(figures)} figures, 🔬 {len(wsi)} WSI, 📊 {len(tables)} tables[/dim]"
            )

            if format.lower() == "json":
                # Output as JSON
                import json

                attachments_data = [
                    attachment.model_dump() for attachment in attachments
                ]
                console.print_json(json.dumps(attachments_data))
            else:
                # List format (default)
                for i, attachment in enumerate(attachments):
                    console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")

                    # Determine icon based on type
                    if attachment.is_figure:
                        icon = "📷"
                        type_label = "Figure"
                    elif attachment.is_wsi:
                        icon = "🔬"
                        type_label = "WSI"
                    elif attachment.is_table:
                        icon = "📊"
                        type_label = "Table"
                    else:
                        icon = "📎"
                        type_label = attachment.type

                    console.print(
                        f"[bold yellow]{icon} Attachment {i + 1} ({type_label})[/bold yellow]"
                    )
                    console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")

                    # Show basic info
                    console.print(f"[bold]File ID:[/bold] {attachment.fileId}")

                    if attachment.clean_title:
                        console.print(f"[bold]Title:[/bold] {attachment.clean_title}")

                    if attachment.clean_diagnosis:
                        console.print(
                            f"[bold]Diagnosis:[/bold] {attachment.clean_diagnosis}"
                        )

                    if attachment.clean_legend:
                        console.print(f"[bold]Legend:[/bold] {attachment.clean_legend}")

                    if attachment.clean_source:
                        console.print(f"[bold]Source:[/bold] {attachment.clean_source}")

                    if attachment.clean_copyright:
                        console.print(
                            f"[bold]Copyright:[/bold] {attachment.clean_copyright}"
                        )

                    # Type-specific info
                    if attachment.is_figure:
                        console.print(f"[bold]Image URL:[/bold] {attachment.imageUrl}")
                        console.print(f"[bold]Thumbnail:[/bold] {attachment.thumbnail}")
                    elif attachment.is_wsi:
                        console.print(
                            f"[bold]WSI URL (DZI):[/bold] {attachment.imageUrl}"
                        )
                        console.print(
                            "[dim]Note: WSI files use DeepZoom Image format (.dzi)[/dim]"
                        )
                    elif attachment.is_table:
                        console.print(
                            f"[bold]Table HTML:[/bold] {len(attachment.tablehtml)} characters"
                        )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch attachments: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def tables(
    book_id: int = typer.Argument(..., help="Book ID"),
    chapter_id: int = typer.Argument(..., help="Chapter ID"),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown, json"
    ),
):
    """
    Render chapter tables as readable markdown.

    Fetches table attachments and converts the HTML to markdown tables.
    Use --format json for raw JSON output (same as 'attachments --type table --format json').
    """
    try:
        with WHOAPIClient() as client:
            rprint(
                f"[bold blue]Fetching tables for chapter {chapter_id} in book {book_id}...[/bold blue]"
            )

            # Verify book and get title
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            # Get chapter ancestors for context
            try:
                ancestors = client.get_chapter_ancestors(book_id, chapter_id)
                chapter_title = (
                    ancestors[-1].chapterTitle if ancestors else "Unknown Chapter"
                )
            except Exception:
                chapter_title = f"Chapter {chapter_id}"

            all_attachments = client.get_attachments(book_id, chapter_id)
            table_attachments = [a for a in all_attachments if a.is_table]

            if not table_attachments:
                rprint(f"[yellow]No tables found for chapter {chapter_id}[/yellow]")
                raise typer.Exit(0)

            rprint(
                f"[green]Found {len(table_attachments)} tables for '{chapter_title}' in '{book.bookTitle}'[/green]\n"
            )

            if format.lower() == "json":
                import json

                attachments_data = [a.model_dump() for a in table_attachments]
                console.print_json(json.dumps(attachments_data))
            else:
                # Markdown format (default)
                for i, attachment in enumerate(table_attachments):
                    if i > 0:
                        console.print("")

                    title = attachment.clean_title or f"Table {i + 1}"
                    console.print(f"[bold cyan]### {title}[/bold cyan]")
                    console.print("")

                    md = attachment.table_markdown
                    if md:
                        console.print(md)
                    else:
                        console.print("[dim](table could not be converted)[/dim]")

                    if attachment.clean_source:
                        console.print(f"\n[dim]Source: {attachment.clean_source}[/dim]")

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch tables: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def download_images(
    book_id: int = typer.Argument(..., help="Book ID"),
    chapter_id: int = typer.Argument(..., help="Chapter ID"),
    output_dir: str = typer.Option(
        ".", "--output", "-o", help="Output directory for downloaded images"
    ),
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing files"
    ),
):
    """
    Download all regular figure images from a chapter.

    Downloads only regular figures (.jpg format) to the specified directory.
    WSI (whole slide images) are automatically skipped as they use DeepZoom format (.dzi)
    which requires special handling. Tables are also skipped.

    Images are saved as: {output_dir}/{fileId}.jpg
    """
    try:
        with WHOAPIClient() as client:
            rprint(
                f"[bold blue]Downloading images from chapter {chapter_id} in book {book_id}...[/bold blue]"
            )

            # Verify book and get title
            try:
                book = client.get_book(book_id)
            except Exception:
                rprint(f"[bold red]Book with ID {book_id} not found[/bold red]")
                raise typer.Exit(1) from None

            # Get chapter title for context
            try:
                ancestors = client.get_chapter_ancestors(book_id, chapter_id)
                chapter_title = (
                    ancestors[-1].chapterTitle if ancestors else "Unknown Chapter"
                )
            except Exception:
                chapter_title = f"Chapter {chapter_id}"

            rprint(f"[dim]Book: {book.bookTitle}[/dim]")
            rprint(f"[dim]Chapter: {chapter_title}[/dim]")
            rprint(f"[dim]Output: {output_dir}[/dim]\n")

            # Download images
            stats = client.download_chapter_images(
                book_id, chapter_id, output_dir, overwrite=overwrite
            )

            # Display results
            rprint("\n[bold green]Download Complete![/bold green]")
            rprint(f"[green]✓ Downloaded: {stats['downloaded']} figures[/green]")

            if stats["skipped_wsi"] > 0:
                rprint(
                    f"[yellow]⊘ Skipped: {stats['skipped_wsi']} WSI (DeepZoom format not supported)[/yellow]"
                )

            if stats["skipped_tables"] > 0:
                rprint(f"[yellow]⊘ Skipped: {stats['skipped_tables']} tables[/yellow]")

            if stats["errors"] > 0:
                rprint(f"[red]✗ Errors: {stats['errors']} failed downloads[/red]")

            if stats["downloaded"] == 0:
                rprint(
                    "\n[yellow]No figures were downloaded. This chapter may only contain WSI or tables.[/yellow]"
                )
                rprint(
                    "[dim]Use 'who-api-client attachments' to see all attachment types.[/dim]"
                )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to download images: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def login(
    email: str = typer.Option(None, "--email", "-e", help="WHO account email"),
    password: str = typer.Option(None, "--password", "-p", help="WHO account password"),
    use_keyring: bool = typer.Option(
        False,
        "--use-keyring",
        help="Save credentials to system keyring instead of config file",
    ),
    save_to_env: bool = typer.Option(
        False,
        "--save-to-env",
        help="Save credentials to .env file in current directory",
    ),
):
    """
    Authenticate with WHO API and save credentials.

    If email/password are not provided, you'll be prompted interactively.
    Credentials are encrypted and saved to ~/.config/who-api-client/ by default.
    """
    cred_manager = CredentialManager()

    # Interactive prompts if not provided
    if not email:
        email = typer.prompt("WHO Email")

    if not password:
        password = getpass.getpass("WHO Password: ")

    # Test credentials by attempting authentication
    rprint("[bold blue]Testing credentials...[/bold blue]")

    try:
        with WHOAPIClient() as client:
            # Temporarily set credentials for testing
            import os

            os.environ["WHO_EMAIL"] = email
            os.environ["WHO_PASSWORD"] = password

            # Try to authenticate
            client._authenticate()

            # Determine storage backend
            if save_to_env:
                backend = "env_file"
                storage_label = ".env file"
            elif use_keyring:
                backend = "keyring"
                storage_label = "system keyring"
            else:
                backend = "config_file"
                from .credentials import _get_credentials_file

                storage_label = f"config file ({_get_credentials_file()})"

            rprint(f"[bold blue]Saving credentials to {storage_label}...[/bold blue]")

            cred_manager.save_credentials(email, password, backend=backend)
            rprint(
                "[bold green]✓ Successfully authenticated and saved credentials![/bold green]"
            )
            rprint(f"[dim]Credentials stored in: {storage_label}[/dim]")

            # Clear temporary environment variables
            del os.environ["WHO_EMAIL"]
            del os.environ["WHO_PASSWORD"]

    except AuthenticationError as e:
        rprint(f"[bold red]Authentication failed: {e}[/bold red]")
        rprint("[dim]Please check your email and password and try again.[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def logout(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
):
    """Remove stored WHO API credentials."""
    cred_manager = CredentialManager()

    if debug:
        info = cred_manager.debug_info()
        rprint("[bold cyan]Debug Information:[/bold cyan]")
        for key, value in info.items():
            rprint(f"  {key}: {value}")

    if not cred_manager.has_credentials():
        rprint("[yellow]No credentials found to remove.[/yellow]")
        raise typer.Exit(0)

    source = cred_manager.get_credential_source()

    if source == "environment variables":
        rprint(
            f"[yellow]Credentials are stored in {source}. Please remove them manually.[/yellow]"
        )
    elif source == ".env file":
        rprint(
            f"[yellow]Credentials are stored in {source}. Please remove them manually.[/yellow]"
        )
        rprint(
            "[dim]You can delete the WHO_EMAIL and WHO_PASSWORD lines from your .env file.[/dim]"
        )
    else:
        confirm = typer.confirm("Are you sure you want to remove stored credentials?")
        if confirm:
            try:
                cred_manager.clear_credentials()
                rprint("[bold green]✓ Credentials removed.[/bold green]")
            except RuntimeError as e:
                rprint(f"[bold red]Failed to remove credentials: {e}[/bold red]")
                raise typer.Exit(1) from None
        else:
            rprint("[yellow]Logout cancelled.[/yellow]")


@app.command()
def status():
    """Check authentication status and credential source."""
    cred_manager = CredentialManager()

    if not cred_manager.has_credentials():
        rprint("[bold red]✗ No credentials found[/bold red]")
        rprint("\n[dim]To authenticate, run:[/dim]")
        rprint("  [cyan]who-api-client login[/cyan]")
        raise typer.Exit(1)

    source = cred_manager.get_credential_source()
    email, _ = cred_manager.get_credentials()

    rprint("[bold green]✓ Credentials found[/bold green]")
    rprint(f"[bold]Email:[/bold] {email}")
    rprint(f"[bold]Source:[/bold] {source}")

    # Test authentication
    rprint("\n[bold blue]Testing authentication...[/bold blue]")

    try:
        with WHOAPIClient() as client:
            # This will trigger authentication
            book_series = client.get_book_series()
            rprint("[bold green]✓ Authentication successful![/bold green]")
            rprint(
                f"[dim]Connected to WHO API - found {book_series.count} book series[/dim]"
            )
    except AuthenticationError as e:
        rprint(f"[bold red]✗ Authentication failed: {e}[/bold red]")
        rprint(
            "[dim]Your credentials may be incorrect or expired. Try logging in again.[/dim]"
        )
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]✗ Connection error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command("profile")
def profile(
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
):
    """
    Get user profile and subscription details for the current authenticated user.
    """
    try:
        with WHOAPIClient() as client:
            rprint("[bold blue]Fetching current user details...[/bold blue]")

            user = client.get_user_details()

            if format.lower() == "json":
                # Output as JSON
                console.print_json(user.model_dump_json())
            else:
                # Table format
                table = Table(
                    title=f"User Details: {user.name}",
                    show_header=True,
                    header_style="bold cyan",
                    title_style="bold blue",
                )
                table.add_column("Field", style="cyan", no_wrap=True)
                table.add_column("Value", style="white")

                # Basic info
                table.add_row("Email", user.email)
                table.add_row("Name", user.name)
                table.add_row("Title", user.title)
                table.add_row("User ID", str(user.pkuserId))

                # Add separator
                table.add_row("", "")

                # Professional info
                table.add_row("Position", user.currentPosition)
                table.add_row("Department", user.department)
                table.add_row("Institution", user.institution)
                table.add_row("City", f"{user.city}, {user.country}")
                table.add_row("Zip Code", user.zipcode)

                # Add separator
                table.add_row("", "")

                # Subscription info
                table.add_row("Subscription Start", user.subscriptionStartDate)
                table.add_row("Subscription End", user.subscriptionEndDate)
                table.add_row("Expires In", user.subscriptionEndsin)
                table.add_row("Is Renewal", "Yes" if user.isRenewal else "No")
                table.add_row(
                    "Profile Updated", "Yes" if user.isProfileUpdated else "No"
                )

                console.print(table)

                # Show renewal URL if subscription is expiring soon
                if user.subscriptionRenewalUrl and "day(s)" in user.subscriptionEndsin:
                    days = int(user.subscriptionEndsin.split()[0])
                    if days < 30:
                        rprint(
                            f"\n[bold yellow]⚠️  Your subscription expires in {days} days![/bold yellow]"
                        )
                        rprint(f"[dim]Renewal URL: {user.subscriptionRenewalUrl}[/dim]")

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        raise typer.Exit(1) from None
    except AuthenticationError as e:
        rprint(f"[bold red]Authentication error: {e}[/bold red]")
        rprint("[dim]Try running 'who-api-client login' to authenticate first.[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command("favourites")
def favourites(
    format: str = typer.Option(
        "tree", "--format", "-f", help="Output format: tree, table, list, json"
    ),
    sort: str = typer.Option("book", "--sort", "-s", help="Sort by: book, chapter"),
):
    """
    Display all favourite chapters grouped by book.

    Shows your saved favourite chapters from the WHO Classification system.
    Use the web interface to add/remove favourites, or use the API directly.
    """
    try:
        with WHOAPIClient() as client:
            rprint("[bold blue]Fetching your favourite chapters...[/bold blue]")

            favourite_books = client.get_favourites()

            if not favourite_books:
                rprint("[yellow]You don't have any favourite chapters yet.[/yellow]")
                rprint(
                    "[dim]Add favourites through the WHO Classification web interface.[/dim]"
                )
                raise typer.Exit(0)

            # Count total favourites
            total_chapters = sum(len(book.chapters) for book in favourite_books)
            rprint(
                f"[green]Found {total_chapters} favourite chapters across {len(favourite_books)} books[/green]\n"
            )

            if format.lower() == "json":
                # Output as JSON
                import json

                favourites_data = [book.model_dump() for book in favourite_books]
                console.print_json(json.dumps(favourites_data))

            elif format.lower() == "tree":
                # Tree format (default)
                tree = Tree("[bold blue]📚 Favourite Chapters[/bold blue]")

                for book in favourite_books:
                    book_node = tree.add(
                        f"[bold cyan]{book.bookTitle}[/bold cyan] [dim](ID: {book.bookId})[/dim]"
                    )

                    # Sort chapters if requested
                    chapters = book.chapters
                    if sort == "chapter":
                        chapters = sorted(chapters, key=lambda c: c.chapterTitle or "")

                    for chapter in chapters:
                        book_node.add(
                            f"[yellow]📖[/yellow] {chapter.chapterTitle} [dim](ID: {chapter.chapterId})[/dim]"
                        )

                console.print(tree)

            elif format.lower() == "table":
                # Table format
                table = Table(
                    title="Favourite Chapters",
                    show_header=True,
                    header_style="bold cyan",
                    title_style="bold blue",
                )
                table.add_column("Book", style="cyan", no_wrap=False)
                table.add_column("Chapter", style="yellow", no_wrap=False)
                table.add_column("Book ID", style="dim", width=8)
                table.add_column("Chapter ID", style="dim", width=10)

                for book in favourite_books:
                    for i, chapter in enumerate(book.chapters):
                        # Only show book title on first row for each book
                        book_title = book.bookTitle if i == 0 else ""
                        book_id = str(book.bookId) if i == 0 else ""

                        table.add_row(
                            book_title,
                            chapter.chapterTitle or "Untitled",
                            book_id,
                            str(chapter.chapterId),
                        )

                    # Add separator between books (except after last book)
                    if book != favourite_books[-1]:
                        table.add_row("", "", "", "")

                console.print(table)

            else:  # list format
                # Simple list format
                for book in favourite_books:
                    console.print(
                        f"\n[bold cyan]{book.bookTitle}[/bold cyan] [dim](Book ID: {book.bookId})[/dim]"
                    )
                    console.print("[dim]" + "─" * 60 + "[/dim]")

                    for chapter in book.chapters:
                        console.print(
                            f"  • {chapter.chapterTitle} [dim](Chapter ID: {chapter.chapterId})[/dim]"
                        )

            # Show tip about managing favourites
            console.print(
                "\n[dim]💡 Tip: Use the WHO Classification web interface to add or remove favourites.[/dim]"
            )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        raise typer.Exit(1) from None
    except AuthenticationError as e:
        rprint(f"[bold red]Authentication error: {e}[/bold red]")
        rprint("[dim]Try running 'who-api-client login' to authenticate first.[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to fetch favourites: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command("favorites")
def favorites(
    format: str = typer.Option(
        "tree", "--format", "-f", help="Output format: tree, table, list, json"
    ),
    sort: str = typer.Option("book", "--sort", "-s", help="Sort by: book, chapter"),
):
    """
    Display all favorite chapters grouped by book (alias for favourites).

    Shows your saved favorite chapters from the WHO Classification system.
    Use the web interface to add/remove favorites, or use the API directly.
    """
    # Just call the favourites function
    favourites(format=format, sort=sort)


@app.command()
def search(
    query: str = typer.Argument(
        ..., help="Search text to find in WHO Classification content"
    ),
    book_ids: str = typer.Option(
        None,
        "--books",
        "-b",
        help="Comma-separated book IDs to search in (default: all books)",
    ),
    include_chapters: bool = typer.Option(
        True,
        "--chapters/--no-chapters",
        help="Include chapter-level results (default: True)",
    ),
    include_headings: bool = typer.Option(
        False,
        "--headings/--no-headings",
        help="Include chapter heading results (default: False)",
    ),
    include_content: bool = typer.Option(
        False,
        "--content/--no-content",
        help="Include chapter content results (default: False)",
    ),
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, list, json"
    ),
    max_results: int = typer.Option(
        50, "--max-results", "-m", help="Maximum number of results to display"
    ),
):
    """
    Search for text across WHO Classification content.

    This performs a simple text search across chapters, headings, and/or content.
    For advanced searches with boolean logic, use the Python API directly.

    Examples:
      who-api-client search "adenocarcinoma"
      who-api-client search "carcinoma" --books 31,32 --headings --content
      who-api-client search "melanoma" --no-chapters --headings --content
    """
    try:
        with WHOAPIClient() as client:
            # Parse book IDs if provided
            parsed_book_ids = None
            if book_ids:
                try:
                    parsed_book_ids = [
                        int(book_id.strip()) for book_id in book_ids.split(",")
                    ]
                except ValueError:
                    rprint(
                        "[bold red]Error: Book IDs must be comma-separated integers[/bold red]"
                    )
                    rprint("Example: --books 31,32,48")
                    raise typer.Exit(1) from None

            # Validate that at least one include option is enabled
            if not any([include_chapters, include_headings, include_content]):
                rprint(
                    "[bold red]Error: At least one search option must be enabled[/bold red]"
                )
                rprint("Use --chapters, --headings, and/or --content")
                raise typer.Exit(1) from None

            rprint(f"[bold blue]Searching for '{query}'...[/bold blue]")

            # Show search scope
            scope_parts = []
            if include_chapters:
                scope_parts.append("chapters")
            if include_headings:
                scope_parts.append("headings")
            if include_content:
                scope_parts.append("content")

            book_scope = (
                f"books {', '.join(map(str, parsed_book_ids))}"
                if parsed_book_ids
                else "all books"
            )
            rprint(
                f"[dim]Searching in {', '.join(scope_parts)} across {book_scope}[/dim]"
            )

            # Perform search
            results = client.search(
                search_text=query,
                book_ids=parsed_book_ids,
                include_chapter=include_chapters,
                include_chapter_heading=include_headings,
                include_chapter_content=include_content,
            )

            if not results.results:
                rprint(f"[yellow]No results found for '{query}'[/yellow]")
                rprint(
                    "[dim]Try different search terms or enable more search options[/dim]"
                )
                raise typer.Exit(0)

            # Limit results if requested
            display_results = results.results[:max_results]
            total_results = len(results.results)

            rprint(f"[green]Found {total_results} results![/green]")
            if total_results > max_results:
                rprint(
                    f"[dim]Showing first {max_results} results (use --max-results to change)[/dim]"
                )

            if format.lower() == "json":
                # Output as JSON
                import json

                results_data = [result.model_dump() for result in display_results]
                console.print_json(json.dumps(results_data))
            elif format.lower() == "list":
                # Simple list format
                for i, result in enumerate(display_results):
                    console.print(f"\n[bold cyan]Result {i + 1}[/bold cyan]")
                    console.print(f"[bold]Title:[/bold] {result.title}")
                    console.print(f"[bold]Book ID:[/bold] {result.bookId}")
                    console.print(f"[bold]Chapter ID:[/bold] {result.chapterId}")
                    if result.headingId > 0:
                        console.print(f"[bold]Heading ID:[/bold] {result.headingId}")
                    console.print(f"[bold]Ranking:[/bold] {result.ranking}")
                    if result.searchedString:
                        console.print(
                            f"[bold]Matched Text:[/bold] {result.searchedString}"
                        )
            else:
                # Table format (default)
                table = Table(
                    title=f"Search Results for '{query}' ({len(display_results)} of {total_results} shown)",
                    show_header=True,
                    header_style="bold cyan",
                    title_style="bold blue",
                )
                table.add_column("Title", style="white", no_wrap=False, min_width=40)
                table.add_column("Book", style="green", width=6)
                table.add_column("Chapter", style="yellow", width=8)
                table.add_column("Heading", style="cyan", width=8)
                table.add_column("Ranking", style="magenta", width=8)

                for result in display_results:
                    # Truncate long titles for table display
                    title = result.title
                    if len(title) > 80:
                        title = title[:77] + "..."

                    table.add_row(
                        title,
                        str(result.bookId),
                        str(result.chapterId),
                        str(result.headingId) if result.headingId > 0 else "-",
                        f"{result.ranking:.1f}" if result.ranking > 0 else "-",
                    )

                console.print(table)

            # Show usage tip
            if total_results > 0:
                console.print(
                    "\n[dim]💡 Tip: Use 'who-api-client content <book_id> <chapter_id>' to view chapter content[/dim]"
                )

    except ConfigurationError as e:
        rprint(f"[bold red]Configuration error: {e}[/bold red]")
        rprint("\n[bold yellow]First time using who-api-client?[/bold yellow]")
        rprint("Run: [cyan]who-api-client login[/cyan] to set up your credentials")
        rprint("\n[dim]Or set WHO_EMAIL and WHO_PASSWORD in your .env file[/dim]")
        raise typer.Exit(1) from None
    except AuthenticationError as e:
        rprint(f"[bold red]Authentication error: {e}[/bold red]")
        rprint("[dim]Try running 'who-api-client login' to authenticate first.[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[bold red]Failed to perform search: {e}[/bold red]")
        raise typer.Exit(1) from e


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
