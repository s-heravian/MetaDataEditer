import urllib.request
import re
import zipfile
import os
import shutil

html = urllib.request.urlopen('https://exiftool.org/').read().decode('utf-8')
match = re.search(r'href\s*=\s*[\'"](exiftool-\d+\.\d+\.zip)[\'"]', html)
if match:
    url = 'https://exiftool.org/' + match.group(1)
    print("Downloading:", url)
    urllib.request.urlretrieve(url, 'exiftool.zip')
    print('Downloaded. Extracting...')
    
    with zipfile.ZipFile('exiftool.zip', 'r') as zip_ref:
        zip_ref.extractall('exiftool_dir')
        
    for root, dirs, files in os.walk('exiftool_dir'):
        for file in files:
            if file.startswith('exiftool') and file.endswith('.exe'):
                exe_path = os.path.join(root, file)
                shutil.move(exe_path, os.path.join('backend', 'exiftool.exe'))
                print("ExifTool executable moved to backend.")
                break
                
    # Cleanup
    os.remove('exiftool.zip')
    shutil.rmtree('exiftool_dir')
    print('Done.')
else:
    print('Could not find download link on the page.')
