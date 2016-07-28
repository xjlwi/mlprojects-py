import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mltools import apply_zeroMeanUnit2D, preprocess2DtoZeroMeanUnit, undo_zeroMeanUnit2D
import time

import re
from matplotlib import cm as CM


from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer
from sklearn import metrics

from sklearn.cluster import KMeans, MiniBatchKMeans

from inventory_demand import *

def five_group_stats(group):
    sales = np.array(group['Demanda_uni_equil'].values)
    #samana = group['Semana'].values
    #max_index = np.argmax(samana)
    return np.mean(sales), len(sales), np.std(sales), np.median(sales)


def add_five_grouped_stats(train_df, test_df, testDf):
    start_ts = time.time()

    #we first remove any entry that has only returns
    sales_df = train_df[train_df['Demanda_uni_equil'] > 0]
    grouped = sales_df.groupby(['Agencia_ID', 'Canal_ID', 'Ruta_SAK', 'Cliente_ID', 'Producto_ID'])

    slope_data_df = grouped.apply(five_group_stats)
    sales_data_df = slope_data_df.to_frame("sales_data")
    sales_data_df.reset_index(inplace=True)
    valuesDf = expand_array_feild_and_add_df(sales_data_df, 'sales_data', ["mean_sales", "sales_count", "sales_stddev", "median_sales"])
    #valuesDf = expand_array_feild_and_add_df(sales_data_df, 'sales_data', ["sales_count"])

    #now we merge the data
    sale_data_aggr_time = time.time()
    train_df_m = pd.merge(train_df, valuesDf, how='left', on=['Agencia_ID', 'Canal_ID', 'Ruta_SAK', 'Cliente_ID', 'Producto_ID'])
    train_df_m.fillna(0, inplace=True)
    test_df_m = pd.merge(test_df, valuesDf, how='left', on=['Agencia_ID', 'Canal_ID', 'Ruta_SAK', 'Cliente_ID', 'Producto_ID'])
    test_df_m.fillna(0, inplace=True)

    if testDf is not None:
        testDf = pd.merge(testDf, valuesDf, how='left', on=['Agencia_ID', 'Canal_ID', 'Ruta_SAK', 'Cliente_ID', 'Producto_ID'])
        testDf.fillna(0, inplace=True)

    slopes_time = time.time()
    print "Add Sales Data took %f (%f, %f)" %(slopes_time - start_ts, sale_data_aggr_time-start_ts, slopes_time-sale_data_aggr_time)
    return train_df_m, test_df_m, testDf

def check_accuracy_from_model_output(conf, y_pred_raw, y_actual_test, label):
    y_pred_final = modeloutput2predictions(y_pred_raw, parmsFromNormalization=conf.parmsFromNormalization)
    if conf.target_as_log:
        y_pred_final = retransfrom_from_log(y_pred_final)

    error_ac, rmsep, mape, rmse = almost_correct_based_accuracy(y_actual_test, y_pred_final, 10)
    rmsle = calculate_rmsle(y_actual_test, y_pred_final)
    print ">> %s AC_errorRate=%.1f RMSEP=%.6f MAPE=%6f RMSE=%6f rmsle=%.5f" %("Run " + str(conf.command)+ " "
                                                                              + label, error_ac, rmsep, mape, rmse, rmsle)



def do_simple_models(conf, train_df, test_df, subdf, y_actual_test):
    train_df, test_df, testDf = add_five_grouped_stats(train_df, test_df, subdf)

    mean_forecast = test_df['mean_sales']
    calculate_accuracy("mean_forecast", y_actual_test, mean_forecast)

    median_forecast = test_df['median_sales']
    calculate_accuracy("median_forecast", y_actual_test, median_forecast)