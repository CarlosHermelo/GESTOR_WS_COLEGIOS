@echo off
echo ==============================================
echo DETENIENDO LOS DOCKERS DE LAS 4 CARPETAS
echo ==============================================

echo [1/4] Bajando ERP Mock...
cd erp_mock
docker-compose down
cd ..

echo [2/4] Bajando Gestor WS...
cd gestor_ws
docker-compose down
cd ..

echo [3/4] Bajando Frontend Admin...
cd frontend_admin
docker-compose down
cd ..

echo [4/4] Bajando Knowledge Graph...
cd knowledge_graph
docker-compose down
cd ..

echo ==============================================
echo TODOS LOS SERVICIOS HAN SIDO DETENIDOS
echo ==============================================
pause