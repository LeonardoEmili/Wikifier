from shutil import copyfileobj
import glob
import json
from tqdm import tqdm
import bz2

# This simple script simply performs a merge operation from files located in 'data/' directory

merge_file = []
files = glob.glob("data/*.json")
out_filename = "raw_data.json"

print("Parsing input files ...\n", flush=True)

for i in tqdm(range(len(files))):
    f_in = files[i]
    with open(f_in, "r") as json_f:
        merge_file.append(json.load(json_f))

print("\nMerging results into {} ...".format(out_filename), end=" ", flush=True)

with open(out_filename, "w") as f_out:
    json.dump(merge_file, f_out)

print("DONE", flush=True)
print("Creating compressed file ...", end=" ", flush=True)

with open(out_filename, "rb") as f_in:
    with bz2.BZ2File(out_filename + ".bz2", "wb", compresslevel=9) as f_out:
        copyfileobj(f_in, f_out)

print("DONE", flush=True)