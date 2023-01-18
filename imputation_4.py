# -*- coding: utf-8 -*-
"""Imputation_4.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1xOLZ0bmCkh9TkCpF-lwflQq7jyey8hWy
"""



"""## Importing the necessary libraries and setting of global variables"""

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.experimental import enable_iterative_imputer # noqa
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler, PolynomialFeatures
from sklearn import linear_model
from sklearn.pipeline import Pipeline
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.decomposition import PCA

# %matplotlib inline

pd.options.display.max_columns = None

# Global varaibles
CORR_THRESHOLD = 0.10
FEATURE_COLUMNS = []
column_names = ['Dataset', 'Imputation Algorithm', 'Strategy', 'n_nearest_features','Train r^2 score', 'Prediction r^2 score']
RESULTS_SUMMARY = pd.DataFrame(columns=column_names)

"""### Helper Functions"""

# Drop a fraction of columns
def drop_column_frac(df:pd.DataFrame, column_name:str, replace_with, drop_frac=0.1) -> pd.DataFrame:
    drop_idx = df[column_name].sample(frac=drop_frac).index
    dropped_df = df.copy()
    dropped_df.loc[drop_idx, column_name] = replace_with
    return dropped_df

# Drop columns 
def drop_columns(df:pd.DataFrame, columns_to_drop: list) -> pd.DataFrame:
    return df.drop(columns=columns_to_drop)

# Drop NAs
def drop_nas(df:pd.DataFrame) -> pd.DataFrame:
    return df.dropna()

# Returns best_score_, best_params_, grid_search object
def grid_search(X:np.array, y:np.array, pipeline: Pipeline, params_grid: dict, n_jobs=10) -> (float, dict, float):
    search = GridSearchCV(pipeline, params_grid, n_jobs=n_jobs)
    search.fit(X, y)
    return search.best_score_, search.best_params_, search

# Run pipeline
def run_pipeline(X_train:np.array, y_train:np.array, X_test:np.array, y_test:np.array, pipeline: Pipeline, params_grid: dict) -> [float, float]:
    # Set Parameters
    pipeline.set_params(**params_grid)
    # Fit data
    pipeline.fit(X_train, y_train)
    # Predict data
    y_predicted = pipeline.predict(X_test)
    # Calculate scores
  
    mean_error = mean_squared_error(y_test, y_predicted)
    rms = mean_squared_error(y_test, y_predicted, squared=False)
    r2_score_val = r2_score(y_test, y_predicted)

    return  mean_error, rms, r2_score_val

"""# Zillow Dataset

## Data Preprocessing on Zillow Data
"""

from google.colab import drive
drive.mount('/content/drive/')

# Using training data set since the properties datasets are HUGE
zillow_df = pd.read_csv('/content/drive/My Drive/properties_2016_small.csv')

#Set true target
TRUE_TARGET = 'taxvaluedollarcnt'

# Check the data
zillow_df.head(15)

zillow_df.info()

# Print the value counts for categorical columns
for col in zillow_df.columns:
    if zillow_df[col].dtype == 'object':
        print('\nColumn Name:', col,)
        print(zillow_df[col].value_counts())

"""### Drop all categorical data """

# Select the categorical columns
cat_cols = zillow_df.select_dtypes(include='object').columns

# Drop the columns
zillow_df = zillow_df.drop(columns=cat_cols)

"""### Calculate correlation coefficients against target column"""

correlation_array = zillow_df.corr()[TRUE_TARGET].sort_values(ascending=False)
correlation_array

CORR_THRESHOLD = 0.2

"""### Drop redudant features"""

# Only keep colms that have correlation coeff greater than CORR_THRESHOLD
colms_to_keep = correlation_array[correlation_array > CORR_THRESHOLD]
# Only keep the best correlated columns
parsed_zillow_df = zillow_df[colms_to_keep.index]

"""### Number of NAN values in target column"""

# Number of NANs in target column
num_nan = parsed_zillow_df[TRUE_TARGET].isna().sum()
print('Number of NANs in target column is: ', num_nan)

"""### Drop rows with NAN values in target column"""

# Drop rows with NAN in target column
parsed_zillow_df = parsed_zillow_df.dropna(subset=[TRUE_TARGET], how='any')
# Shuffle data
parsed_zillow_df = parsed_zillow_df.sample(frac=1)
print('Shape of data after dropping NAN values in target column: ', parsed_zillow_df.shape)

"""### Generate correlation map for missing values in feature matrix"""

# Function to plot correlation for variables with NAN values
def correlationMatrix(df, dropDuplicates = True):
    """Plot correlation matrix"""
    # Calculate correlation
    df_corr = df.corr()

    # Exclude duplicate correlations by masking uper right values
    if dropDuplicates:    
        mask = np.zeros_like(df_corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True

    # Set background color / chart style
    sns.set_style(style = 'white')

    # Set up  matplotlib figure
    f, ax = plt.subplots(figsize=(15, 12))

    # Add diverging colormap from red to blue
    cmap = sns.diverging_palette(250, 10, as_cmap=True)

    # Draw correlation plot with or without duplicates
    if dropDuplicates:
        sns.heatmap(df_corr, mask=mask, cmap=cmap, 
                square=True,
                linewidth=.5, cbar_kws={"shrink": .5}, ax=ax)
    else:
        sns.heatmap(df_corr, cmap=cmap, 
                square=True,
                linewidth=.5, cbar_kws={"shrink": .5}, ax=ax)

"""### Create feature and target matrix"""

# Extract target
target = parsed_zillow_df[TRUE_TARGET]

# Extract features
X_original = parsed_zillow_df.drop(columns=[TRUE_TARGET])

# Columns to be used for pair plots
FEATURE_COLUMNS = X_original.columns.to_numpy()

# Check the structure of the data
print('Shape of feature matrix: ', X_original.shape)
print('Shape of target matrix: ', target.shape)

# Columns of rows with NAN values
nan_values = X_original.isna()
nan_columns = nan_values.any()

# Dataframe with columns that have got NAN values
X_original_nan = X_original[(nan_columns[nan_columns == True]).index]

X_original_nan.shape

# Plot the correlation matrix for the variables containing NAN values
# This will help us determine the variables whose covariance is likely to be affected after
# imputation and also which varibales can be used together when imputing
correlationMatrix(X_original_nan, dropDuplicates = True)

correlationMatrix(X_original[X_original.columns.difference(['calculatedfinishedsquarefeet'])], dropDuplicates = True)



X_original = X_original.drop(columns=['calculatedfinishedsquarefeet', 'finishedsquarefeet50'])

X_original.shape

"""# Multivariate Imputation on Zillow Data
Before getting into using various models to perform imputation, we prform mean imputation to create a base for comparison for our models. We then use the state of the art MICE imputation and finally we perform imputation using the various chosen models.

## MICE with MLPRegressor Regressor
### Hyperparameter tuning for MLPRegressr model
"""

# Copy feature matrix
X_missing_mlp = X_original.copy()

# Parameters
param_grid_mlp = {'iterativeimputer__n_nearest_features': [1, 3], 'iterativeimputer__estimator__hidden_layer_sizes':  [10, 30, 50, 80, 100, 150],
                 'iterativeimputer__estimator__alpha': [0.001, 0.0001], 'iterativeimputer__estimator__learning_rate':['constant', 'adaptive'],
                  'iterativeimputer__estimator__tol': [0.001, 0.0001], 'iterativeimputer__estimator__early_stopping':[True],
                  'iterativeimputer__estimator__activation':['relu','logistic'], 'iterativeimputer__estimator__max_iter': [200, 300, 500],
                  'iterativeimputer__estimator__learning_rate_init':[0.01,0.001]}

# Regressor
br_estimator_mlp = BayesianRidge()
# Instantiate knn imputer
iterative_imputer_mlp = IterativeImputer(estimator=MLPRegressor())
# Scaler
scaler_mlp = StandardScaler()
# Estimator
estimator_mlp = make_pipeline(iterative_imputer_mlp, scaler_mlp, br_estimator_mlp)
# Grid search
grid_iterative_imputer_score_mlp, grid_iterative_imputer_params_mlp, grid_iterative_search_mlp = grid_search(X_missing_mlp, target, estimator_mlp, param_grid_mlp)
print('Best MLPRegressor imputer paramemeters: ' , grid_iterative_imputer_params_mlp)

