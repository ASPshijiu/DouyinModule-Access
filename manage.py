"""本地维护名单；输入的UID不会写入文件或输出。"""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('list', choices=['black', 'white'])
parser.add_argument('action', choices=['add', 'remove'])
args = parser.parse_args()
uid = getpass.getpass('输入抖音UID（隐藏输入）: ')
if not re.fullmatch(r'[1-9][0-9]{0,29}', uid):
    parser.error('UID格式不正确')
key = 'sha256:' + hashlib.sha256(uid.encode()).hexdigest()
path = Path(__file__).parent / 'policies/access.json'
data = json.loads(path.read_text())
assert data['schema'] == 1
name = args.list + 'list'
values = set(data[name])
if args.action == 'add':
    values.add(key)
else:
    values.discard(key)
data[name] = sorted(values)
path.write_text(json.dumps(data, indent=2) + '\n')
print('名单文件已更新；提交并推送后由模块读取。')
