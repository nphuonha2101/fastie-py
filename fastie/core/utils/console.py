from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.table import Table

# Define a professional theme for Fastie
fastie_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "brand": "bold magenta",
    "header": "bold white on blue",
})

console = Console(theme=fastie_theme)

class FastieConsole:
    """Centralized console utility for Fastie branding"""
    
    @staticmethod
    def print_banner():
        """Print the Fastie gradient banner"""
        brand_text = Text(" FASTIE FRAMEWORK ", style="bold white")
        brand_text.stylize("italic", 0, 18)
        
        # Create a gradient-like effect using rich colors
        # Cyan -> Sky Blue -> Blue -> Magenta
        gradient_text = Text()
        gradient_text.append("F", style="bold #00f2fe")
        gradient_text.append("a", style="bold #00e5ff")
        gradient_text.append("s", style="bold #00d4ff")
        gradient_text.append("t", style="bold #00c0ff")
        gradient_text.append("i", style="bold #00a8ff")
        gradient_text.append("e", style="bold #0090ff")
        
        console.print(Panel(
            gradient_text,
            subtitle="[dim]The High-Speed FastAPI Framework[/dim]",
            border_style="#00a8ff",
            expand=False,
            padding=(0, 2)
        ))

    @staticmethod
    def success(message: str):
        console.print(f"[success]✅[/success] {message}")

    @staticmethod
    def info(message: str):
        console.print(f"[info]🚀[/info] {message}")

    @staticmethod
    def warning(message: str):
        console.print(f"[warning]⚠️ [/warning] {message}")

    @staticmethod
    def error(message: str):
        console.print(f"[error]❌[/error] {message}")

    @staticmethod
    def step(message: str):
        console.print(f"[brand]📝[/brand] {message}")

    @staticmethod
    def table(title: str, columns: list, rows: list):
        """Display a beautiful table"""
        table = Table(title=title, show_header=True, header_style="bold magenta", border_style="dim")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        console.print(table)

fastie_console = FastieConsole()
