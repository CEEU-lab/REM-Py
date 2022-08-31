import sys
import yaml
import os
from REM.properaty_data import *
from REM.datasources import *
from REM.models import *

def run(download_offer=False, area_clip='thiner', property_type='demolicion'):

    # PRECIOS DE OFERTA
    if download_offer:
        print('Downloading REAL ESTATE PRICES ...')
        print('')
        bbox = get_bbox_sur()
        query_sur = get_query(bbox, sd='2021-01-01',ed='2022-08-14')
        client = get_client()
        oferta_residencial = query_properati(client=client, query=query_sur)

        print('Download results')
        print('****************')
        print('Total avisos residenciales: {}'.format(len(oferta_residencial)))
        print('Superficie valida:')
        print(oferta_residencial['surface_total'].isna().value_counts())
        propiedades = gpd.GeoDataFrame(oferta_residencial, crs=4326,
                                       geometry=gpd.points_from_xy(oferta_residencial['longitud'],
                                                                   oferta_residencial['latitud']))

    # TODO: agregar otros recursos/datasets != Properati
    else:
        print('Using local path for REAL ESTATE PRICES')
        propiedades = read_local_properati(path='../data/oferta_residencial_properaty.csv')
        propiedades.start_date = pd.to_datetime(propiedades.start_date)

    # PARCELAS
    parcelas = caba_parcelas(source_idx=1) # por default lee directorio local. Conectar ACA a la DB
    if area_clip == 'thiner':
        mascara = BO_Area()
    elif area_clip == 'coarser':
        mascara = comunas(idx=[4,8]) # se pueden usar otras comunas tambien
    else:
        raiseValueError("El area de recorte debe ser superior o inferior")
    parcelas_sur = build_study_area(parcelas, mascara)

    ## PRECIOS OBSERVADOS POR PARCELA
    propiedades_target = properaty_observed_prices(propiedades, parcelas_sur, property_type)

    ref_price = propiedades_target.groupby('smp')[['price_adj','usdm2','usdm2_f']].mean()
    parcelas_sur['usdm2'] = parcelas_sur['smp'].map(ref_price['usdm2'])
    parcelas_sur['usdm2_f'] = parcelas_sur['smp'].map(ref_price['usdm2_f']) # asumiendo sup mediana
    parcelas_sur['price_adj'] = parcelas_sur['smp'].map(ref_price['price_adj'])

    # TODO 0.0: parametrizar el usdm2_left
    parcelas_cprecio = parcelas_sur[~parcelas_sur['usdm2'].isna()].copy()
    parcelas_sprecio = parcelas_sur[parcelas_sur['usdm2'].isna()].copy()

    # Configs: variables explicativas e hiperparametros
    with open(os.getenv('config', "..") + "/config/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    best_params = cfg['xgboost']['params'][0]
    expvars = cfg['xgboost']['expvars]']
    expvars_df = pd.read_csv('../data/sprecio_expvars.csv')

    to_predict = parcelas_sprecio.join(expvars_df)
    prediccion = xgb_regressor(to_predict_df, expvars, best_params)

    parcelas_sprecio['usdm2'] = prediccion
    predicted = pd.concat([parcelas_cprecio, parcelas_sprecio])
    predicted.to_file('../runs/sim_prices.geojson', driver='GeoJSON')

    print("SIMULACION FINALIZADA")
    print("**********************")
    print("IMPRIMIR METRICAS RESUMEN")
    return None

if __name__ == '__main__':

    # Run simulation with optional command-line arguments
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument("-do", "--download_offer", type=eval, default=False, help="Descarga oferta de Properati")
        parser.add_argument("-ac", "--area_clip", type=str, default='thiner', help="Define bbox para consulta avisos")
        parser.add_argument("-pt", "--property_type", type=str, default='demolicion', help="Define producto inmobiliario residencial o demolicion")
        args = parser.parse_args()

        download_offer = args.download_offer if args.download_offer else False
        area_clip = args.area_clip if args.area_clip else 'thiner'
        property_type = args.property_type if args.property_type else 'demolicion'

        run(download_offer, area_clip, property_type)

    else:
        run()
