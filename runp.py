import subprocess
import sys
from flask import Flask, Response, stream_with_context
import os
import time

app = Flask(__name__)

# Dictionary to hold script names with their options and refresh intervals
script_options = {}

def parse_refresh_argument(arg):
    # Handle refresh argument with optional time suffix (s for seconds, m for minutes, h for hours, d for days)
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    if arg[-1] in units:
        try:
            return int(arg[:-1]) * units[arg[-1]]
        except ValueError:
            return 15  # Default to 15 seconds if parsing fails
    try:
        return int(arg)
    except ValueError:
        return 15  # Default to 15 seconds for non-numeric values

def parse_script_options(argv):
    script_with_options = {}
    current_script = None
    for arg in argv[1:]:  # Skip the script's own name
        if arg.endswith('.py'):
            current_script = arg
            script_with_options[current_script] = {'refresh': False, 'refresh_interval': 15, 'header': False, 'last_run': 0, 'cache': ''}
        elif arg.startswith('--refresh') and current_script:
            refresh_value = arg.split('=')[1] if '=' in arg else '15'  # Default to 15 seconds if no value provided
            script_with_options[current_script]['refresh'] = True
            script_with_options[current_script]['refresh_interval'] = parse_refresh_argument(refresh_value)
        elif arg == '--header' and current_script:
            script_with_options[current_script]['header'] = True
    return script_with_options

script_options = parse_script_options(sys.argv)

@app.route('/output')
def output():
    def generate():
        current_time = time.time()
        for script_name, options in script_options.items():
            if options['header'] and len(script_options) > 1:
                yield f"<h2>{os.path.basename(script_name)}</h2><br>\n"
            
            # Check if cache is valid based on refresh interval
            if current_time - options['last_run'] > options['refresh_interval']:
                process = subprocess.Popen(["python3", script_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                output_cache = ""
                for line in iter(process.stdout.readline, ''):
                    output_cache += line.replace("\n", "<br>\n")
                process.stdout.close()
                process.wait()
                options['cache'] = output_cache
                options['last_run'] = current_time
            yield options['cache']

            if len(script_options) > 1:
                yield "<hr>\n"

    return Response(stream_with_context(generate()), mimetype='text/html')

@app.route('/')
def index():
    refresh_intervals = [options['refresh_interval'] for options in script_options.values() if options['refresh']]
    refresh_interval = min(refresh_intervals) if refresh_intervals else 15  # Default to 15 seconds

    script_loader = f'''
    <script>
        function fetchOutput() {{
            fetch('/output')
                .then(response => response.text())
                .then(data => {{
                    document.getElementById('output').innerHTML = data;
                }})
                .catch(console.error);
        }}
        window.onload = fetchOutput; // Initial load
        setInterval(fetchOutput, {refresh_interval * 1000}); // Reload data based on the shortest refresh interval

        function updateRefreshTime() {{
            const refreshTime = {refresh_interval};
            let remainingTime = refreshTime;
            let countdownElement = document.getElementById('countdown');
            let nextRefreshElement = document.getElementById('nextRefresh');

            function updateCountdown() {{
                countdownElement.innerText = 'Time until next refresh: ' + remainingTime + ' seconds';
                remainingTime--;
                if (remainingTime < 0) {{
                    remainingTime = refreshTime;
                }}
            }}

            updateCountdown(); // Initial update
            setInterval(updateCountdown, 1000); // Update countdown every second

            function updateNextRefreshTime() {{
                let currentTime = new Date();
                let nextRefreshTime = new Date(currentTime.getTime() + remainingTime * 1000);
                nextRefreshElement.innerText = 'Next refresh at: ' + nextRefreshTime.toLocaleTimeString();
            }}

            updateNextRefreshTime(); // Initial update
            setInterval(updateNextRefreshTime, 1000); // Update next refresh time every second
        }}

        updateRefreshTime();
    </script>
    '''

    return f'''
    <html>
        <head>
            <title>Script Outputs</title>
            {script_loader}
            <style>
                #countdown, #nextRefresh {{
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div id="output">Loading...</div>
            <div id="countdown"></div>
            <div id="nextRefresh"></div>
        </body>
    </html>
    '''

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: runp <script_name.py> [--refresh[=interval]] [--header]")
        sys.exit(1)

    app.run(debug=True, host='0.0.0.0', port=5000)
