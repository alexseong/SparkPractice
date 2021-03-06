
# coding: utf-8

# In[3]:

from pyspark import SparkContext
from pyspark.sql import Row, SQLContext
from pyspark.sql import HiveContext, DataFrameWriter
from datetime import datetime
from dateutil import tz
import time
import os


# In[17]:

#Put all variables here
iHiveTable = "vrawsession"
oHiveTable = "vconsolsession"

iHiveQuery = "SELECT CONCAT(uid, ','," + " start_time, ',' ,dur_loc_seq, ',', " + " data_dt) as ev from " +  iHiveTable


# In[5]:

#iHiveQuery


# In[8]:

#Must do this if running py files independently
sc = SparkContext( 'local', 'pyspark')
hiveContext = HiveContext(sc)


# In[18]:

tdf = hiveContext.sql(iHiveQuery)


# In[19]:

#tdf.collect()


# In[20]:

def toLocDurTuples(line):
    DATETIME_FMT="%Y-%m-%d@%H:%M:%S"
    uidI = 0
    dateI = 3
    startTimeI = 1
    durLocI = 2
    
    values = line.split(',')
    
    #uid_date becomes the key later
    uid_date = values[uidI] + '_' + values[dateI]
    
    #Convert time string to epoch time stamp
    dt_with_tz = datetime(*time.strptime(values[startTimeI], DATETIME_FMT)[:6],
                         tzinfo=tz.tzutc())
    delta = (dt_with_tz - datetime(1970,1,1,tzinfo=tz.tzutc()))
    startTime = delta.days*86400 + delta.seconds
    
    durLocStrL = values[durLocI].split('][')
    durList = map(int, durLocStrL[0][1:].split(':'))
    loclist = map(int, durLocStrL[1][0:-1].split(':'))
    
    locTimeL = []
    dur = 0;
    i = 0
    for d in durList:
        locTimeL.append((loclist[i], startTime+dur, d))
        dur += d
        i += 1
    return (uid_date, locTimeL)

def tfin(x):
    uid_dateI = 0
    locTimeDurI = 1
    
    locI = 0
    tsI = 1
    durI = 2
    
    uid,date = x[uid_dateI].split('_')
    
    data = x[locTimeDurI]
    #Sort by timestamp
    data = sorted(data, key=lambda tup: tup[tsI])
    
    #Remove redundant locations
    data2 = []
    maxlen = len(data) - 1
    i = 0
    while(1):
        if (i >= maxlen):
            if (i == maxlen):
                data2.append(data[i])
            break;
        if data[i][locI] != data[i+1][locI]:
            #locations are different
            data2.append(data[i])
            i += 1
        else:
            #locations are same!
            if (data[i][tsI] + data[i][durI] == data[i+1][tsI]):
                #back to back on same location
                data2.append((data[i][locI],                               data[i][tsI],                               data[i][durI] + data[i+1][durI]))
                #skip the next entry
                i += 2
            else:
                i += 1
    data2 = sorted(data2, key=lambda x: x[2], reverse=True)
    data3 = str(data2).replace(', ',':').replace('):',')|')
    return((uid, data3, int(date)))


# In[21]:

rdd2 = tdf.select("ev").rdd.map(lambda x: toLocDurTuples(x.ev))                        .reduceByKey(lambda a,b: a+b)                        .map(lambda x: tfin(x))


# In[27]:

#rdd2.take(10)


# In[23]:

tdf2 = hiveContext.createDataFrame(rdd2, ['uid','loc_ts_dur', 'data_dt'])


# In[24]:

#tdf2.collect()


# In[25]:

df_writer = DataFrameWriter(tdf2)
df_writer.insertInto(oHiveTable,overwrite=True)


# In[26]:

sc.stop()


# In[31]:

#toLocDurTuples('101,2016-06-01@12:04:02,[40:50][202:203],20160601')


# In[32]:

#tfin(('101_20160601', [(202, 1464782642, 40), (203, 1464782682, 50)]))

