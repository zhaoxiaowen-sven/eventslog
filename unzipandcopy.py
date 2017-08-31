# coding: utf-8
import os
import shutil
import zipfile
import time
import getopt
import sys

def un_zip(target_dir, dir_name):
    """unzip zip file"""
    zip_file = zipfile.ZipFile(target_dir)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    for names in zip_file.namelist():
        # print(names)
        zip_file.extract(names, dir_name)
    zip_file.close()


def get_zip_files(target_dir):
    paths = []
    for path, names, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".zip"):
                paths.append(os.path.join(path, f))
    # print(paths)
    return paths


def copy_event_log(unzipdir, target_dir):
    event_log_dir = []
    for root, dirs, files in os.walk(unzipdir):
        for f in files:
            if f == "events_log":
                event_log_dir.append(os.path.join(root, f))
    
    for dir in event_log_dir:
        print(dir)
        imei = (dir.split("IMEI")[1]).split("Version")[0]
        filename = (dir.split("adb_log/")[1]).split(r"/events")[0]
        print(imei, filename)
        temp = target_dir + imei + "/" + filename + "/"
        if not os.path.exists(temp):
            os.makedirs(temp)
        shutil.copy(dir, temp)

def make_need_dirs():
    pass

if __name__ == '__main__':
    time1 = time.time()
    print("=====start unzip and copy=====")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hm:")
        print(sys.argv[0])
    except getopt.GetoptError as e:
        print(e)

    for opt, arg in opts:
        if opt == '-h':
            print("please input -m with a model name")
        elif opt == '-m':
            model = arg

    # model = "PD1635"
    zipdir = "zip/" + model + "/"
    unzipdir = "unzip/" + model + "/"
    if not os.path.exists(zipdir):
        print("couldn't find target zip dir")
        sys.exit(0)

    for x in get_zip_files(zipdir):
        un_zip(x, unzipdir)

    print("=====unzip finished =====")
    copy_event_log(unzipdir, "eventslog/"+model+"/")
    print("spend time %s", time.time() - time1)