from rich import box
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
    """Centralized console utility for Fastie branding (Neo-Brutalism style)"""
    
    @staticmethod
    def print_banner():
        """Print the Fastie Neo-Brutalism banner"""
        # Perfectly aligned 5x5 pixel art logo
        fastie_lines = [
            "█████ █████ █████ █████ █████ █████",
            "█     █   █ █       █     █   █    ",
            "████  █████ █████   █     █   ████ ",
            "█     █   █     █   █     █   █    ",
            "█     █   █ █████   █   █████ █████",
        ]
        
        py_lines = [
            "█████ █   █",
            "█   █  █ █ ",
            "█████   █  ",
            "█       █  ",
            "█       █  ",
        ]
        
        # Combine logo lines
        logo_content = []
        for i in range(5):
            logo_content.append(f" {fastie_lines[i]}   {py_lines[i]} ")

        logo_text = Text("\n".join(logo_content), style="black")
        
        # Logo Panel (Yellow background)
        logo_panel = Panel(
            logo_text,
            title="[bold black] FASTIE-PY [/bold black]",
            title_align="left",
            border_style="black",
            style="on #FFEF00", # Pure Neo-Brutalism Yellow
            box=box.HEAVY,
            padding=(1, 2),
            expand=False
        )
        
        # Info Panel (Cyan background)
        status = Panel(
            Text("FastAPI Bestie • Built by NPHUONHA & Antigravity • v0.0.1a1", style="bold black"),
            style="on #00E5FF", # Pure Neo-Brutalism Cyan
            box=box.SQUARE,
            border_style="black",
            padding=(0, 2),
            expand=False
        )
        
        console.print()
        console.print(logo_panel)
        console.print(status)
        console.print()

    @staticmethod
    def success(message: str):
        console.print(Panel(Text(f" [ DONE ] {message}", style="bold black"), style="on #ADFF2F", box=box.SQUARE, border_style="black", expand=False))

    @staticmethod
    def info(message: str):
        console.print(Panel(Text(f" [ INFO ] {message}", style="bold black"), style="on #00E5FF", box=box.SQUARE, border_style="black", expand=False))

    @staticmethod
    def warning(message: str):
        console.print(Panel(Text(f" [ WAIT ] {message}", style="bold black"), style="on #FFA500", box=box.SQUARE, border_style="black", expand=False))

    @staticmethod
    def error(message: str):
        console.print(Panel(Text(f" [ FAIL ] {message}", style="bold black"), style="on #FF3131", box=box.SQUARE, border_style="black", expand=False))

    @staticmethod
    def step(message: str):
        console.print(f" [bold #FFEF00]›[/bold #FFEF00] [dim white]{message}[/dim white]")

    @staticmethod
    def table(title: str, columns: list, rows: list):
        """Display a Neo-Brutalism style table"""
        table = Table(
            title=f"[bold black on #FFEF00] {title} [/]", 
            show_header=True, 
            header_style="bold black on #00E5FF", 
            border_style="black",
            box=box.HEAVY
        )
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*row)
        console.print(table)

fastie_console = FastieConsole()
