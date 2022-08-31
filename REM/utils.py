import pandas as pd
from scipy.spatial import distance
import numpy.ma as ma
from shapely.geometry import Point
import numpy as np

# 1. Ajustar series de precios por inflacion para traer oferta vieja
def ajuste_inflacion(gdf, inflation):
    '''
    gdf(GeoDataFrame): Points con las coordenadas del aviso
    inflation(DataFrame): Tabla con ratios de inflacion mensual en formato wide
    '''
    def add_0(x):
        if len(x)==1:
            return'0'+x
        else:
            return x
    mth = {'Jan':1, 'Feb':2, 'Mar':3,
           'Apr':4,'May':5, 'Jun':6,
           'Jul':7, 'Aug':8, 'Sep':9,
           'Oct':10, 'Nov':11, 'Dec':12}

    inflation.set_index('Year', inplace=True)

    inflation_ = inflation.reset_index()
    inflation_m = inflation_.melt(id_vars='Year', value_vars=list(mth.keys()))
    inflation_m['variable'] = inflation_m.variable.map(mth)
    inflation_m.rename(columns={'Year':'year', 'variable':'month', 'value':'coeff'}, inplace=True)
    inflation_m = inflation_m.sort_values(by=['year','month'])
    inflation_m.reset_index(inplace=True)
    inflation_m.drop(columns='index', inplace=True)
    inflation_m['year'] = inflation_m['year'].astype(str)
    inflation_m['month'] = inflation_m['month'].astype(str)
    inflation_m['month'] = inflation_m['month'].apply(lambda x: add_0(x))
    inflation_m['period'] = inflation_m['year']+'-'+inflation_m['month']
    inflation_m['period'] = inflation_m['period'].apply(lambda x: pd.Period(x))

    # TODO: escribir requerimientos de dtypes
    gdf['year'] = gdf.start_date.apply(lambda x: str(x)[:4])
    gdf['month'] = gdf.start_date.apply(lambda x: x.month)
    gdf['period'] = gdf['year'].astype(str) + '-' + gdf['month'].astype(str)
    gdf['period'] = gdf['period'].apply(lambda x: add_0(x))

    max_year = gdf.start_date.max().year
    max_month = gdf.start_date.max().month
    max_period = str(max_year) + '-' + add_0(str(max_month+1))

    adj_price=[]
    for row in gdf[['period','price']].iterrows():
        rng_date = pd.date_range(start=row[1]['period'],end=max_period, freq='M')
        tgt_dates = [str(i)[:7] for i in rng_date]
        inflation_p = inflation_m.loc[inflation_m['period'].astype(str).isin(tgt_dates)]
        coeff = inflation_p['coeff'].mean()
        adj_price.append(int(row[1]['price']+row[1]['price']*(coeff*0.001)))

    gdf['price_adj'] = adj_price

    return gdf.copy()

# 2. Obtiene los N vecinos mas cercanos en un mismo GeodataFrame de Poligonos
def neighbor_fields(poly_gdf, proj, N=2, field_name='usdm2'):
    # TODO: parametrizar para crear el valor de cualquier columna vecina
    poly_gdf['area'] = poly_gdf.to_crs(proj).geometry.area
    valid_geom_point = poly_gdf[['geometry','smp',field_name, 'area']].copy()
    valid_geom_point['geometry'] = valid_geom_point.geometry.apply(lambda geom: Point(geom.centroid.x,
                                                                                      geom.centroid.y))
    coords = np.stack(valid_geom_point.geometry.apply(lambda x: [x.x, x.y]))
    distance_matrix = ma.masked_where((dist := distance.cdist(*[coords] * 2)) == 0, dist)

    N_NEAREST = 2
    nearest_id_cols = list(map("nearest_id_{}".format, range(1, N_NEAREST + 1)))
    nearest_idx_cols = list(map("nearest_smp_{}".format, range(1, N_NEAREST + 1)))

    for c in nearest_id_cols:
        valid_geom_point[c] = None

    valid_geom_point[nearest_id_cols] = np.argsort(distance_matrix, axis=1)[:, :N_NEAREST]

    smp_ngbor_smp = dict(zip(valid_geom_point.reset_index().index, valid_geom_point['smp']))
    smp_ngbor_price = dict(zip(valid_geom_point.reset_index().index, valid_geom_point[field_name]))
    smp_ngbor_area = dict(zip(valid_geom_point.reset_index().index, valid_geom_point['area']))

    for i in range(1,N_NEAREST+1):
        smp_col = 'nearest_smp_{}'.format(i)
        price_col = 'nearest_price_{}'.format(i)
        area_col = 'nearest_area_{}'.format(i)
        valid_geom_point[smp_col] = valid_geom_point['nearest_id_{}'.format(i)].map(smp_ngbor_smp)
        valid_geom_point[price_col] = valid_geom_point['nearest_id_{}'.format(i)].map(smp_ngbor_price)
        valid_geom_point[area_col] = valid_geom_point['nearest_id_{}'.format(i)].map(smp_ngbor_area)
    return valid_geom_point
