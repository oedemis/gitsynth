import pytest
from rich.console import Console
from rich.panel import Panel

@pytest.fixture(autouse=True)
def test_output():
    console = Console()
    
    def show_test_output(test_name, output):
        console.print(Panel(
            output,
            title=f"[bold blue]{test_name}[/bold blue]",
            border_style="blue"
        ))
    
    return show_test_output 