import functools
import aiohttp
import asyncio
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta, date

def force_async(fn):
    '''
    turns a sync function to async function using threads
    '''
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # make it awaitable

    return wrapper

# need to make query loop
# around 100 rows per query
# {
#   reserveDatas(orderBy: id, orderDirection: asc, where: { id_gte: "2022/11/30" }) {
#     id
#     stableBorrowRate
#   }
# }
async def get_api_data(session, id_gte):
    data = {
        "query": "{ reserveDatas(first: 100, orderBy: id, orderDirection: asc, where: { id_gte: " + '"' + id_gte + '"' + " }) {id stableBorrowRate variableBorrowRate supplyRate } totalDeposits(first: 100, orderBy: id, orderDirection: asc, where: { id_gte: " + '"' + id_gte + '"' + " }) {id value } totalWithdraws(first: 100, orderBy: id, orderDirection: asc, where: { id_gte: " + '"' + id_gte + '"' + " }) {id value } }"
    }
    async with session.post(f"https://api.thegraph.com/subgraphs/name/kidacrypto/aave-analysis", json=data) as response:
       return await response.json()

async def get_all_data():
    increment = timedelta(days=100) # 50 day increment per query
    async with aiohttp.ClientSession() as session:
        post_tasks = []
        start_date = date(2022, 9, 1)
        end_date = date.today()

        while start_date < end_date:
            date_str = start_date.isoformat()
            # prepare the coroutines that post
            post_tasks.append(get_api_data(session, date_str))
            start_date = start_date + increment
        # now execute them all at once
        return await asyncio.gather(*post_tasks)

def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), 
                         ['', 'K', 'M', 'B', 'T'][magnitude])

def genSankey(df,cat_cols=[],value_cols='',title='Sankey Diagram'):
    # maximum of 6 value cols -> 6 colors
    colorPalette = ['#4B8BBE','#306998','#FFE873','#FFD43B','#646464']
    labelList = []
    colorNumList = []
    for catCol in cat_cols:
        labelListTemp =  list(set(df[catCol].values))
        colorNumList.append(len(labelListTemp))
        labelList = labelList + labelListTemp
        
    # remove duplicates from labelList
    labelList = list(dict.fromkeys(labelList))
    
    # define colors based on number of levels
    colorList = []
    for idx, colorNum in enumerate(colorNumList):
        colorList = colorList + [colorPalette[idx]]*colorNum
        
    # transform df into a source-target pair
    for i in range(len(cat_cols)-1):
        if i==0:
            sourceTargetDf = df[[cat_cols[i],cat_cols[i+1],value_cols]]
            sourceTargetDf.columns = ['source','target','count']
        else:
            tempDf = df[[cat_cols[i],cat_cols[i+1],value_cols]]
            tempDf.columns = ['source','target','count']
            sourceTargetDf = pd.concat([sourceTargetDf,tempDf])
        sourceTargetDf = sourceTargetDf.groupby(['source','target']).agg({'count':'sum'}).reset_index()
        
    # add index for source-target pair
    sourceTargetDf['sourceID'] = sourceTargetDf['source'].apply(lambda x: labelList.index(x))
    sourceTargetDf['targetID'] = sourceTargetDf['target'].apply(lambda x: labelList.index(x))
    sourceTargetDf['label'] = sourceTargetDf['count'].apply(lambda x: human_format(x))
    
    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(
            color = "black",
            width = 0.5
          ),
          label = labelList,
          color = colorList,
        ),
        link = dict(
          source = sourceTargetDf['sourceID'],
          target = sourceTargetDf['targetID'],
          value = sourceTargetDf['count'],
          label = sourceTargetDf['label']
        ))])
    
    fig.update_layout(title_text=title)
    return fig

# returns the apy based on rate
def calculate_apy(rate):
    #source https://docs.aave.com/developers/v/2.0/guides/apy-and-apr
    RAY = float(10**27)
    SECONDS_PER_YEAR = float(31536000)
    apr = float(rate) / RAY
    apy = pow((1 + (apr / SECONDS_PER_YEAR)), SECONDS_PER_YEAR) - 1
    apy = apy * 100
    return apy