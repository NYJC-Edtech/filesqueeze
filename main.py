from typing import Mapping
from pathlib import Path

import compressor
import scan



VIDEO_EXTS = ('.flv', '.avi', '.mkv', '.mov', '.mp4', '.wmv')
SLIDE_EXTS = ('.ppt', '.pptx')
EXTS = set(VIDEO_EXTS + SLIDE_EXTS)



def display(data: Mapping):
    filename = data['origin']
    status = '[' + data['status'].upper() + ']'
    if data['format']:
        format, ext = data['format'].split('.')
        fstr = f'({ext} {format})'
    else:
        fstr = '' 
    print(status, filename, fstr, end='\r')

def run(topdir: str):
    for filepath in scan.walk(
        topdir,
        isvalid=lambda file: Path(file).suffix.lower() in EXTS,
    ):
        outfile = compressor.make_video(filepath, on_update=display)
        print()  # Put linebreak after last display line



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Converts input file(s) to video file(s).")
    parser.add_argument('infile', help='input path or filename')
    args = parser.parse_args()
    
    run(args.infile)