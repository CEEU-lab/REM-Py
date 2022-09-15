import geopandas as gpd
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV
from REM.utils import neighbor_fields
import matplotlib.pyplot as plt


##########################################################################################
###################### REAL ESTATE PRICES ESTIMATION #####################################
##########################################################################################
def find_min_rmse(nf, x, data_dmatrix):
    '''
    Runs cross validation evaluation to determine the params
    value that minimizes root mean square error.
    ...
    Args:
    ----
    nf (int): n_folds
    x (list): list from 'params' dict values are completed
    data_matrix: xgboost.core.DMatrix

    Returns:
        numeric: min value within the pandas series of all rmse
    '''
    params = {"objective":'reg:squarederror',
              "colsample_bytree":x[0],
              "learning_rate":x[1],
              "max_depth":x[2],
              "alpha":x[3],
             }

    cv_results=xgb.cv(dtrain=data_dmatrix,
                      params=params,
                      nfold=nf,
                      num_boost_round=x[4],
                      early_stopping_rounds=10,
                      metrics='rmse',
                      as_pandas=True)

    return cv_results['test-rmse-mean'].min()

def test_cv_parameters(k, bp, ap, nf, data_dmatrix):
    title = "Optimizing {}".format(k)
    print('')
    print(title)
    print('*'*len(title))
    lst = []

    for v in ap[k]:
        print(v)
        if k == 'colsample_bytree':
            array = [v, bp[1], bp[2], bp[3], bp[4]]

        elif k == 'learning_rate':
            array=[bp[0], v, bp[2], bp[3], bp[4]]

        elif k == 'max_depth':
            array=[bp[0], bp[1], v, bp[3], bp[4]]

        elif k == 'alpha':
            array=[bp[0], bp[1], bp[2], v, bp[4]]

        elif k == 'num_boost_round':
            array=[bp[0], bp[1], bp[2], bp[3], v]

        else:
            pass
        print(array)
        min_rmse = find_min_rmse(nf, array, data_dmatrix)
        lst.append(min_rmse)

    return lst

def print_scores(y_test, preds):
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print("RMSE: %f" % (rmse))

    r2 = np.sqrt(r2_score(y_test, preds))
    print("R_Squared Score : %f" % (r2))


def plot_predicted_vs_test(x_ax, y_test, preds, predicted_name):
    '''
    Plots predicted values against test array.
    '''
    plt.figure(figsize=(14, 5), dpi=80)
    plt.plot(x_ax, y_test, linewidth=0.75, label="test")
    plt.plot(x_ax, preds, '--', linewidth=0.5, color='red', label="predicted",)
    plt.title("Parcels {} - Test and Predicted data".format(predicted_name))
    plt.legend()
    plt.xlabel('Parcel idx')
    plt.ylabel('{} (USD)'.format(predicted_name))
    plt.grid(True)
    plt.show();

def plot_min_rmse(alternatives,results,parameter, color):
    '''
    Plots RMSE change with different parameter values.
    '''
    plt.figure(figsize=(12, 4))
    plt.plot(alternatives, results, color)
    plt.xlabel(parameter)
    plt.ylabel("RMSE")
    plt.title("RMSE change with increasing {}?".format(parameter))
    plt.grid(True)

def optimal_hyperparam(dict1, dict2):
    '''
    Returns the hyperparameter that reduces RMSE.
    ...
    Args:
    ----
    dict1: the parameter name is the key that houses alternative values under list format
    dict2: the parameter name is the key that houses rmse for each tested value

    Returns:
        numeric: parameter value associated to the minimum RMSE
    '''
    df = pd.DataFrame({'parameter':dict1, 'rmse':dict2})
    optimal = df.loc[df['rmse']==df['rmse'].min(),'parameter']
    idx = optimal.index[0]
    return optimal[idx]

def grid_search_optimization(params, X_train,y_train):
    # Gradient Boosting
    xgb_estimator = xgb.XGBRegressor(seed=42)
    gsearch = GridSearchCV(estimator=xgb_estimator,param_grid=params,
                           scoring='neg_root_mean_squared_error',n_jobs=-1,
                           refit='neg_root_mean_squared_error',cv=5,verbose=11)

    gsearch.fit(X_train,y_train)
    print(f'Best Estimator: {gsearch.best_estimator_}')
    print(f'Best Parameters: {gsearch.best_params_}')
    print(f'Best Score: {gsearch.best_score_}')
    return gsearch
