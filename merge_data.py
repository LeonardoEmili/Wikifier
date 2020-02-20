from shutil import copyfileobj
import glob
import json
import os
import random
from tqdm import tqdm
import bz2

# This simple script simply performs a merge operation from files located in 'data/' directory

def store_as_file(data, out_filename):
    print("Generating {} ...".format(out_filename + ".bz2"), end=" ", flush=True)
    with open(out_filename, "w") as f_out:
        json.dump(data, f_out)

    with open(out_filename, "rb") as f_in:
        with bz2.BZ2File(out_filename + ".bz2", "wb", compresslevel=9) as f_out:
            copyfileobj(f_in, f_out)

    os.remove(out_filename)
    print("DONE", flush=True)


files = glob.glob("data/*.json")
random.shuffle(files)
training_set_size = int(0.7 * len(files))
test_set_size = int(0.15 * len(files))
validation_set_size = len(files) - training_set_size - test_set_size

training_set = []
test_set = []
validation_set = []

print("Parsing input files ...\n", flush=True)

for i in tqdm(range(len(files))):
    f_in = files[i]
    with open(f_in, "r") as json_f:
        if (i < training_set_size):
            training_set.append(json.load(json_f))
        elif (i < training_set_size + test_set_size):
            test_set.append(json.load(json_f))
        else:
            validation_set.append(json.load(json_f))

print(flush=True)
store_as_file(training_set, "training_set.json")
store_as_file(test_set, "test_set.json")
store_as_file(validation_set, "validation_set.json")