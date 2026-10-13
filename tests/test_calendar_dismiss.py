import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_calendar_dismiss_ignores_forms_and_controls_but_clears_blank_clicks():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is needed to execute the calendar event handler")
    tree = ast.parse((Path(__file__).parents[1] / "ui/entry_calendar.py").read_text())
    call = next(item for item in ast.walk(tree) if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "component")
    javascript = ast.literal_eval(next(item.value for item in call.keywords if item.arg == "js"))
    script = """
const listeners = {};
global.document = {addEventListener: (name, fn) => listeners[name] = fn, removeEventListener: () => {}};
let cleared = 0;
const initialize = new Function('return (' + SOURCE.replace('export default function', 'function') + ')')();
initialize({data: {selected: true}, setTriggerValue: () => cleared++});
for (const element of ['input', 'textarea', 'select', 'button', 'label', 'summary', '[data-testid="stForm"]']) {
    listeners.click({composedPath: () => [{matches: selector => selector.includes(element)}]});
}
if (cleared !== 0) throw Error('Form interactions must not trigger reruns');
listeners.click({composedPath: () => [{classList: {contains: name => name === 'st-key-entry_calendar'}}]});
if (cleared !== 0) throw Error('Calendar click must not dismiss');
listeners.click({composedPath: () => [{}]});
if (cleared !== 1) throw Error('Blank click must dismiss');
listeners.keydown({key: 'Escape'});
if (cleared !== 2) throw Error('Escape must dismiss');
""".replace("SOURCE", json.dumps(javascript))
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
