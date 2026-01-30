
@echo off

echo ==============================================
echo LEVANTANDO LOS SERVIDORES MCP TOOLS Y GESTOR WS
echo ==============================================
echo [1/2] Local (el servidor ya está corriendo en puerto 8003):
cd mcp_tools
python run_local.py
echo [2/2] Con Docker (integrado):
echo cd gestor_ws
echo docker-compose up --build



echo ==============================================
echo LEVANTANDO LOS DOCKERS DE LAS 4 CARPETAS
echo ==============================================

echo [1/4] Levantando ERP Mock...
cd erp_mock
docker-compose up -d
cd ..

echo [2/4] Levantando Gestor WS...
cd gestor_ws
docker-compose up -d
cd ..

echo [3/4] Levantando Frontend Admin...
cd frontend_admin
docker-compose up -d
cd ..

echo [4/4] Levantando Knowledge Graph...
cd knowledge_graph
docker-compose up -d
cd ..

echo ==============================================
echo ESTADO FINAL DE LOS SERVICIOS:
echo ==============================================
docker ps
pause