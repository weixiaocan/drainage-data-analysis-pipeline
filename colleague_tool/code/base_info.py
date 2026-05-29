# -*- coding: utf-8 -*-
###
#从base_info.xlsx中读取点位基本信息，并定义相应变量
###
import pandas as pd
from openpyxl import load_workbook
import os

## 读取流量点位基本信息
print("Current working directory:", os.getcwd())
flow_info=pd.read_excel("../base_info.xlsx",'flow')
equip_name=flow_info['equip_name'].values.astype('str') #获取设备编号
node_name=flow_info['node_name'].values.astype('str') #获取点位编号
node_num = len(node_name)#点位数量
D=flow_info['D'].values  #获取管径/mm，如果是渠道，则取高度
H=flow_info['H'].values #获取井深/m
dry_day_mode = flow_info['mode'].values #旱天选择模式
#选择的旱天日期汇总
dry_day={}
for i in range(node_num):
     if dry_day_mode[i] == 1:  #连续旱天，取起始日期和结束日期
         day_start = flow_info['day_start'][i]
         day_end = flow_info['day_end'][i]
         day_period = pd.date_range(day_start,day_end).values.astype('str').tolist()
         for j in range(len(day_period)):
             day_period[j] = day_period[j][0:10]
         dry_day[node_name[i]] = day_period    
     elif dry_day_mode[i] == 2: # 离散旱天，取选择的旱天
         day_select = flow_info['day_select'][i].split(',')
         dry_day[node_name[i]] = day_select
     elif dry_day_mode[i] == 3: #连续旱天+离散旱天
         day_start = flow_info['day_start'][i]
         day_end = flow_info['day_end'][i]
         day_period = pd.date_range(day_start,day_end).values.astype('str').tolist()
         for j in range(len(day_period)):
             day_period[j] = day_period[j][0:10]
         day_select = flow_info['day_select'][i].split(',')
         dry_day[node_name[i]] = day_period+day_select
     elif dry_day_mode[i] == 4: #连续旱天除去部分旱天
         day_start = flow_info['day_start'][i]
         day_end = flow_info['day_end'][i]
         day_period = pd.date_range(day_start,day_end).values.astype('str').tolist()
         for j in range(len(day_period)):
             day_period[j] = day_period[j][0:10]         
         day_delete = flow_info['day_delete'][i].split(',')
         for k in day_delete:
             day_period.remove(k)
         dry_day[node_name[i]] = day_period   
## 读取雨量基本信息
rain_info=pd.read_excel("../base_info.xlsx",'rain')
rainer_name = rain_info['node_name'].values.astype('str') #获取雨量计编号
rainer_data_start = rain_info['day_start'].values.astype('str') #获取雨量计起始监测时间，格式为'yyyy-mm-dd'
rainer_data_end = rain_info['day_end'].values.astype('str') #获取雨量计结束监测时间，格式为'yyyy-mm-dd'
rainer_num = len(rainer_name)#雨量计数量
#每个雨量计对应分析点位
rainer_related_node={}
for i in range(rainer_num):
    rainer_related_node[rainer_name[i]] = rain_info['node'][i].split(',')

## 读取场次降雨信息,即每个雨量计需要分析哪几场场次降雨下的RDII
event_info=pd.read_excel("../base_info.xlsx",'event') 
event_select = {}   
for i in range(len(event_info)):
    event_select[event_info['node_name'][i]] = [int(x) for x in event_info['event'][i].split(',')]
    

##数据文件夹名称
folder_name = 'data'# 代码存储在code文件夹内，数据存储在同级文件夹‘data’内，文件名要对应

###设置参数汇总：
wb = load_workbook(filename = '../base_info.xlsx')
#（1）流量表头名称标注
#顺序为excel数据表格中的第1列，第3列，第4列，第5列
#t-时间 l-液位 velo-流速 f-流量
flow_header_names = eval(wb['parameter']['B2'].value) #默认：['t','f','velo','l']

#（2）绘制旱季特征曲线的模式 
#dry_curve_mode=1:每日曲线不区分日期，统一用灰色显示 
#dry_curve_mode=2:每日曲线区分日期，每个日期配一种颜色 
dry_curve_mode=wb['parameter']['B3'].value  #默认：1

#(3)平滑旱季特征曲线时，移动平均窗口长度
dry_curve_smooth_win_L = wb['parameter']['B4'].value #默认：20

#(4)场次降雨统计规定
min_interval=wb['parameter']['B5'].value  #默认12 #场次降雨划分时间,小时
min_rainfall =wb['parameter']['B6'].value #默认 1 #最小降雨量，mm，即降雨小于此数不算做降雨

#(5)降雨结束后对系统的影响延迟时间,小时
rain_effect_T = wb['parameter']['B7'].value #默认12