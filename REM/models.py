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

def test_cv_parameters(k, hyper_parameters, nf, data_dmatrix):
    title = "Optimizing {}".format(k)
    print(title)
    print('*'*len(title))
    lst = []

    for v in hyper_parameters[k]:
        print(v)
        # TODO: parametrizar el array de base.
        # este es la mejor linea de base obtenida antes de la validacion cruzada
        if k == 'colsample_bytree':
            array = [v, 0.1, 5, 10, 45]
        elif k == 'learning_rate':
            array=[0.3, v, 5, 10, 45]
        elif k == 'max_depth':
            array=[0.3, 0.1, v, 10, 45]
        elif k == 'alpha':
            array=[0.3, 0.1, 5, v, 45]
        elif k == 'num_boost_round':
            array=[0.3, 0.1, 5, 10, v]
        else:
            pass

        min_rmse = find_min_rmse(nf, array, data_dmatrix)
        lst.append(min_rmse)

    return lst

def print_scores(y_test, preds):
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print("RMSE: %f" % (rmse))

    r2 = np.sqrt(r2_score(y_test, preds))
    print("R_Squared Score : %f" % (r2))

def int_block_groups(x):
    return int(x[1:])

def plot_predicted_vs_test(x_ax, y_test, preds, predicted_name):
    '''
    Plots predicted values against test array.
    '''
    plt.figure(figsize=(14, 5), dpi=80)
    plt.plot(x_ax, y_test, linewidth=0.75, label="test")
    plt.plot(x_ax, preds, '--', linewidth=0.5, color='red', label="predicted",)
    plt.title("{} - Test and Predicted data".format(predicted_name))
    plt.legend()
    plt.xlabel('Parcel idx')
    plt.ylabel('{} (USD)'.format(predicted_name))
    plt.grid(True)
    plt.show();

def plot_cross_val(alternatives,results,parameter, color):
    '''
    Plots hyperparameter optimization along Cross Validation Test.
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

def grid_search_optimization(X_train,y_train):
    # Gradient Boosting
    params = {
              'n_estimators':[250, 500, 1000],
              'max_depth':[3,5],
              'learning_rate':np.linspace(0.001,0.1,4),
              'gamma':np.linspace(0,1,5),
              'min_child_weight':np.linspace(1,5,3),
              'subsample':np.linspace(0.3,0.9,3),
              'colsample_bytree':np.linspace(0.3,0.9,3),
              'reg_alpha':[0,.01,.1,.5,1],
              'reg_lambda':[0,.01,.1,.5,1],
              'scale_pos_weight':np.linspace(1,5,3)
              }


    xgb_estimator = xgb.XGBRegressor(seed=42)


    gsearch = GridSearchCV(estimator=xgb_estimator,param_grid=params,
                           scoring='neg_root_mean_squared_error',n_jobs=-1,
                           refit='neg_root_mean_squared_error',cv=5,verbose=11)

    gsearch.fit(X_train,y_train)
    print(f'Best Estimator: {gsearch.best_estimator_}')
    print(f'Best Parameters: {gsearch.best_params_}')
    print(f'Best Score: {gsearch.best_score_}')
    return gsearch


def xgb_regressor(to_predict_df, expvars, best_params):
    xg_reg = xgb.XGBRegressor(objective ='reg:squarederror',
                              colsample_bytree=best_params['colsample_bytree'],
                              learning_rate=best_params['learning_rate'],
                              max_depth=best_params['max_depth'],
                              alpha=best_params['alpha'],
                              n_estimators=best_params['num_boost_round'],
                              subsample=0.45, # TODO: Parametrizar
                              gamma=1000000) # TODO: Parametrizar
    predicted_vals = xg_reg.predict(to_predict[expvars])
    return xpredicted_vals
