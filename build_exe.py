"""Build a compact, offline Windows executable: python build_exe.py."""
from pathlib import Path
import PyInstaller.__main__

root = Path(__file__).resolve().parent
PyInstaller.__main__.run([
    str(root / 'app.py'), '--noconfirm', '--clean', '--onefile', '--windowed',
    '--name', 'Lina-Sjalvtest', '--optimize', '2',
    '--distpath', str(root / 'dist'), '--workpath', str(root / 'build'),
    '--specpath', str(root), '--add-data', f'{root / "questions.json"};.',
    # Local PDF reading needs no TLS. hashlib uses Python's bundled hash
    # implementations when the optional OpenSSL accelerator is unavailable.
    '--exclude-module', '_ssl', '--exclude-module', '_hashlib',
    '--exclude-module', 'unittest', '--exclude-module', 'doctest',
    '--exclude-module', 'pydoc', '--exclude-module', 'test',
    '--exclude-module', 'idlelib',
])
