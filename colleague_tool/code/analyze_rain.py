# -*- coding: utf-8 -*-
###
# 统计分析雨量数据
###
##导入变量
import numpy as np
import pandas as pd
import pickle
from base_info import rainer_name,rainer_num,min_interval,min_rainfall
from read_and_sta_flowdata import save_to_excel
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator,DateFormatter
import os

mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['font.serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False # 解决保存图像是负号'-'显示为方块的问题,或者转换负号为字符串

## 日降雨量统计
def get_daily_rain(df):
    return df.resample('D').sum()

## 场次降雨划分函数：去掉0值后，找出连续两个值之间的时间差是否大于设置的划分标准
#按n小时划分场次降雨
def timeSpilt(df, n):
    #去掉0值
    df_noZero =  df[df != 0]
    df = df_noZero.dropna()

    #获取时间索引
    timeStamp = df.index
    #初始化列表，用于保存生成的降雨开始和结束时间点
    rainRng = []
    #设置开始时间节点列表（第一个数即为第一场降雨的开始时间节点）
    timeNode = [timeStamp[0], ]
    for i in range(1, len(timeStamp)):
        #计算连续两个时间点的时间差（下一场开始-上一场结束）
        diff = (timeStamp[i] - timeStamp[i-1])/np.timedelta64(1, 's')
        if diff >= n*60*60:
            #添加开始时间节点（即开始时间节点列表timeNode的最后一项）和结束时间节点
            rainRng.append([timeNode[-1], timeStamp[i-1]])
            #添加下一场开始降雨时间节点
            timeNode.append(timeStamp[i])
    rainRng.append([timeNode[-1], timeStamp[-1]])
    return rainRng

##处理降雨数据，提取场次降雨特征值
def rainInfo(rainRng, df_Zero,min_rain):
    #初始化字典，用于保存生成的场次降雨特征值
    rf = {}
    #场次降雨特征值的字段名（开始时间，结束时间，总降雨量，持续时间、最大值，最大5分钟累积值，最大10分钟累积值，平均强度）
    names = ['start','end','sum','duration','max','max5','max10','max60','max1440','Intensity']
    #字典keys缺省处理
    for name in names:
        rf.setdefault(name, [])

    #对各场次降雨进行遍历
    for i in range(len(rainRng)):
        start, end = rainRng[i]
        df_need =df_Zero[start:end]
        #总降雨量
        rainsum = float(df_need.sum())
        #选取降雨量大于10mm的降雨量
        if rainsum > min_rain:
            #降雨历时
            duration = (end - start)/(np.timedelta64(1, 's')*60*60)
            rf['duration'].append(duration)            
            rf['start'].append(start)
            rf['end'].append(end)
            #场次降雨总量
            rf['sum'].append(rainsum)
            #最大值
            rf['max'].append(df_need.max()[0])
            #5分钟累积最大值
            rf['max5'].append(df_need.rolling(5).sum().max()[0])
            rf['max10'].append(df_need.rolling(10).sum().max()[0])
            rf['max60'].append(df_need.rolling(60).sum().max()[0])
            rf['max1440'].append(df_need.rolling(1440).sum().max()[0])

            Inten = rainsum/duration
            rf['Intensity'].append(Inten)
    #数据转为为DataFrame      
    df = pd.DataFrame(rf)
    return df

## 绘制降雨过程线
def draw_event_rain(rainer_event,rain_data,figflie_name):
    for event_index in range(rainer_event.shape[0]):
        time_start = rainer_event.iloc[event_index,0]
        time_end = rainer_event.iloc[event_index,1]
        time_name = str(time_start.month) + '_' + str(time_start.day)
        #绘制降雨过程线
        fig = plt.figure(figsize=(16,6),dpi=120)
        axis = fig.add_subplot(1,1,1)
        axis.bar(rain_data[time_start:time_end].index,rain_data[time_start:time_end]['rain'].values,width=0.005)
        axis.xaxis.set_major_formatter(DateFormatter('%m-%d %H:%M'))
        axis.xaxis.set_major_locator(HourLocator(byhour=range(0,24,1)))  #设置时间显示格式和间隔
        axis.set_xlim((time_start,time_end)) #设置时间横轴范围，可直接用时间戳！
        axis.set_xlabel('时间',fontsize = 'large')
        axis.set_ylabel('降雨/mm',fontsize = 'large')
        for tick in axis.get_xticklabels():  #时间标签旋转
            tick.set_rotation(30)
        #保存图片
        #新建文件夹
        folder_name = '../figure/rain_curve/'+figflie_name
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        plt_name = folder_name+'/'+time_name+'_rain_event.png'
        plt.savefig(plt_name,dpi=300,bbox_inches = 'tight')    
        plt.cla()
        plt.clf()
        plt.close()

## 主代码
if __name__ == '__main__':
    ## 雨量数据读取
    with open('rain_data.pickle', 'rb') as f:
        rain_data = pickle.load(f)    
    ## 日降雨量统计和保存
    daily_rain = {}
    for i in range(rainer_num):
        daily_rain[rainer_name[i]] = get_daily_rain(rain_data[rainer_name[i]])
        #保存统计结果至EXCEL表格
        excel_name = '../statistics.xlsx'
        sheet_name = rainer_name[i]+'_日降雨量'
        hds=['日期','日降雨量(mm)']
        save_to_excel(daily_rain[rainer_name[i]],excel_name,sheet_name,hds) 
    ##场次降雨统计和保存
    n=min_interval #场次降雨划分时间,小时
    min_rain = min_rainfall #最小降雨量，mm，即降雨小于此数不算做降雨
    event_rain = {}
    for i in range(rainer_num):
        rainRng = timeSpilt(rain_data[rainer_name[i]], n)
        event_rain[rainer_name[i]] = rainInfo(rainRng, rain_data[rainer_name[i]],min_rain)
        #保存统计结果至EXCEL表格
        excel_name = '../statistics.xlsx'
        sheet_name = rainer_name[i]+'_场次降雨统计'
        hds=['编号','开始时间','结束时间','总降雨量/mm','降雨历时/h','最大1分钟降雨量/mm','最大5分钟降雨量/mm','最大10分钟降雨量/mm','最大60分钟降雨量/mm','最大24小时降雨量/mm','平均强度/mm/h']
        save_to_excel(event_rain[rainer_name[i]],excel_name,sheet_name,hds)        
    with open('event_rain.pickle', 'wb') as f:
        pickle.dump(event_rain, f, pickle.HIGHEST_PROTOCOL)
    ## 绘制降雨过程线
    for i in range(rainer_num):
        draw_event_rain(event_rain[rainer_name[i]],rain_data[rainer_name[i]],rainer_name[i])