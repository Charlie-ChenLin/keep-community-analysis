"""Export the 12-minute deck in the background, without opening a GUI app."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STEM = 'Keep社区内容表达与互动反馈_12分钟版'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--soffice', default=os.environ.get('SOFFICE_PATH') or shutil.which('soffice'))
    args = parser.parse_args()
    if not args.soffice:
        parser.error('Set SOFFICE_PATH or pass --soffice to a LibreOffice executable.')
    # A temporary profile and output folder keep the user's open documents and
    # all existing presentation/PDF versions outside this export operation.
    with tempfile.TemporaryDirectory(prefix='keep_12min_render_') as work:
        work = Path(work)
        subprocess.run([
            args.soffice, '-env:UserInstallation=' + (work / 'profile').as_uri(),
            '--headless', '--norestore', '--nodefault', '--nofirststartwizard',
            '--convert-to', 'pdf:impress_pdf_Export', '--outdir', str(work),
            str(ROOT / (STEM + '.pptx')),
        ], check=True, timeout=90, capture_output=True, text=True)
        pdf = work / (STEM + '.pdf')
        if not pdf.is_file():
            raise RuntimeError('Background export did not produce a PDF.')
        shutil.copyfile(pdf, ROOT / (STEM + '.pdf'))
    print(ROOT / (STEM + '.pdf'))


if __name__ == '__main__':
    main()
