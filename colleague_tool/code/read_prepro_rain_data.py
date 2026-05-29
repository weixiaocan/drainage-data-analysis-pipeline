# -*- coding: utf-8 -*-
###
# 读取、预处理、存储雨量数据
###
##导入变量
import numpy as np
import pandas as pd
import pickle
from base_info import folder_name,rainer_name,rainer_num

## 原始雨量数据读取
def get_rain_data_ori(folder_name,rainer_name,rainer_num):
    #生成数据读取的路径
    path = []
    for i in range(rainer_num):
        path.append('../'+folder_name+'/' + rainer_name[i] + '.csv')
    #原始数据的读取和储存
    rain_data_ori = {}
    for i in range(rainer_num):
        rain_data_ori[rainer_name[i]] = pd.read_csv(path[i],header = 0,index_col = 0,parse_dates = [0])
    return rain_data_ori

## 数据预处理
#生成连续时间的降雨数据；未监测的时间点填充0
def zeroData(df):  
    index = df.index
    #得到开始和结束时间
    start, end = index[0], index[-1]
    #原始数据为分钟级数据    
    rng = pd.date_range(start, end, freq='T')
    #填充0值
    df_allZero = pd.Series(np.zeros(len(rng)),index = rng) 
    df_allZero_pd = pd.DataFrame({'temp':df_allZero})
    temp_df = pd.concat([df,df_allZero_pd],axis=1)
    temp_df = temp_df.fillna(0)
    df_Zero = temp_df.drop('temp',axis=1)
    return df_Zero

## 主代码
if __name__ == '__main__':
    ## 原始雨量数据读取
    rain_data_ori = get_rain_data_ori(folder_name,rainer_name,rainer_num)
    ## 存储数据
    with open('rain_data_ori.pickle', 'wb') as f:
        pickle.dump(rain_data_ori, f, pickle.HIGHEST_PROTOCOL)
    ## 数据预处理，分钟级0值填充
    rain_data = {}
    for i in range(rainer_num):
        rain_data[rainer_name[i]] = zeroData(rain_data_ori[rainer_name[i]])
    ## 存储数据
    with open('rain_data.pickle', 'wb') as f:
        pickle.dump(rain_data, f, pickle.HIGHEST_PROTOCOL)
