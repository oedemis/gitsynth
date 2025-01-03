from pathlib import Path
import json
import subprocess
import webbrowser
import time
from watchfiles import watch
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich.syntax import Syntax

console = Console()
HOST = "192.168.0.87"  # Deine IP

def update_display(layout, test_output):
    """Update the live display with test results"""
    try:
        # Parse test output
        test_results = []
        current_test = None
        
        for line in test_output.split('\n'):
            if '::test_' in line:
                current_test = line.split('::')[-1].split()[0]
                status = '[green]PASSED[/green]' if 'PASSED' in line else '[red]FAILED[/red]'
                test_results.append(f"\n{current_test}: {status}")
            elif current_test and 'assert' in line:
                test_results.append(f"  └─ {line.strip()}")
            elif current_test and any(x in line for x in ['Creating', 'Structuring', 'Generating']):
                test_results.append(f"  └─ [yellow]{line.strip()}[/yellow]")
        
        # Update test panel
        layout["tests"].update(Panel(
            "\n".join(test_results) if test_results else "Waiting for tests...",
            title="[bold]Test Progress[/bold]",
            border_style="blue"
        ))
        
        # Show current test details
        if current_test:
            layout["output"].update(Panel(
                f"[bold]{current_test}[/bold]\n\n{test_output}",
                title="[bold]Current Test Output[/bold]",
                border_style="yellow"
            ))
            
    except Exception as e:
        console.print(f"[red]Error updating display: {e}[/red]")

def run_tests():
    """Run tests with live reporting"""
    result = subprocess.run([
        "pytest",
        "gitsynth/tests/test_llm_handler.py",
        "--html=reports/report.html",
        "-vv",
        "--capture=tee-sys",
        "--show-capture=all",
        "-s"
    ], capture_output=True, text=True)
    
    # Extrahiere OllamaHandler Output
    current_test = None
    test_outputs = {}
    collecting_analysis = False
    
    for line in result.stdout.split('\n'):
        if '::test_' in line:
            current_test = line.split('::')[-1].split()[0]
            test_outputs[current_test] = {
                'test_name': current_test,
                'steps': [],
                'assertions': [],
                'complete_analysis': []
            }
        
        if current_test:
            # Sammle Complete Analysis Output
            if "=== Complete Analysis Output ===" in line:
                collecting_analysis = True
                continue
            elif "===========================" in line:
                collecting_analysis = False
                continue
            elif collecting_analysis:
                test_outputs[current_test]['complete_analysis'].append(line.strip())
            
            # Sammle andere Outputs
            if 'Creating technical analysis...' in line:
                test_outputs[current_test]['steps'].append(line.strip())
            elif 'assert' in line:
                test_outputs[current_test]['assertions'].append(line.strip())
    
    # HTML Report
    test_details = []
    for test_name, data in test_outputs.items():
        details = (
            '<div class="test-case">'
            f'<h3>{test_name}</h3>'
            '<div class="steps">'
            '<h4>Test Steps:</h4>'
            f'<pre class="steps">{chr(10).join(data["steps"])}</pre>'
            '</div>'
            '<div class="complete-analysis">'
            '<h4>Complete Analysis Output:</h4>'
            f'<pre class="analysis">{chr(10).join(data["complete_analysis"])}</pre>'
            '</div>'
            '<div class="assertions">'
            '<h4>Failed Assertions:</h4>'
            f'<pre class="assertions">{chr(10).join(data["assertions"])}</pre>'
            '</div>'
            '</div>'
        )
        test_details.append(details)
    
    # Update HTML mit besserer Formatierung
    ollama_section = (
        '<style>'
        '.test-case { margin: 20px 0; padding: 20px; background: #1e1e1e; color: #d4d4d4; }'
        '.steps { color: #569cd6; }'
        '.commit-type { color: #4ec9b0; }'
        '.commit-message { color: #ce9178; }'
        '.raw-analysis { color: #9cdcfe; }'
        '.analysis { color: #dcdcaa; }'
        '.error { color: #f44747; }'
        '.assertions { color: #6a9955; }'
        'pre { margin: 5px 0; padding: 10px; background: #2d2d2d; white-space: pre-wrap; }'
        'h4 { color: #c586c0; }'
        '</style>'
        '<div class="ollama-details">'
        '<h2>Test Details with analyze_diff() Outputs</h2>'
        f'{"".join(test_details)}'
        '</div>'
    )
    
    with open("reports/report.html", "r") as f:
        html = f.read()
    html = html.replace('</body>', f'{ollama_section}</body>')
    with open("reports/report.html", "w") as f:
        f.write(html)
    
    return result.stdout

def start_browser():
    """Start browser with live reload"""
    from livereload import Server
    server = Server()
    server.watch("reports/report.html")
    url = f"http://{HOST}:5500/report.html"
    
    with open("reports/report.html", "w") as f:
        f.write("""
        <html>
        <head>
            <meta http-equiv="refresh" content="1">
            <title>Test Results</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .status { 
                    padding: 10px; 
                    background: #f0f0f0;
                    border-radius: 5px;
                    margin: 10px 0;
                }
                .ollama-output {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    overflow-x: auto;
                }
                .ollama-output pre {
                    white-space: pre-wrap;
                }
            </style>
        </head>
        <body>
            <div class="status">Auto-refreshing every second...</div>
            <h1>Waiting for tests to start...</h1>
        </body>
        </html>
        """)
    
    # Open browser after short delay
    time.sleep(1)
    webbrowser.open(url)
    
    # Start server
    server.serve(root="reports", port=5500, host=HOST)

def main():
    """Main entry point"""
    console.print("[yellow]Starting test watcher...[/yellow]")
    
    # Create reports dir
    Path("reports").mkdir(exist_ok=True)
    
    # Setup layout
    layout = Layout()
    layout.split_column(
        Layout(name="tests", ratio=2),
        Layout(name="output", ratio=1)
    )
    
    # Initialize display
    layout["tests"].update(Panel("Waiting for tests...", title="[bold]Tests[/bold]"))
    layout["output"].update(Panel("", title="[bold]Output[/bold]"))
    
    # Start browser in background
    import threading
    browser_thread = threading.Thread(target=start_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start watching with live display
    with Live(layout, refresh_per_second=4):
        # Wait for server
        time.sleep(2)
        console.print("[yellow]Running initial tests...[/yellow]")
        
        # Run initial tests
        test_output = run_tests()
        update_display(layout, test_output)
        
        # Watch for changes
        for changes in watch("gitsynth"):
            console.print(f"[yellow]Changes detected, running tests...[/yellow]")
            test_output = run_tests()
            update_display(layout, test_output)

if __name__ == "__main__":
    main()