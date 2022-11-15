# **R**eal**E**state**M**odeler

Templates para análisis de patrones inmobiliarios.

* Root

```
virtualenv venv --python=python3.10
source venv/bin/activate
pip install -r requirements.txt

```
* Develop mode

```
virtualenv venv --python=python3.10
source venv/bin/activate
python setup.py develop
pip install -r requirements-dev.txt

```

**Patrones de precios**

Aprender de precios observados para distintos productos inmobiliarios (terrenos, departamentos, alquileres, etc.) ...

![precios_observados](REM/img/observed_prices.png)

... y ensayar tasaciones a distintos niveles de agregación geográfica (parcelas, manzanas, etc.)

<p float="left">
  <img src="/REM/img/to_predict.png" width="200" />
  <img src="/REM/img/predicted.png" width="200" /> 
</p>
