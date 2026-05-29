# -*- coding: utf-8 -*-
### 
#数据预处理
###
##导入变量
import pandas as pd
import numpy as np
import pickle
#读取基本信息
from base_info import node_num,node_name
    
##预处理    
#1、处理负值，设为0
def no_zero(flow_data):
    for i in range(node_num):
        flow_data[node_name[i]][flow_data[node_name[i]]<0] = 0
    return flow_data

#2、缺失数据插值 
def data_interpolation(flow_data):
    for i in range(node_num):
        time_start = flow_data[node_name[i]].index[0]  
        time_end =flow_data[node_name[i]].index[-1]   #序列的起始和结束时间
        full_date_index = pd.date_range(time_start,time_end,freq = 'T') 
        full_data_series = pd.Series(np.random.randn(len(full_date_index)),index = full_date_index)  
        full_data_pd = pd.DataFrame({'temp':full_data_series})
        temp_df = pd.concat([flow_data[node_name[i]],full_data_pd],axis=1) 
        temp_df.interpolate(method = 'linear',axis = 0,inplace = True) 
        flow_data[node_name[i]] = temp_df.drop('temp',axis=1) 
    return flow_data

if __name__ == '__main__':
    ##读取原始数据
    with open('flow_data_ori.pickle', 'rb') as f:
        flow_data_ori = pickle.load(f)
    ##处理负值，设为0
    # flow_data = no_zero(flow_data_ori)
    ##缺失数据插值
    flow_data = data_interpolation(flow_data_ori)
    #检查
    #no_neg = flow_data[node_name[0]]<0
    #no_neg.sum()
    #flow_data[node_name[0]].isnull().sum()
    ##存储原始数据为pickle格式，数据量较大时可减少读取时间
    with open('flow_data.pickle', 'wb') as f:   
        pickle.dump(flow_data, f, pickle.HIGHEST_PROTOCOL)