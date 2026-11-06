import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest
from qec_project.ibm_access import public_json


def test_public_output_rejects_private_values():
    secret='dummy_test_credential_value_123456'
    with pytest.raises(ValueError):public_json({'nested':{'value':secret}},[secret])
    assert 'backend' in public_json({'backend':'test_backend'},[secret])


@pytest.mark.parametrize('sensitive',[False,True])
def test_staged_scanner_blocks_secret_without_echoing(tmp_path,sensitive):
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'scripts').mkdir()
    (tmp_path/'scripts/check_secrets.py').write_bytes((root/'scripts/check_secrets.py').read_bytes())
    token='dummy_local_credential_000000000000000'
    (tmp_path/'api.txt').write_text(token)
    (tmp_path/'.gitignore').write_text('/api.txt\n')
    (tmp_path/'payload.txt').write_text(token if sensitive else 'non-sensitive research output')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    subprocess.run(['git','-C',str(tmp_path),'add','payload.txt'],check=True)
    result=subprocess.run([sys.executable,str(tmp_path/'scripts/check_secrets.py'),'--history'],capture_output=True,text=True)
    assert result.returncode==(1 if sensitive else 0)
    assert token not in result.stdout and token not in result.stderr


def test_forced_private_file_is_blocked(tmp_path):
    root=Path(__file__).resolve().parents[1]
    (tmp_path/'scripts').mkdir()
    (tmp_path/'scripts/check_secrets.py').write_bytes((root/'scripts/check_secrets.py').read_bytes())
    token='dummy_local_private_file_00000000000'
    (tmp_path/'api.txt').write_text(token)
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    subprocess.run(['git','-C',str(tmp_path),'add','api.txt'],check=True)
    result=subprocess.run([sys.executable,str(tmp_path/'scripts/check_secrets.py')],capture_output=True,text=True)
    assert result.returncode==1 and 'protected' in result.stdout
    assert token not in result.stdout and token not in result.stderr
