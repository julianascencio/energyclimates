"""Build a portable source+website ZIP without credentials, raw archives or self-recursion."""
from pathlib import Path
import shutil
import zipfile

root=Path(__file__).resolve().parents[1]
dest=root/'atlas/downloads/energyclimates-software.zip'
shutil.copy(root/'README.md',root/'atlas/downloads/README.md')
shutil.copy(root/'docs/ENGINE_GUIDE.md',root/'atlas/downloads/ENGINE_GUIDE.md')
shutil.copy(root/'examples/monthly-climate.csv',root/'atlas/downloads/monthly-climate.csv')
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
    paths=[root/'README.md',root/'pyproject.toml',root/'LICENSE',root/'NOTICE',root/'DATA_LICENSES.md',root/'CONTRIBUTING.md',root/'CITATION.cff',root/'.gitignore',root/'.gitattributes']
    for folder in ['.github','energyclimates','kgpv','tests','docs','configs','scripts','examples','atlas']:
        paths+=list((root/folder).rglob('*'))
    for p in sorted(set(paths)):
        if not p.is_file() or p==dest or '__pycache__' in p.parts or p.suffix=='.pyc':continue
        if p.parent==root/'atlas/data' and p.suffix in ['.bin','.png']:continue
        z.write(p,'energyclimates/'+str(p.relative_to(root)))
print(f'Packaged {dest.stat().st_size:,} bytes')
