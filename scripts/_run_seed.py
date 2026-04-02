import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    exec(open('scripts/seed_db.py', encoding='utf-8').read())
except Exception as e:
    traceback.print_exc()
    print(f"\nERROR: {e}")
