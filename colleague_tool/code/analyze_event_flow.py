# -*- coding: utf-8 -*-
###
#统计各场次降雨下所有点位的最大液位和平均流量
###
#导入变量
import pandas as pd
import pickle
from datetime import timedelta
from base_info import rainer_related_node,rainer_name,rainer_num,rain_effect_T
from read_and_sta_flowdata import save_to_excel

##统计各场次降雨下各监测点位的最大液位和平均流量,点位对应雨量计
def event_flow_info(flow_data,rainer_event,related_node,delay_T):
    #最大液位
    max_level = {}
    #字典keys缺省处理
    for name in related_node:
        max_level.setdefault(name, [])
    #计算最大液位/m
    for i in range(len(related_node)):
        for j in range(len(rainer_event)):
            time_start = rainer_event.iloc[j,0]
            time_end = rainer_event.iloc[j,1] + timedelta(hours=delay_T)
            level_need = flow_data[related_node[i]][time_start:time_end]['l']
            max_level[related_node[i]].append(level_need.max())
    max_level = pd.DataFrame(max_level)       
    
    #平均流量
    ave_flow = {}
    #字典keys缺省处理
    for name in related_node:
        ave_flow.setdefault(name, [])    
    #计算平均流量/m3/d
    for i in range(len(related_node)):
        for j in range(len(rainer_event)):
            time_start = rainer_event.iloc[j,0]
            time_end = rainer_event.iloc[j,1] + timedelta(hours=delay_T)
            flow_need = flow_data[related_node[i]][time_start:time_end]['f']
            ave_flow[related_node[i]].append(flow_need.mean()*86.4)
    ave_flow = pd.DataFrame(ave_flow)      
    
    return (max_level,ave_flow)

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
    ## 统计各场次降雨下各监测点位的最大液位和平均流量,点位对应雨量计
    #降雨效应延迟时间,小时
    delay_T = rain_effect_T
    event_max_level = {} #所有雨量计下相关点位在所有场次降雨下的最大液位
    event_ave_flow = {} #所有雨量计下相关点位在所有场次降雨下的最大流量   
    for i in range(rainer_num):    
        (event_max_level[rainer_name[i]],event_ave_flow[rainer_name[i]]) = event_flow_info(flow_data,event_rain[rainer_name[i]],rainer_related_node[rainer_name[i]],delay_T)
        ##保存统计结果至EXCEL表格
        excel_name = '../statistics.xlsx'
        sheet_name1 = rainer_name[i]+'点位最大液位'
        sheet_name2 = rainer_name[i]+'点位平均流量'
        hds=['编号']+rainer_related_node[rainer_name[i]]
        save_to_excel(event_max_level[rainer_name[i]],excel_name,sheet_name1,hds)
        save_to_excel(event_ave_flow[rainer_name[i]],excel_name,sheet_name2,hds)        
    #保存数据至pickle
    with open('event_max_level.pickle', 'wb') as f:
        pickle.dump(event_max_level, f, pickle.HIGHEST_PROTOCOL)
    with open('event_ave_flow.pickle', 'wb') as f:
        pickle.dump(event_ave_flow, f, pickle.HIGHEST_PROTOCOL)
    