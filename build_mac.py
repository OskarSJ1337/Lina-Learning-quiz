"""Build on macOS with Python + Tkinter installed."""
from pathlib import Path
import sys
import subprocess
import platform

if sys.platform != 'darwin':
    raise SystemExit('Mac-versionen måste byggas på macOS.')
import PyInstaller.__main__
root = Path(__file__).resolve().parent
name = 'Linas självstudie quiz'
PyInstaller.__main__.run([
    str(root / 'app.py'), '--noconfirm', '--clean', '--onedir', '--windowed',
    '--name', name, '--optimize', '2',
    '--distpath', str(root / 'dist'), '--workpath', str(root / 'build-mac'),
    '--specpath', str(root), '--add-data', f'{root / "questions.json"}:.',
    '--osx-bundle-identifier', 'se.linas.sjalvstudiequiz',
    '--exclude-module', 'unittest', '--exclude-module', 'doctest',
    '--exclude-module', 'test', '--exclude-module', 'idlelib',
])
archive = root / 'dist' / f'Linas-quiz-Mac-{platform.machine()}.zip'
subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                str(root / 'dist' / f'{name}.app'), str(archive)], check=True)
print(f'Färdig app att skicka: {archive}')
