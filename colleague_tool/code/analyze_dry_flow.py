 # -*- coding: utf-8 -*-
###
#旱天数据处理
###
##导入包和变量
import pandas as pd
import numpy as np
import pickle
#from pandas.tseries.offsets import Day
#from datetime import datetime
import matplotlib.pyplot as plt
#from matplotlib.font_manager import FontProperties
import matplotlib as mpl
from matplotlib.dates import HourLocator,DateFormatter
from read_and_sta_flowdata import save_to_excel
from dateutil.parser import parse
#from openpyxl import load_workbook
#from openpyxl.styles import Font,Border,Alignment,Side
mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['font.serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False # 解决保存图像是负号'-'显示为方块的问题,或者转换负号为字符串
#font = FontProperties(fname=r"c:\windows\fonts\msyh.ttc", size=15)

# 读取基础信息
from base_info import equip_name,node_name,node_num,D,H,dry_day,flow_header_names,dry_curve_mode,dry_curve_smooth_win_L
from time import sleep
from tqdm import tqdm

## 汇总挑选的旱天数据
def get_dry_flow(flow_data,dry_day):
    dry_flow={} 
    for i in range(node_num):
        select_dry_day = dry_day[node_name[i]]
        dry_day_data = [flow_data[node_name[i]][select_dry_day[j]+' 00:00:00':select_dry_day[j]+' 23:59:00'] for j in range(len(select_dry_day))]
        dry_flow[node_name[i]] = pd.concat(dry_day_data)
    return dry_flow

##旱天特征曲线数据，多个旱天数据同一时刻进行平均，划分工作日和周末
def get_dry_curve_data(flow_data,dry_day):
    day_index = pd.date_range('00:00:00','23:59:00',freq = 'T')#pd.timedelta_range('00:00:00','23:59:00',freq = 'T')  
    dry_curve_data = {} #总体
    dry_curve_data_workday={} #工作日
    dry_curve_data_weekend={} #周末
    day_num_temp = np.zeros((node_num,2)) #存储工作日和周末的天数
    for i in range(node_num):
        print(equip_name[i])#可以对着baseinfo表看哪个表格数据有问题
        day_flow_temp = np.zeros((1440,3))
        day_flow_workday_temp = np.zeros((1440,3))
        day_flow_weekend_temp = np.zeros((1440,3))
        select_dry_day = dry_day[node_name[i]]
        workday_num = 0
        weekend_num = 0
        for j in range(len(select_dry_day)):
            day_flow_temp = day_flow_temp + flow_data[node_name[i]][select_dry_day[j]+' 00:00:00':select_dry_day[j]+' 23:59:00'].values
            if parse(select_dry_day[j]).weekday()+1 in [1,2,3,4,5]:
                workday_num = workday_num+1
                day_flow_workday_temp = day_flow_workday_temp + flow_data[node_name[i]][select_dry_day[j]+' 00:00:00':select_dry_day[j]+' 23:59:00'].values
            elif parse(select_dry_day[j]).weekday()+1 in [6,7]:
                weekend_num = weekend_num + 1
                day_flow_weekend_temp = day_flow_weekend_temp + flow_data[node_name[i]][select_dry_day[j]+' 00:00:00':select_dry_day[j]+' 23:59:00'].values
        day_num_temp[i,0] = workday_num
        day_num_temp[i,1] = weekend_num
        dry_curve_data[node_name[i]] = pd.DataFrame(day_flow_temp/len(select_dry_day),index = day_index,columns=flow_header_names[1:])
        if workday_num != 0:
            dry_curve_data_workday[node_name[i]] = pd.DataFrame(day_flow_workday_temp/workday_num,index = day_index,columns=flow_header_names[1:])
        if weekend_num != 0:
            dry_curve_data_weekend[node_name[i]] = pd.DataFrame(day_flow_weekend_temp/weekend_num,index = day_index,columns=flow_header_names[1:])
    day_num = pd.DataFrame(day_num_temp,index=node_name,columns=['workday_num','weekend_num'])
    return dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,day_num
        
##绘制流量特征曲线  
def draw_dry_flow_curve(dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,flow_data,dry_day,day_num,dry_curve_mode,name_suffix):
    for i in tqdm(range(node_num)):
        sleep(0.01)
        #获取所有旱天数据的dataframe
        num_of_day = len(dry_day[node_name[i]])
        dry_flow_each_day = np.zeros((1440,num_of_day))
        for j in range(num_of_day):
            date = dry_day[node_name[i]][j]
            dry_flow_each_day[:,j] = flow_data[node_name[i]][date+' 00:00:00':date+' 23:59:00']['f'].values
        day_index = pd.date_range('00:00:00','23:59:00',freq = 'T')#day_index = pd.timedelta_range('00:00:00','23:59:00',freq = 'T')
        dry_flow_each_day_df = pd.DataFrame(dry_flow_each_day,index = day_index,columns=dry_day[node_name[i]])
        #绘图
        fig = plt.figure(figsize=(10,5),dpi=120)
        ax1 = fig.add_subplot(1,1,1)          
        if dry_curve_mode==1: #每日曲线不区分日期，统一用灰色显示
            if num_of_day == 1:
                dry_flow_each_day_df[dry_day[node_name[i]][0]].plot(ax=ax1,color='#D3D3D3',label='每日流量',legend = True,alpha=0.5)
            elif num_of_day >1:
                for j in range(0,num_of_day-1):
                    dry_flow_each_day_df[dry_day[node_name[i]][j]].plot(ax=ax1,color='#D3D3D3',label='',legend = False,alpha=0.5)
                dry_flow_each_day_df[dry_day[node_name[i]][num_of_day-1]].plot(ax=ax1,color='#D3D3D3',label='每日流量',legend = True,alpha=0.5)
        elif dry_curve_mode==2: #每日曲线区分日期，每个日期配一种颜色
            dry_flow_each_day_df.plot(ax=ax1,legend = True,alpha=0.3)
        
        if day_num.loc[node_name[i],'workday_num'] != 0 and day_num.loc[node_name[i],'weekend_num'] != 0:
            # dry_curve_data_workday[node_name[i]]['f'].plot(ax=ax1,color='#FF8C00',label='流量特征曲线_工作日',legend = True)
            # dry_curve_data_weekend[node_name[i]]['f'].plot(ax=ax1,color='#008080',label='流量特征曲线_周末',legend = True)
            dry_curve_data[node_name[i]]['f'].plot(ax=ax1,color='#1E90FF',label='流量特征曲线_总体',legend = True)

        else:
            dry_curve_data[node_name[i]]['f'].plot(ax=ax1,color='#1E90FF',label='流量特征曲线',legend = True)        

        #图形设计
        ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(HourLocator(byhour=range(0,24,2)))  #设置时间显示格式和间隔
        # time_start = dry_curve_data[node_name[i]].index[0]
        # time_end = dry_curve_data[node_name[i]].index[-1]
        # ax1.set_xlim((time_start,time_end)) #设置时间横轴范围，可直接用时间戳！
        ax1.set_xlabel('时间')
        ax1.set_ylabel('流量/(L/s)') 
        plt.savefig('../figure/dry_curve/'+node_name[i]+name_suffix,dpi=300,bbox_inches = 'tight')
        plt.cla()
        plt.clf()
        plt.close()

##绘制液位特征曲线  
def draw_dry_level_curve(dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,flow_data,dry_day,day_num,dry_curve_mode,name_suffix):
    for i in tqdm(range(node_num)):
        sleep(0.01)
        #获取所有旱天数据的dataframe
        num_of_day = len(dry_day[node_name[i]])
        dry_level_each_day = np.zeros((1440,num_of_day))
        for j in range(num_of_day):
            date = dry_day[node_name[i]][j]
            dry_level_each_day[:,j] = flow_data[node_name[i]][date+' 00:00:00':date+' 23:59:00']['l'].values
        day_index = pd.date_range('00:00:00','23:59:00',freq = 'T')#day_index = pd.timedelta_range('00:00:00','23:59:00',freq = 'T')
        dry_level_each_day_df = pd.DataFrame(dry_level_each_day,index = day_index,columns=dry_day[node_name[i]])
        #绘图
        fig = plt.figure(figsize=(10,5),dpi=120)
        ax1 = fig.add_subplot(1,1,1)  
             
        # if dry_curve_mode==1: #每日曲线不区分日期，统一用灰色显示
        #     if num_of_day == 1:
        #         dry_level_each_day_df[dry_day[node_name[i]][0]].plot(ax=ax1,color='#D3D3D3',label='每日液位',legend = True,alpha=0.5)
        #     elif num_of_day >1:
        #         for j in range(0,num_of_day-1):
        #             dry_level_each_day_df[dry_day[node_name[i]][j]].plot(ax=ax1,color='#D3D3D3',label='',legend = False,alpha=0.3)
        #         dry_level_each_day_df[dry_day[node_name[i]][num_of_day-1]].plot(ax=ax1,color='#D3D3D3',label='每日液位',legend = True,alpha=0.5)
        # elif dry_curve_mode==2: #每日曲线区分日期，每个日期配一种颜色
        #     dry_level_each_day_df.plot(ax=ax1,legend = True,alpha=0.3)
        
        if day_num.loc[node_name[i],'workday_num'] != 0 and day_num.loc[node_name[i],'weekend_num'] != 0:
            # dry_curve_data_workday[node_name[i]]['l'].plot(ax=ax1,label='液位特征曲线_工作日',color='#FF8C00',legend = True)
            # dry_curve_data_weekend[node_name[i]]['l'].plot(ax=ax1,label='液位特征曲线_周末',color='#008080',legend = True)
            dry_curve_data[node_name[i]]['l'].plot(ax=ax1,label='液位特征曲线',color='#1E90FF',legend = True)
        else:
            dry_curve_data[node_name[i]]['l'].plot(ax=ax1,label='液位特征曲线',color='#1E90FF',legend = True)        

        #图形设计
        ax1.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        ax1.xaxis.set_major_locator(HourLocator(byhour=range(0,24,2)))  #设置时间显示格式和间隔
        # time_start = dry_curve_data[node_name[i]].index[0]
        # time_end = dry_curve_data[node_name[i]].index[-1]
        # ax1.set_xlim((time_start,time_end)) #设置时间横轴范围，可直接用时间戳！
        ax1.set_xlabel('时间')
        ax1.set_ylabel('液位/(m)') 
        plt.savefig('../figure/dry_curve/'+node_name[i]+name_suffix,dpi=300,bbox_inches = 'tight')
        plt.cla()
        plt.clf()
        plt.close()

## 平滑处理后曲线数据
def get_dry_curve_smooth_data(dry_curve_data,win_L):
    dry_curve_data_smooth = {}
    all_keys = [str(key) for key in (dry_curve_data.keys())] 
    for i in range(len(all_keys)):
        dry_curve_data_smooth[all_keys[i]] = dry_curve_data[all_keys[i]].rolling(win_L,min_periods=1,center=True).mean()
    return dry_curve_data_smooth
        
##计算旱天统计值
def get_dry_flow_sta(dry_flow,dry_curve_data):
    all_keys = [str(key) for key in (dry_curve_data.keys())]
    dry_flow_sta = np.empty((len(all_keys),9))
    sta_name = ['daily_flow','max_flow','min_flow','std','max_level','max_fullness','flood_risk','mean_velo','mean_level']
    for i in range(len(all_keys)):
        dry_flow_sta[i,0] = np.round(dry_curve_data[all_keys[i]]['f'].mean()*86.4,2)  #daily_flow 日均流量m3/d
        dry_flow_sta[i,1] = np.round(dry_curve_data[all_keys[i]]['f'].max(),2) #max_flow 日最大流量L/s
        dry_flow_sta[i,2] = np.round(dry_curve_data[all_keys[i]]['f'].min(),2) #min_flow 日最小流量L/s
        dry_flow_sta[i,3] = np.round(dry_curve_data[all_keys[i]]['f'].std(),2) #std 流量标准差 L/s
        dry_flow_sta[i,4] = np.round(dry_flow[all_keys[i]]['l'].max(),2) #max_level 最大液位 m
        dry_flow_sta[i,5] = np.round(dry_flow_sta[i,4]/D[i]*1000,2) #max_fullness 最大充满度 最大液位/管径
        dry_flow_sta[i,6] = np.round(dry_flow_sta[i,4]/H[i],2) #flood_risk 外溢风险 最大液位/井深
        dry_flow_sta[i,7] = np.round(dry_flow[all_keys[i]]['velo'].mean(),6) #mean_velo 平均流速 m/s
        dry_flow_sta[i,8] = np.round(dry_flow[all_keys[i]]['l'].mean(),2) #mean_level 平均液位 m

        # key = all_keys[i]
        # if 'velo' not in dry_flow[key].columns:
        #     print(f"[警告] 点位 {key} 缺少 'velo' 字段！")
        # elif dry_flow[key]['velo'].isna().all():
        #     print(f"[警告] 点位 {key} 的 'velo' 全部为 NaN！")
        # elif dry_flow[key]['velo'].isna().sum() > 0:
        #     print(f"[提示] 点位 {key} 的 'velo' 有 {dry_flow[key]['velo'].isna().sum()} 个 NaN 值")
        # else:
        #     print(f"[正常] 点位 {key} 的平均流速为 {dry_flow[key]['velo'].mean():.4f} m/s")
    dry_flow_sta = pd.DataFrame(dry_flow_sta,index = all_keys, columns = sta_name)
    return dry_flow_sta

if __name__ == '__main__':
    ##读取流量数据
    with open('flow_data.pickle', 'rb') as f:
        flow_data = pickle.load(f)
    ## 汇总挑选的旱天数据
    dry_flow = get_dry_flow(flow_data,dry_day)    
    ##获取旱天特征曲线数据
    dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,day_num = get_dry_curve_data(flow_data,dry_day)
    ##存储数据
    with open('dry_curve_data.pickle', 'wb') as f:   
        pickle.dump(dry_curve_data, f, pickle.HIGHEST_PROTOCOL)
    with open('dry_curve_data_workday.pickle', 'wb') as f:   
        pickle.dump(dry_curve_data_workday, f, pickle.HIGHEST_PROTOCOL)
    with open('dry_curve_data_weekend.pickle', 'wb') as f:   
        pickle.dump(dry_curve_data_weekend, f, pickle.HIGHEST_PROTOCOL)        
    ##绘制特征曲线
    #流量
    # draw_dry_flow_curve(dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,flow_data,dry_day,day_num,dry_curve_mode,'_dry_flow_curve.png')
    #液位
    # draw_dry_level_curve(dry_curve_data,dry_curve_data_workday,dry_curve_data_weekend,flow_data,dry_day,day_num,dry_curve_mode,'_dry_level_curve.png')
    ## 平滑处理后绘制特征曲线
    win_L = dry_curve_smooth_win_L   #窗口长度 
    #test,可用于测试合适的平滑窗口长度
    #dry_curve_data_smooth = {}
    #win_L = 20   #窗口长度 
    #dry_curve_data_smooth = dry_curve_data[node_name[0]].rolling(win_L,min_periods=1,center=True).mean()
    #dry_curve_data_smooth.plot(legend = False,figsize = (10,5))
    #ax = plt.gca()
    #ax.set_xlabel('时间',fontproperties=font)
    #ax.set_ylabel('流量/(L/s)',fontproperties=font)
    ## 平滑处理后曲线数据
    dry_curve_data_smooth = get_dry_curve_smooth_data(dry_curve_data,win_L)
    dry_curve_data_workday_smooth = get_dry_curve_smooth_data(dry_curve_data_workday,win_L)
    dry_curve_data_weekend_smooth = get_dry_curve_smooth_data(dry_curve_data_weekend,win_L)
    ## 存储数据
    file_name1 = 'dry_curve_data_smooth_'+str(win_L)+'.pickle'
    with open(file_name1, 'wb') as f:   
        pickle.dump(dry_curve_data_smooth, f, pickle.HIGHEST_PROTOCOL)
    file_name2 = 'dry_curve_data_workday_smooth_'+str(win_L)+'.pickle'
    with open(file_name2, 'wb') as f:   
        pickle.dump(dry_curve_data_workday_smooth, f, pickle.HIGHEST_PROTOCOL) 
    file_name3 = 'dry_curve_data_weekend_smooth_'+str(win_L)+'.pickle'
    with open(file_name3, 'wb') as f:   
        pickle.dump(dry_curve_data_weekend_smooth, f, pickle.HIGHEST_PROTOCOL)     
    ## 绘制平滑处理后曲线
    #流量
    name_suffix = '_dry_flow_curve_smooth_'+str(win_L)+'.png'
    draw_dry_flow_curve(dry_curve_data_smooth,dry_curve_data_workday_smooth,dry_curve_data_weekend_smooth,flow_data,dry_day,day_num,dry_curve_mode,name_suffix)
    #液位
    name_suffix = '_dry_level_curve_smooth_'+str(win_L)+'.png'
    draw_dry_level_curve(dry_curve_data_smooth,dry_curve_data_workday_smooth,dry_curve_data_weekend_smooth,flow_data,dry_day,day_num,dry_curve_mode,name_suffix)
    ##计算旱天统计值
    dry_flow_sta = get_dry_flow_sta(dry_flow,dry_curve_data)
    # dry_flow_workday_sta = get_dry_flow_sta(dry_flow,dry_curve_data_workday)
    # dry_flow_weekend_sta = get_dry_flow_sta(dry_flow,dry_curve_data_weekend)
    ##保存统计结果至EXCEL表格    
    excel_name = '../statistics.xlsx'
    sheet_name = '旱天指标统计'
    hds=['点位编号','日均流量(m3/d)','日最大流量(L/s)','日最小流量(L/s)','流量标准差(L/s)','最大液位(m)','最大充满度','外溢风险','平均流速(m/s)','平均液位m']
    save_to_excel(dry_flow_sta,excel_name,sheet_name,hds)
    