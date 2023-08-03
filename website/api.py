#packages
from flask import Blueprint, request

#plots 
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#data 
import pandas as pd

#utils
from .utils import get_all_data, genSankey, calculate_apy
import json

#for importing
import joblib

api = Blueprint("api", __name__)

## routes for api, we need these routes to get graphs
@api.route('/all_graphs')
async def all_graphs():
    raw = await get_all_data()
    # format
    # {
        # data: {
        #   reserveData: {
        #       id,
        #       stableBorrowRate,
        #       variableBorrowRate,
        #       supplyRate
        #   }[],
        #   totalDeposits: {
        #       id,
        #       value,
        #   }[],
        #   totalWithdraws: {
        #       id,
        #       value,
        #   }[],
        # }
    # }[]

    data = []
    for inner_raw in raw:
        data += inner_raw["data"]["reserveDatas"]

    df = pd.DataFrame(data)
    df.set_index("id", inplace=True)
    df['supplyAPY'] = df['supplyRate'].apply(lambda x: calculate_apy(x))
    df['stableBorrowAPY'] = df['stableBorrowRate'].apply(lambda x: calculate_apy(x))
    df['variableBorrowAPY'] = df['variableBorrowRate'].apply(lambda x: calculate_apy(x))

    fig = px.line(
                df, 
                y='supplyAPY',
                #color="PROTOCOL",
                #color_discrete_map=color_discrete_map,
                labels={
                    "id": "Date",
                    "supplyAPY": "Supply APY (%)"
                },
                title="Rates",
            )
    fig.update_layout(hovermode="x")
    fig2 = px.line(
                df, 
                y=['stableBorrowAPY', 'variableBorrowAPY'],
                labels={
                    "id": "Date",
                    "stableBorrowAPY": "Stable Borrow APY (%)",
                    "variableBorrowAPY": "Variable Borrow APY (%)",
                },
                title="Borrow Rates",
            )
    fig2.update_layout(yaxis_title="APY (%)", xaxis_title="Date", hovermode="x")

    #deposit and withdraws
    deposit_data = []
    for inner_raw in raw:
        deposit_data += inner_raw["data"]["totalDeposits"]

    #deposit and withdraws
    withdraw_data = []
    for inner_raw in raw:
        withdraw_data += inner_raw["data"]["totalWithdraws"]

    deposit_df = pd.DataFrame(deposit_data).set_index("id")
    # withdraw_df = pd.DataFrame(withdraw_data)

    # value_df = deposit_df.merge(withdraw_df, on='id')
    # print(value_df)
    DECIMALS = 10**18 # 10e18 decimal points
    deposit_df['ETH_DEPOSIT'] = deposit_df['value'].apply(lambda x: float(x) / DECIMALS)

    fig3 = px.bar(
                deposit_df, 
                y=['ETH_DEPOSIT'],
                labels={
                    "id": "Date",
                    "ETH_DEPOSIT": "Deposits (ETH)",
                },
                title="ETH Deposits And Withdrawals",
            )
    fig3.update_layout(yaxis_title="Deposits and Withdrawals (ETH)", xaxis_title="Date", hovermode="x")

    return {
        "rate_lines": fig.to_html(),
        "borrow_lines": fig2.to_html(),
        "deposits": fig3.to_html(),
    }
