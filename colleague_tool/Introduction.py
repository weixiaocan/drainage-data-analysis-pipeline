#**************************************************************************
# 【Purpose】
# 流量数据分析:旱天分析、雨天分析、RDII分析等
# 【Version】
# V0.4(beta试用阶段)
# 【Inputs】
# 1.base_info.xlsx 包含信息如下
# 1.1 sheet:parameter
#   flow_header_names:流量表头名称标注 顺序为excel数据表格中的第1列，第3列，第4列，第5列 t-时间 l-液位 velo-流速 f-流量
#   dry_curve_mode：绘制旱季特征曲线的模式  dry_curve_mode=1:每日曲线不区分日期，统一用灰色显示  dry_curve_mode=2:每日曲线区分日期，每个日期配一种颜色
#   dry_curve_smooth_win_L：平滑旱季特征曲线时，移动平均窗口长度
#   min_interval：场次降雨划分时间,小时
#   min_rainfall：最小降雨量，mm，即降雨小于此数不算做降雨
#   rain_effect_T：降雨结束后对系统的影响延迟时间,小时
# 1.2 sheet:flow
#   node_name:点位编号
#   equip_name:设备编号，与下载的数据表格名称（不包含后缀）一致
#   D:管径/mm，如果是渠道，则取高度
#   H:井深/m
#   mode：旱天选取模式
#       1：连续旱天，取day_start,day_end
#       2：离散旱天，取day_select
#       3：连续旱天+离散旱天,取day_start,day_end,day_select
#       4：连续旱天除去部分旱天,取day_start,day_end,day_delete
#   day_start:旱天分析起始日期，格式为'yyyy-mm-dd'
#   day_end:旱天分析结束日期，格式为'yyyy-mm-dd'
#   day_select:旱天离散选择日期，格式为'yyyy-mm-dd'，多个值','相隔
#   day_delete:剔除不分析旱天日期,格式为'yyyy-mm-dd'，多个值','相隔
# 1.3 sheet：rain
#   No:编号
#   node_name：雨量计名称，与数据表格名称（不包含后缀）一致
#   day_start: 雨量数据起始时间，格式为'yyyy-mm-dd'
#   day_end:雨量数据结束时间，格式为'yyyy-mm-dd'
#   node：雨量计关联点位,多个值','相隔
# 1.4 sheet:event
#   No:编号
#   node_name：雨量计名称，与rain表一致
#   event:需要分析的场次降雨编号，在降雨分析（analyze_rain.py）后挑选
# 1.5 注意事项：
#   1.5.1 各列数据的格式及excel单元格类型请勿修改，输入值后若excel自动调整格式需要手动还原
#   1.5.2 逗号需要用英文格式
# 2.监测数据表格，存放于data文件夹内
#   2.1 流量计数据：利用平台的批量下载数据功能下载，1个点位一张表格，表格名称（不包含后缀）和base_info.xlsx表sheet:flow中的equip_name对应
#                   下载时指标选择液位、流速、流量，输出值选平均值，间隔1分钟
#   2.2 雨量计数据：分钟级降雨数据，表格名称（不包含后缀）和base_info.xlsx表sheet:rain中的node_name对应
#   2.3 注意事项：
#       2.3.1：数据表的表头应按照示例，请勿修改
#       2.3.2：雨量计数据为excel表，非分钟级时需进行预处理（rain_hour2minute.py）
# 【Outputs】
# 1.statistics.xlsx:
#   1.1数据总量统计：所有点位的数据量，缺失量，缺失率统计
#   1.2旱天指标统计：所有点位旱天相关指标统计
#   1.3日降雨量：日降雨量统计
#   1.4场次降雨统计：场次降雨及特征参数统计
#   1.5点位最大液位：各点位在各场次降雨下的最大液位统计,m
#   1.6点位平均流量：各点位在各场次降雨下的平均流量统计，m3/d
#   1.7RDII总量：各点位在各场次降雨下的RDII总量统计，m3
# 2.figure文件夹
#   2.1 dry_curve:所有点位旱天流量特征曲线，原始+平滑处理
#   2.2 rain_curve:所有场次降雨过程线
#   2.3 rdii_curve:各点位在各场次降雨下的RDII过程线
# 【Instruction】
# 1.把标准代码复制到工作文件夹
# 2.利用平台的批量下载数据功能下载需要分析的数据表格（下载时指标选择液位、流速、流量，输出值选平均值，间隔1分钟），统一命名，放入“data”文件夹
# 3.填写base_info.xlsx中sheet:parameter/flow/rain相关信息
# 4.依次运行read_and_sta_flowdata.py,prepro_flowdata.py,analyze_dry_flow.py,read_prepro_rain_data.py,analyze_rain.py,analyze_event_flow.py
# 5.查看雨量分析结果，填写base_info.xlsx中sheet:event相关信息
# 6.运行analyze_event_RDLL.py
# 7.在figure中查看图，在statistics.xlsx中查看统计结果
# 8.详细流程和输入输出参见代码框架.jpg
# 【Applicability】  
# 1.day_end当天的全天数据包括在内，如结束日期设为2020-02-01，则分析过程中包含2月1号的数据
# 2.用于分析旱天的选择需要结合数据平台上的时间序列过程线进行判断，
#   选择不受降雨影响，数据稳定未发生异常中断的时间段
# 3.场次降雨分析的选择主要参考雨量过程线，剔除降雨较小的场次
# 4.得到的RDII过程线需要人为分析，对于不好的曲线进行手动剔除，在statistics.xlsx中sheet:RDII总量做相应数据的剔除
# 【Development Date】
# V0.2:2020-02-03
# V0.3:2020-03-15
# V0.4:
# 【Author】
# ZHANG Xudong 
# THWATER
# Email: zhangxd@thwater.com
# Phone: 13718801386
# 【UpdateLog】
# 1.2020-03-06 优化输入输出
#   ZHU Wanning 
#   THWATER
# 2.2020-03-16 升级为V0.3版本
#   加入降雨分析、雨天分析、RDII分析，统一了整体框架，优化输入输出形式
#   ZHANG Xudong 
#   THWATER
# 3.2020-03-18 
#   优化旱天流量特征曲线，除显示特征曲线外，背景叠加显示参与分析的旱天曲线，优化标签显示
#   背景显示可选择灰色无差别显示和不同日期不同颜色显示
#   ZHANG Xudong 
#   THWATER
# 4.2020-03-25
#   优化旱天流量特征曲线,分工作日和周末分别展示，且横轴时间显示调整为正小时
#   ZHANG Xudong 
#   THWATER
# 5.2020-04-06
#   修复降雨统计无法包括最后一场降雨的bug
#   ZHANG Xudong 
#   THWATER
# 6.2020-05-19
#   根据平台批量下载数据格式调整流量数据读取部分的代码
#   ZHANG Xudong 
#   THWATER
# 7.2020-07-01
#   在base_info.py中加入流量表头名称标注，避免平台下载数据表头顺序不一致导致的问题
#   把代码中的所有控制参数全部汇总在base_info.xlsx中，统一配置和设置
#   ZHANG Xudong 
#   THWATER
# 8.2021-01-18
#   analyze_dry_flow的输出中增加液位特征曲线
#   ZHANG Xudong 
#   THWATER
# 9.2021-02-18
#  修复最新版anaconda下载后，特征曲线图例显示错误问题
#   ZHANG Xudong 
#   THWATER
# 10.2021-03-15
#   修复最新版anaconda下载后，旱天选择必须按时间先后顺序填报，否则会报错的问题
#   ZHANG Xudong 
#   THWATER
#11.2022-02-08
#   Zhu Yin
#   易用性优化，可定位报错的文件
#   新增运行进度条
# 【copyright】
# 仅供THWATER员工内部使用，请勿外传
# 【Future Version】
# 1.利用聚类、均值等方法排除异常旱天数据，对存在一致规律的旱天数据进行特征曲线运算
# 2.计算RDII时，每场降雨对应的旱天选择离降雨最近的旱天数据
#**************************************************************************
