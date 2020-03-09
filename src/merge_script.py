from shutil import copyfileobj
import glob
import os
import random
from tqdm import tqdm
import bz2

# This simple script simply performs a merge operation from files located in 'data/' directory

def store_as_file(data, out_filename):
    print("Generating {} ...".format(out_filename + ".bz2"), end=" ", flush=True)
    
    with open(out_filename, "w") as f_out:
        f_out.write(data)
    with open(out_filename, "rb") as f_in:
        with bz2.BZ2File(out_filename + ".bz2", "wb", compresslevel=9) as f_out:
            copyfileobj(f_in, f_out)

    os.remove(out_filename)
    print("DONE", flush=True)

def generate_input_data():

    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    files = glob.glob("../raw_data/*.txt")
    #random.shuffle(files)
    training_set_size = int(0.7 * len(files))
    test_set_size = int(0.15 * len(files))

    training_set = ""
    test_set = ""
    validation_set = ""

    print("Reading raw files ...\n", flush=True)

    for i in tqdm(range(len(files))):
        f_in = files[i]
        with open(f_in, "r") as f:
            # This is a single file, useless here
            training_set += f.read()
            #if (i < training_set_size):
                #training_set += f.read()
            #elif (i < training_set_size + test_set_size):
                #test_set += f.read()
            #else:
                #validation_set += f.read()

    print(flush=True)
    os.makedirs("../input_data/",0o0755, exist_ok=True)
    store_as_file(training_set, "../input_data/wiki.txt")
    #store_as_file(training_set, "../input_data/train.txt")
    #store_as_file(test_set, "../input_data/test.txt")
    #store_as_file(validation_set, "../input_data/validation.txt")

if __name__ == '__main__':
    generate_input_data()