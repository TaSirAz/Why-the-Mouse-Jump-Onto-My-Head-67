"""Fetch a public independent photo fixture for packaged semantic-inference checks."""
from pathlib import Path
import urllib.request

url = 'https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/sample_data/grace_hopper.jpg'
target = Path('work/inference-photo.jpg')
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(urllib.request.urlopen(url, timeout=30).read())
print('Independent photographic fixture ready for package inference check.')
