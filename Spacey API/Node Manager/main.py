import sys
from os.path import dirname as dir
parentdir = dir(dir(__file__))
sys.path.insert(0,parentdir) 
from admin_map_creator import main
 
if __name__ == "__main__":
    main()  