#!/usr/bin/env python
# coding:utf-8

SCREEN_REPORT = "event_log_screen_results.xlsx"
EXCEPT_REPORT = "event_log_except_results.xlsx"
PROC_REPORT = "event_log_proc_results.xlsx"
RESUME_REPORT = "event_log_resume_results.xlsx"
PSS_REPORT = "event_log_pss_results.xlsx"
KILL_REPORT = "event_log_kill_results.xlsx"
MEM_REPORT = "event_log_mem_results.xlsx"
BATTERY_REPORT = "event_log_battery_results.xlsx"

MB = 1024.0 * 1024.0
DAY = 24 * 60 * 60 * 1000.0
HOUR = 60 * 60 * 1000.0

__author = 'zhaoxiaowen'
import datetime
import getopt
import os
import sqlite3
import sys
import threading
import time
from collections import Counter

import numpy as np
import pandas as pd
import pandas.io.sql as pdsql
import xlsxwriter
from pandas import DataFrame
from parsers import *

top10app = ["com.tencent.mobileqq", "com.qiyi.video", "com.tencent.karaoke", "com.tencent.mm", "com.kugou.android",
            "com.tencent.qqlive", "com.eg.android.AlipayGphone", "com.taobao.taobao", "com.sina.weibo",
            "com.smile.gifmaker"]

top10app2 = top10app + ['0', 'com.bbk.launcher2', 'com.vivo.upslide']

REPORT_PATH = "E:/Project/Pycharm/eventslog/report/"

IMEI_RECORD = []


class ParseThread(threading.Thread):
    def __init__(self, func, args, threadid=0, name=''):
        threading.Thread.__init__(self)
        self.threadid = threadid
        self.name = name
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)


class EventLog:
    def __init__(self, path, prefix_name):
        # print("init")
        self.path = path
        self.prefix_name = prefix_name

    def parse(self, rev=True):
        start_time = time.time()
        end_time = time.time() - start_time
        print("parse files end %.1f s" % end_time)
        # self.make_sheets(results, self.prefix_name)

    def comparetime(self, time1, time2):
        return (parse(time2) - parse(time1)).total_seconds() * 1000

    def parse_files(self):
        filepaths = []
        for dirpath, dirnames, filenames in os.walk(self.path):
            for file in filenames:
                filepaths.append(os.path.join(dirpath, file))
        # print(filepaths)
        for p in filepaths:
            print("======", p, "======")
            # print(p.split('\\'))
            # 这2个参数和log文件夹路径相关
            # eventslog\PD1635\865044030056099\AdbLog_2017_0712_121801_55
            model = p.split('/')[1]
            imei = p.split('/')[2]

            # print(imei, model)
            # return
            # 每个imei 最多只选一条有效数据
            if imei not in IMEI_RECORD:
                resume = {"time": [], "pkg": [], "ui": []}
                mem = {"time": [], "cached": [], "free": [], "zram": [], "kernel": [], "native": []}
                anr = {"time": [], "pkg": []}
                crash = {"time": [], "pkg": []}
                pss = {"time": [], "process": [], "pss": [], "uss": []}
                self.parse_file(p, imei, resume, mem, pss, anr, crash)
                # print(resume)
                if len(resume.get("time")) > 0:
                    df_resume = DataFrame(resume).sort_values(by=["time"])
                    df_resume = pd.concat(
                        [DataFrame({"time": [df_resume.iloc[0].time], "pkg": ["0"], "ui": ["0"]}), df_resume,
                         DataFrame({"time": [df_resume.iloc[-1].time], "pkg": ["0"], "ui": ["0"]})])

                    self.appendImeiModel(df_resume, imei, model, "resume_record")
                    self.insertImei(model, imei)
                    self.make_app_use_time_sql(df_resume, imei, self.prefix_name)
                    self.save_app_switch_tosql(df_resume, imei, model)
                    # self.saveDF2sql(df_resume, "resume_record")
                if len(mem.get("time")) > 0:
                    df_mem = DataFrame(mem).sort_values(by=["time"])
                    self.appendImeiModel(df_mem, imei, model, "mem_record")

                if len(anr.get("time")) > 0:
                    df_anr = DataFrame(anr).sort_values(by=["time"])
                    self.appendImeiModel(df_anr, imei, model, "anr_record")

                if len(crash.get("time")) > 0:
                    df_crash = DataFrame(crash).sort_values(by=["time"])
                    self.appendImeiModel(df_crash, imei, model, "crash_record")
                if len(pss.get("time")) > 0:
                    df_pss = DataFrame(pss).sort_values(by=["time"])
                    self.appendImeiModel(df_pss, imei, model, "pss_record")

    def appendImeiModel(self, df, imei, model, table):
        df["imei"] = imei
        df["model"] = model
        self.saveDF2sql(df, table)

    # 取首页
    def getstart(self, lines, length, t_str):
        for i in range(length):
            if lines[i].startswith(t_str):
                # print(length-i)
                return i
        return length

    # 解析某个文件
    def parse_file(self, path, imei, resume, mem, pss, anr, crash):
        # 多个路径 这里加循环 for path in paths:
        with open(path, encoding="utf-8", errors='ignore') as f:
            # 拿到imei
            lines = f.readlines()
            length = len(lines)
            # 如果是空行
            if length == 0:
                return
            try:
                first_line = lines[0]
                end_line = lines[length - 1]
                t = self.comparetime(first_line[0:18], end_line[0:18])
                if t < DAY:
                    return
                # 这里的时间一定是大于24小时的，暂时选择1天的数据
                ts = parse(end_line[0:18]) - datetime.timedelta(1)
                t_str = datetime.datetime.strftime(ts, "%m-%d %H:%M")
                # 数据添加到列表里
                IMEI_RECORD.append(imei)
            except Exception as e:
                print("#####file wrong" + path + "#####")
                print("Exception : ", e)
                return
            # print("count_time", count_time)
            for x in range(self.getstart(lines, length, t_str), length):
                line = lines[x]
                if line.find("am_resume_activity") != -1:  # resume的数据
                    # 06-09 21:46:53.637
                    # ResumeParser().parse(line, result.get('resume'), x, lines, result.get('resume2'),
                    #                      result.get('resume3'))
                    ResumeParser2().parse(line, resume)
                elif line.find("screen_toggled") != -1:
                    # ScreenParser().parse(length, line, lines, result.get("screen"), result.get("screen_focused"), x,
                    #                     result.get("resume4"))
                    ScreenOffParser().parse(line, resume)
                elif line.find("am_activity_launch_time") != -1:
                    LauncherParser().parse(line, resume)
                # elif line.find("am_on_resume_called") != -1:
                #     ResumeCalledParser().parse(line, result.get("resume_called"))
                elif line.find("am_meminfo") != -1:
                    MemParser().parse(line, mem)
                elif line.find("am_crash") != -1:
                    CrashParser().parse(line, crash)
                elif line.find("am_anr") != -1:
                    AnrParser().parse(line, anr)
                elif line.find("am_pss") != -1:
                    PssParser().parse(line, pss)
                else:
                    pass

                    # return resume, mem, crash, anr

    # 画图相关
    def make_sheets(self):
        # builder = SheetBuilder()
        # time1 = results.get("count_time")
        # print("统计时间总和 = " + str(time1 / HOUR) + " 小时")
        report_dir = "report/" + self.prefix_name + "/"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
       
        # for n in users:
            # df = pd.read_sql(
                # '''SELECT * FROM resume_record where imei = '{0}' and model = '{1}' '''.format(n, model), self.openDb())
            # self.make_app_use_time_sql(df, n, self.prefix_name)

        self.top10_use_time(report_dir)
        self.top10_fg_times(report_dir)
        self.top10_fg_spread_time(report_dir)
        self.queryMem(report_dir)
        self.top10_fg_ui_times(report_dir)
        self.make_top10_pss_sheet(report_dir)
        self.make_top10_app_switch_sheet(report_dir)

    def make_top10_pss_sheet(self, report_dir):
        writer_to = pd.ExcelWriter(report_dir + "/" + self.prefix_name + "top10_main_process_pss_detail.xlsx")
        df = pd.read_sql(
            '''SELECT process, AVG(pss) as avg, imei from pss_record WHERE process in ('{0}') and model = '%s' group by imei'''.format(
                "','".join(top10app)) % self.prefix_name, self.openDb())
        result = {'pkg': [], 'avg(M)': []}
        for n in df['process'].unique():
            df2 = df[df['process'] == n].copy()
            # print(df2.head())
            # print(df2['avg'])
            df2['avg(M)'] = [x / MB for x in df2['avg']]
            # df2.to_csv("report/"+self.prefix_name+"top10_main_process_pss")
            result.get('pkg').append(n)
            result.get('avg(M)').append(df2['avg(M)'].mean())
            df2.to_excel(writer_to, sheet_name=str(n))
        DataFrame(result).to_csv(report_dir + "/" + self.prefix_name + "top10_main_process_pss.csv")

    # top10 切换过程
    def make_top10_app_switch_sheet(self, report_dir):
        df = pd.read_sql(''' select pkg,pkg2,count(1) count,sum(next_pkg) sum1,sum(pre_pkg) sum2, sum(next_pkg)/count(1) avg1,sum(pre_pkg)/count(1) avg2 
        from app_switch_record where model='{0}' group by pkg,pkg2 '''.format(self.prefix_name), self.openDb())
        df = df[df['pkg'].isin(top10app2)]
        df = df[df['pkg2'].isin(top10app2)]
        df.to_csv(report_dir + "/" + self.prefix_name + "top10_app_switch.csv")

        # 可以在解析的时候做

    def save_app_switch_tosql(self, results, imei, model):
        # 应用的跳转关系
        # 移动一次计算
        # results = pd.read_sql(''' SELECT * from resume_record where model = '{0}' '''.format(self.prefix_name), self.openDb())
        # 对于某个imei的用户
        # for i in self.queryImeis(self.prefix_name):
        # data = results[results['imei'] == i].set_index("time").sort_index()
        data = results.set_index("time").sort_index()
        data['next_pkg'] = data['pkg'].shift(-1)
        # data['third_pkg'] = data['pkg'].shift(-2)
        # writer_to = pd.ExcelWriter("report/to.xlsx")
        uniquepkg = data['pkg'].unique()
        # print(top10app)
        df0 = DataFrame()
        # 筛选数据 top10的
        # for p in (top10app2):
        for p in uniquepkg:
            to_data1 = pd.value_counts(data[data['pkg'] == p]['next_pkg'], ascending=False)
            from_data1 = pd.value_counts(data[data['next_pkg'] == p]['pkg'], ascending=False)
            dfx = pd.concat([to_data1, from_data1], axis=1).reset_index().dropna()
            dfx['pre_pkg'] = dfx['pkg']
            dfx['pkg'] = p
            dfx['imei'] = imei
            dfx['model'] = model
            dfx.rename(columns={'index': 'pkg2'}, inplace=True)
            # 继续筛选 去掉index列不在top10中的应用
            # dfx = dfx[dfx['pkg2'].isin(top10app2)]
            # dfx = dfx[dfx[pkg].isin(top10app2) && dfx['pkg2'].isin(top10app2)]
            # dfx = dfx[dfx['pkg2'].isin(top10app2)]
            # print(dfx)
            df0 = df0.append(dfx)
        self.saveDF2sql(df0, "app_switch_record")
        # writer_from = pd.ExcelWriter("report/from.xlsx")
        # for p in uniquepkg:
        # from_data1 = pd.value_counts(data[data['next_pkg'] == p]['pkg'], ascending=False)
        # from_data1.to_excel(writer_from, sheet_name=str(p) if len(str(p)) < 32 else str(p)[:31])

    # 应用的使用时长
    def make_app_use_time_sql(self, df_all, imei, model):
        # com.tencent.tmgp.sgame
        # 应用的时长关系
        df_all = df_all.sort_values("time")  # .sort_index()
        # df_all.to_csv("report/all.csv")
        df_all['next_time'] = df_all["time"].shift(-1)
        f1 = "%m-%d %H:%M:%S.%f"
        df_all['timex'] = pd.to_datetime(df_all['next_time'], format=f1) - pd.to_datetime(df_all['time'], format=f1)
        unique_pkg = df_all['pkg'].unique()
        # print(unique_pkg)
        d = {}
        for p in unique_pkg:
            wx1 = df_all[df_all['pkg'] == p]
            d[p] = wx1.timex.sum()
        # print(d.values(), d.keys())
        df_final = DataFrame({"pkg": list(d.keys()), "time": list(d.values())}).sort_values(by=['time'],
                                                                                            ascending=False)
        df_final['seconds'] = [x.total_seconds() for x in df_final.time]
        df_final['minutes'] = df_final['seconds'] / 60.0
        df_final['imei'] = imei
        df_final['model'] = model
        df_final.drop(['time'], axis=1, inplace=True)
        self.saveDF2sql(df_final, "app_use_time")

    # top10 应用的时长
    def top10_use_time(self, report_dir):
        users = self.queryImeis(self.prefix_name)
        result = []
        # for n in top10app:
            # result.append(self.queryAppUsetime(n))
        # df = DataFrame(data=result, columns=["pkg", "users", "seconds", "avg_min"]).sort_values("seconds",
                                                                                                # ascending=False)
        df = pd.read_sql(''' SELECT pkg, COUNT(imei) as user, sum(seconds) as secs, sum(seconds)/60.0/count(imei) as avg_time 
                        FROM app_use_time WHERE pkg in ('{0}') and model = '{1}' group by pkg '''.format("','".join(top10app),self.prefix_name), self.openDb())
        # print(df.head())
        df['all_user'] = len(users)
        df.to_csv(report_dir + self.prefix_name + "top10_use_time.csv")

    # top10 应用前台的次数
    def top10_fg_times(self, report_dir):
        df = pd.read_sql(''' SELECT pkg, COUNT(pkg)/COUNT(distinct imei) as avg_times, COUNT(pkg) as all_times,COUNT(distinct imei) as users from resume_record
        WHERE pkg in ('{0}') and model = '{1}' GROUP BY pkg '''.format("','".join(top10app), self.prefix_name),
                         self.openDb())
        df = df.sort_values("avg_times", ascending=False)
        df.to_csv(report_dir + self.prefix_name + "top10_fg_times.csv")

    # top10 应用界面次数
    def top10_fg_ui_times(self, report_dir):
        writer_to = pd.ExcelWriter(report_dir + self.prefix_name + "top10_ui_times.xlsx")
        conn = self.openDb()
        df = pdsql.read_sql(
            '''SELECT pkg,ui,COUNT(ui) as uis, COUNT(DISTINCT imei) as users, COUNT(ui)/COUNT(DISTINCT imei) as avg 
            from resume_record WHERE pkg in ('{0}') and model = '{1}' GROUP BY pkg,ui '''.format("','".join(top10app),
                                                                                                 self.prefix_name),
            conn)
        for n in top10app:
            df2 = df[df['pkg'] == n].sort_values("uis", ascending=False)
            df2.to_excel(writer_to, sheet_name=str(n))

    # top10 应用前台时间分布
    def top10_fg_spread_time(self, report_dir):
        conn = self.openDb()
        dx = {}
        for p in top10app:
            df = pdsql.read_sql('''SELECT time,pkg,ui FROM resume_record WHERE(pkg = '{0}')'''.format(p), conn)
            d2 = dict(Counter([int(x[6:8]) for x in df['time']]))
            dx[p] = [d2.get(x) if d2.get(x) else 0 for x in range(24)]
        # DataFrame(dx).to_csv("report/top10_times.csv")
        wb = xlsxwriter.Workbook(report_dir + self.prefix_name + "top10_fg_spread_time.xlsx")
        s = wb.add_worksheet("times")
        i = 0
        for k, v in dx.items():
            s.write(i, 0, k)
            for j in range(len(v)):
                s.write(i, j + 1, v[j])
            i += 1
        s2 = wb.add_worksheet("percent")
        i = 0
        for k, v in dx.items():
            s2.write(i, 0, k)
            count = 1 if sum(v) == 0 else sum(v)
            for j in range(len(v)):
                s2.write(i, j + 1, v[j] / count)
            i += 1
        wb.close()

        # top10 应用的次数
        # def queryTop10Times(self):
        # conn = self.openDb()
        # sql = ''' SELECT pkg,COUNT(pkg) as times,COUNT(distinct imei) as users 
        # from resume_record WHERE pkg in ('{0}') and model = '%s' GROUP BY pkg '''.format("','".join(top10app)) % self.prefix_name
        # # print(sql)
        # cursor = conn.execute(sql)
        # res = []
        # for row in cursor.fetchall():
        # res.append([row[0], row[1], row[2]])
        # conn.close()
        # return res

    # 查询某个机型的内存信息 
    def queryMem(self, report_dir):
        conn = self.openDb()
        df = pdsql.read_sql(
            '''SELECT time, imei,free,cached from mem_record where model = '{0}' '''.format(self.prefix_name), conn)
        # print(df.head())
        conn.close()
        df['free_cached'] = (df['free'].astype(np.float64) + df['cached'].astype(np.float64)) / (1024.0 * 1024.0)
        df['time'] = [str[6:11] for str in df['time']]
        result = {'imei': [], 'mem_avg': []}
        # print(df['imei'].unique())
        for n in df['imei'].unique():
            result.get("imei").append(n)
            result.get("mem_avg").append(df[df['imei'] == n]['free_cached'].mean())
        DataFrame(result).to_csv(report_dir + self.prefix_name + "mem_result.csv")

    # 保存DataFrame 数据到数据库
    def saveDF2sql(self, data, table):
        conn = self.openDb()
        data.to_sql(table, conn, index=False, if_exists="append")
        conn.close()

    # 插入imei数据
    def insertImei(self, model, imei):
        conn = self.openDb()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS imei_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model text,
                imei text
            )
        ''')
        conn.execute("INSERT INTO imei_record VALUES(NULL,?,?)", (model, imei))
        conn.commit()
        conn.close()

    # 数据库操作 
    def openDb(self):
        return sqlite3.connect("eventlog.db")

    # 查询某个机型的样本数据
    def queryImeis(self, model):
        imeis = []
        conn = self.openDb()
        cursor = conn.execute("SELECT * FROM imei_record WHERE(model = ?)", (model,))
        for row in cursor:
            imeis.append(row[2])
        conn.close()
        return imeis

    # 查询应用的使用时间
    def queryAppUsetime(self, pkg):
        conn = self.openDb()
        # cursor = conn.execute("SELECT COUNT(DISTINCT imei),SUM(seconds) FROM app_use_time WHERE pkg = ? and model = ?",
                              # (pkg, self.prefix_name,))
        ''' SELECT COUNT(imei) as user,sum(seconds),sum(seconds)/60.0/count(imei) FROM app_use_time WHERE pkg in ('{0}') and model = '{1}' '''.format("','".join(top10app),self.prefix_name)
        res = cursor.fetchone()
        conn.close()
        if res[0] != 0:
            return [pkg, res[0], res[1], res[1] / res[0] / 60.0]
        return [pkg, 0, 0, 0]

    def threads_run(self, threads):
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def drop_tables_by_model(self, model):
        conn = self.openDb()
        cursor = conn.execute("DELETE * FROM anr_record WHERE model = ?", (model,))
        # pass


if __name__ == '__main__':
    start = time.time()
    print("parse start ...")
    model = "undefined"
    xx = '0'
    yy = '1'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hm:p:d:")
        print(sys.argv[0:])
    except getopt.GetoptError as e:
        print(e)

    for opt, arg in opts:
        if opt == '-h':
            print('''====
            please input:
            -m with a model name
            -p with 1 or 0 to determine whether need reparse 
            -d with 1 or 0 to determine whether need make new theets 
            ''')
            # sys.exit(0) 
        elif opt == '-m':
            model = arg
        elif opt == '-p':
            xx = arg
        elif opt == '-d':
            yy = arg

    DIR = "eventslog/" + model + "/"
    if not os.path.exists(DIR) or len(model) == 0:
        print("!!! couldn't find target log dir !!!")
        sys.exit(0)

    # model = "PD1635"
    eventlog = EventLog(DIR, model)
    # 文件解析写入数据库
    if xx == '1':  # may need drop table first
        eventlog.parse_files()
    # 绘图
    if yy == '1':
        eventlog.make_sheets()
        # eventlog.save_app_switch_tosql()
        # eventlog.make_top10_app_switch_sheet("report/"+model+"/")
        # # eventlog.make_sheets("report/"+model+"/")
    end = time.time() - start
    print("parse and make sheet end in %.1f s" % end)
