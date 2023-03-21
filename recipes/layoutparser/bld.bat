
@REM Download Pre-trained model weights for PaddleDetect model
if not exist %RECIPE_DIR%\ppyolov2_r50vd_dcn_365e_publaynet.tar (
    curl https://paddle-model-ecology.bj.bcebos.com/model/layout-parser/ppyolov2_r50vd_dcn_365e_publaynet.tar -o %RECIPE_DIR%\ppyolov2_r50vd_dcn_365e_publaynet.tar
)
if not exist %PREFIX%\etc\ipypdf_models mkdir %PREFIX%\etc\ipypdf_models
tar -xvzf %RECIPE_DIR%\ppyolov2_r50vd_dcn_365e_publaynet.tar -C %PREFIX%\etc\ipypdf_models

python -m pip install ./layoutparser --no-deps
python -m pip install paddlepaddle-2.1.0-cp38-cp38-win_amd64.whl --no-deps
