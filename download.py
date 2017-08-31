# coding: utf-8
import logging
import os
import urllib.request
import getopt
import sys

def get_download_url(url):
    '''
    获取跳转后的真实下载链接
    :param url: 页面中的下载链接
    :return: 跳转后的真实下载链接
    '''
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
    response = urllib.request.urlopen(req)
    dlurl = response.geturl()  # 跳转后的真实下载链接
    return dlurl


def download_file(dlurl):
    '''
    从真实的下载链接下载文件
    :param dlurl: 真实的下载链接
    :return: 下载后的文件
    '''
    req = urllib.request.Request(dlurl)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko')
    response = urllib.request.urlopen(req)
    return response.read()


def save_file(dlurl, dlfolder):
    '''
    把下载后的文件保存到下载目录
    :param dlurl: 真实的下载链接
    :param dlfolder: 下载目录
    :return: None
    '''
    # os.chdir(dlfolder)  # 跳转到下载目录
    if not os.path.exists(dlfolder):
        os.makedirs(dlfolder)
    filename = dlfolder+dlurl.split('/')[-1]  # 获取下载文件名
    dlfile = download_file(dlurl)
    with open(filename, 'wb') as f:
        f.write(dlfile)
        f.close()
    return None

def readConfig(path):
    urls = []
    with open(path) as f:
        urls.extend(f.readlines())
    # print("=====",urls)
    return urls

if __name__ == '__main__':
    # 设置log
    LOG_DIR = 'log/'
    dlfolder = 'zip/'  # 下载目录
    LOG_FILE = 'update.log'
    model = "undefined"
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
    print("===== start download logs =====")
    CONFIG_DIR = "config/"
    if not os.path.exists(CONFIG_DIR+model):
        print("===== couldn't find url file =====")
        sys.exit(0)

    print("=====download bbklog of %s =====" %model)
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    open(LOG_DIR+LOG_FILE, 'w')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s',
                        filename=LOG_DIR+LOG_FILE,
                        filemode='a')

    for url in readConfig(CONFIG_DIR+model):
        dlurl = get_download_url(url)  # 真实下载链接
        logging.debug('开始下载...')
        save_file(dlurl, dlfolder+model+"/")  # 下载并保存文件
        logging.debug('下载完毕.')
    print("===== download logs end =====")