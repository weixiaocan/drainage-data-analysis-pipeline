# -*- coding: utf-8 -*-
###
# 场次降雨RDII分析
###

##导入变量
from datetime import timedelta
import pandas as pd
import numpy as np
import pickle
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
#from matplotlib.dates import MinuteLocator,HourLocator,DateFormatter,datestr2num
from matplotlib import gridspec
mpl.rcParams['font.sans-serif'] = ['SimHei']
mpl.rcParams['font.serif'] = ['SimHei']
mpl.rcParams['axes.unicode_minus'] = False # 解决保存图像是负号'-'显示为方块的问题,或者转换负号为字符串
from read_and_sta_flowdata import save_to_excel
from base_info import rainer_related_node,rainer_name,rainer_num,event_select,rain_effect_T
from time import sleep
from tqdm import tqdm


##特定雨量计下特定场次降雨下所有点位的过程线,雨天数据|旱天数据|差值
def get_rdii_curve_data(flow_data,dry_curve_data,event_index,node_name,rainer_event,delay_T):
    #降雨事件起止时间
    time_start = rainer_event.iloc[event_index,0]
    time_end_org = rainer_event.iloc[event_index,1]
    
    time_end = time_end_org + timedelta(hours=delay_T) 
    # if event_index == 6:
    #     time_end = time_end_org + timedelta(hours=30) 
    #计算降雨总时长/分钟
    delta_T = (time_end - time_start).total_seconds()/60
    #场次降雨发生时间序列
    date_index = pd.date_range(time_start,time_end,freq = 'T')
    #生成过程线
    rdii_curve_data = {}
    for i in range(len(node_name)):      
        if (flow_data[node_name[i]].index[0]<time_start) & (flow_data[node_name[i]].index[-1]>time_end):
            temp = np.empty((int(delta_T)+1,4))
            temp[:,0] = flow_data[node_name[i]][time_start:time_end]['f'].values #降雨条件下实测数据
            daily_flow_temp = dry_curve_data[node_name[i]]['f'].values #对应的旱季特征曲线，从特定时间开始
            daily_flow_temp = np.tile(daily_flow_temp,int(np.ceil(delta_T/1440)+1))
            index_start = time_start.hour*60+time_start.minute #开始时间
            index_end = index_start + int(delta_T) +1 #结束时间
            temp[:,1] =daily_flow_temp[index_start:index_end]
            temp[:,2] = temp[:,0]-temp[:,1]
            temp[:,3] = temp[:,0]
            rdii_curve_data[node_name[i]] = pd.DataFrame(temp,index = date_index, columns = ['雨天流量','旱天流量','RDII',"Overflow"])
       

    return rdii_curve_data

## 统计RDII总量
def get_total_rdii(rdii_curve_data,node_name):
    total_rdii = np.ones((len(node_name),1))
    for i in range(len(node_name)):
        if node_name[i] in rdii_curve_data.keys():
            total_rdii[i] = rdii_curve_data[node_name[i]][rdii_curve_data[node_name[i]]['RDII']>0]['RDII'].sum()*60/1000 #m3
        else:
            total_rdii[i] = np.nan
    return total_rdii
# 统计各点位的雨天流量
def get_total_overflow(rdii_curve_data,node_name):
    total_overflow = np.ones((len(node_name),1))
    for i in range(len(node_name)):
        if node_name[i] in rdii_curve_data.keys():
            total_overflow[i] = rdii_curve_data[node_name[i]]['Overflow'].sum()*60/1000 #m3
        else:
            total_overflow[i] = np.nan
    return total_overflow

## 绘制RDII过程线
def draw_rdii_curve(rdii_curve_data,rainer_rain_data,node_name,rainer_event,event_index,delay_T,rainer_name):
    #降雨事件起止时间
    time_start = rainer_event.iloc[event_index,0]
    time_end_org = rainer_event.iloc[event_index,1]
    time_end = time_end_org + timedelta(hours=delay_T) 
    #绘图
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 3])
    for i in tqdm(range(len(node_name))):
        sleep(0.01)
        if node_name[i] in rdii_curve_data.keys():
            data_to_plot =  rdii_curve_data[node_name[i]].copy()
            data_to_plot.drop(columns=['Overflow'],inplace = True)
            ax1 = plt.subplot(gs[1])
            ax2 = plt.subplot(gs[0])
            ax2.get_xaxis().set_visible(False)
            f = plt.gcf()
            f.subplots_adjust(hspace=0)            
            data_to_plot.plot(ax=ax1,legend = True,figsize = (10,5))
            ax1.set_xlabel('时间',fontsize = 'large')
            ax1.set_ylabel('流量/(L/s)',fontsize = 'large')
            #在上方绘制降雨过程线
            rainer_rain_data[time_start:time_end]['rain'].plot(ax=ax2,kind='bar',width = 0.5)
            ax2.set_ylabel('降雨/mm',fontsize = 'large')
            #保存图片
            #新建文件夹
            time_name = str(time_start.month) + '_' + str(time_start.day)
            folder_name = '../figure/rdii_curve/'+rainer_name + '/event' + str(event_index) + '_' + time_name
            if not os.path.exists(folder_name):
                os.mkdir(folder_name)
            plt_name = folder_name+'/'+node_name[i]+'_rain_event'+str(event_index)+'.png'
            plt.savefig(plt_name,dpi=300,bbox_inches = 'tight')    
            plt.cla()
            plt.clf()
            plt.close()

#主函数
if __name__ == '__main__':
    ##读取流量数据
    #流量数据
    with open('flow_data.pickle', 'rb') as f:
        flow_data = pickle.load(f)    
    #场次降雨信息
    with open('event_rain.pickle', 'rb') as f:
        event_rain = pickle.load(f)      
    #降雨数据
    with open('rain_data.pickle', 'rb') as f:
        rain_data = pickle.load(f) 
    #旱季特征曲线
    with open('dry_curve_data.pickle', 'rb') as f:
        dry_curve_data = pickle.load(f)
        
    ## 获得RDII曲线数据和统计
    #降雨效应延迟时间,小时
    delay_T = rain_effect_T
    #分event,分rainer，字典中的字典
    rdii_curve_data_all = {}
    for i in range(rainer_num):
        rdii_curve_data_rainer = {}
        rainer_event_select = event_select[rainer_name[i]] #该雨量计下需要分析的场次降雨
        node_name = rainer_related_node[rainer_name[i]] #该雨量计对应的点位名称
        rainer_event = event_rain[rainer_name[i]] #该雨量计对应的场次降雨
        for j in range(len(rainer_event_select)):
            event_no = rainer_event_select[j]
            rdii_curve_data_rainer[event_no] = get_rdii_curve_data(flow_data,dry_curve_data,event_no,node_name,rainer_event,delay_T)
        rdii_curve_data_all[rainer_name[i]] = rdii_curve_data_rainer
    #保存数据
    with open('rdii_curve_data_all.pickle', 'wb') as f:
        pickle.dump(rdii_curve_data_all, f, pickle.HIGHEST_PROTOCOL)
    
    ## 统计RDII量，一个rainer一个表，纵轴点位数，横轴降雨事件，RDII总量单位m3
    all_total_rdii = {}
    for i in range(rainer_num):
        rdii_curve_data_rainer = rdii_curve_data_all[rainer_name[i]]
        rainer_event_select = event_select[rainer_name[i]] #该雨量计下需要分析的场次降雨
        node_name = rainer_related_node[rainer_name[i]] #该雨量计对应的点位名称
        rainer_total_rdii = np.empty((len(node_name),len(rainer_event_select)))
        for j in range(len(rainer_event_select)):
            event_no = rainer_event_select[j]
            print(event_no)
            rainer_total_rdii[0:len(node_name),j:j+1]=get_total_rdii(rdii_curve_data_rainer[event_no],node_name)
        all_total_rdii[rainer_name[i]] = pd.DataFrame(rainer_total_rdii,index=node_name,columns=rainer_event_select)
        #保存统计结果至EXCEL表格
        excel_name = '../statistics.xlsx'
        sheet_name = rainer_name[i]+'RDII总量'
        hds=['点位编号']+[str(event) for event in rainer_event_select]
        save_to_excel(all_total_rdii[rainer_name[i]],excel_name,sheet_name,hds)

        ## 统计雨天总流量，一个rainer一个表，纵轴点位数，横轴降雨事件，Overflow总量单位m3
    all_total_overflow = {}
    for i in range(rainer_num):
        rdii_curve_data_rainer = rdii_curve_data_all[rainer_name[i]]
        rainer_event_select = event_select[rainer_name[i]] #该雨量计下需要分析的场次降雨
        node_name = rainer_related_node[rainer_name[i]] #该雨量计对应的点位名称
        rainer_total_overflow = np.empty((len(node_name),len(rainer_event_select)))
        for j in range(len(rainer_event_select)):
            event_no = rainer_event_select[j]
            print(event_no)
            rainer_total_overflow[0:len(node_name),j:j+1]=get_total_overflow(rdii_curve_data_rainer[event_no],node_name)
        all_total_overflow[rainer_name[i]] = pd.DataFrame(rainer_total_overflow,index=node_name,columns=rainer_event_select)
        #保存统计结果至EXCEL表格
        excel_name = '../statistics.xlsx'
        sheet_name = rainer_name[i]+'雨天流量总量'
        hds=['点位编号']+[str(event) for event in rainer_event_select]
        save_to_excel(all_total_overflow[rainer_name[i]],excel_name,sheet_name,hds)

    #保存数据至pickle
    with open('all_total_rdii.pickle', 'wb') as f:
        pickle.dump(all_total_rdii, f, pickle.HIGHEST_PROTOCOL)
    # 绘制曲线
    for i in range(rainer_num):
        #新建rainer文件夹
        folder_name = '../figure/rdii_curve/'+rainer_name[i]
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        rdii_curve_data_rainer = rdii_curve_data_all[rainer_name[i]]
        rainer_event_select = event_select[rainer_name[i]] #该雨量计下需要分析的场次降雨
        node_name = rainer_related_node[rainer_name[i]] #该雨量计对应的点位名称
        rainer_event = event_rain[rainer_name[i]] #该雨量计对应的场次降雨
        for j in range(len(rainer_event_select)):
            event_no = rainer_event_select[j]
            draw_rdii_curve(rdii_curve_data_rainer[event_no],rain_data[rainer_name[i]],node_name,rainer_event,event_no,delay_T,rainer_name[i])

    