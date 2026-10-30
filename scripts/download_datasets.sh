#!/bin/bash
# Fetch the MyFixit repair-manual dataset (iFixit; Nabizadeh et al., LREC 2020; CC BY-NC-SA 3.0)
set -e
cd "/Users/shivansh/Desktop/proof of repair"
mkdir -p data/raw/MyFixit
BASE=https://raw.githubusercontent.com/rub-ksv/MyFixit-Dataset/master
for f in Phone Appliance "Car%20and%20Truck"; do
  name=$(python3 -c "import urllib.parse,sys;print(urllib.parse.unquote(sys.argv[1]))" "$f")
  curl -sSfL -o "data/raw/MyFixit/$name.json" "$BASE/jsons/$f.json" && echo "ok $name.json"
done
curl -sSfL -o data/raw/MyFixit/README.md "$BASE/README.md"
curl -sSfL -o data/raw/MyFixit/LICENSE "$BASE/LICENSE"
echo "Next: python scripts/prepare_multidomain.py && python scripts/init_db.py"
