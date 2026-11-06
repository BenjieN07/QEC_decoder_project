"""Check staged content and optionally local history against local credentials.

Never prints credential contents or matching lines. Does not replace GitHub's
secret scanning; it detects exact local values and common URL encodings.
"""
import argparse
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote,quote_plus
ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL)


def patterns(root):
    values=[]
    for filename in ('api.txt','crn.txt'):
        path=root/filename
        if path.exists():
            value=path.read_text(encoding='utf-8-sig').strip()
            if len(value)<16:raise ValueError('Credential file is too short to validate safely')
            values.extend(s.encode() for s in {value,quote(value,safe=''),quote_plus(value,safe='')})
    return values


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--history',action='store_true')
    parser.add_argument('--all-local',action='store_true',help='Also inspect private app snapshot refs; never push these refs')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    values=patterns(root)
    tracked=git('ls-files','--','api.txt','crn.txt','.env','.env.*','credentials','secrets','private',':(exclude).env.example').splitlines()
    if tracked:
        print('FAIL: a protected credential path is tracked. No values printed.');sys.exit(1)
    if not values:
        print('Protected paths checked. No local credential values available for exact-value scan.');return
    staged=git('ls-files','--stage','-z').split(b'\0');objects=set()
    for entry in staged:
        if entry:objects.add(entry.split(b'\t',1)[0].split()[1].decode())
    if args.history or args.all_local:
        refs=['--all'] if args.all_local else [line.decode() for line in git('for-each-ref','--format=%(refname)','refs/heads','refs/remotes').splitlines()]
        for line in (git('rev-list','--objects',*refs).splitlines() if refs else []):
            objects.add(line.split(b' ',1)[0].decode())
    # Batch mode avoids invoking a process for each object and never prints content.
    process=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    matches=0;blobs=0
    try:
        for oid in sorted(objects):
            process.stdin.write((oid+'\n').encode());process.stdin.flush()
            header=process.stdout.readline().split()
            if len(header)!=3:raise RuntimeError('Git object could not be inspected')
            length=int(header[2]);data=process.stdout.read(length);process.stdout.read(1)
            if header[1]==b'blob':
                blobs+=1
                if any(value in data for value in values):matches+=1
    finally:
        process.stdin.close();process.stdout.close();process.wait()
    if matches:
        print(f'FAIL: local credential content found in {matches} Git blobs. No values printed.');sys.exit(1)
    print(f'PASS: {blobs} staged/history blobs checked; no local credential values found.')


if __name__=='__main__':main()
