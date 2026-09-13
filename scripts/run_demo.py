"""Launch the opt-in demo on localhost with isolated, persistent local data."""
import argparse
import os
import secrets
import sys
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--data-dir',type=Path,default=Path('demo-data'))
parser.add_argument('--library',type=Path)
parser.add_argument('--port',type=int,default=8000)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(repo))
data=args.data_dir.resolve();data.mkdir(parents=True,exist_ok=True)
key=data/'.demo-secret'
if not key.exists(): key.write_text(secrets.token_urlsafe(48),encoding='utf-8')
os.environ['SECRET_KEY']=key.read_text(encoding='utf-8').strip()
os.environ['FENIQ_DEMO']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(data/'demo.db')
os.environ['UPLOAD_DIR']=str(data/'photos')
if args.library: os.environ['FENIQ_DOCUMENT_ROOT']=str(args.library.resolve())
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=args.port)
