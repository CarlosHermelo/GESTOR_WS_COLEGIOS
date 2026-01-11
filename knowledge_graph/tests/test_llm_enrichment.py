"""
Tests para el enriquecimiento LLM del Knowledge Graph.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.etl.llm_enrichment import LLMEnrichment


@pytest.fixture
def mock_neo4j():
    """Mock del cliente Neo4j."""
    client = MagicMock()
    client.execute = AsyncMock()
    client.execute_write = AsyncMock()
    return client


@pytest.fixture
def mock_llm_response():
    """Genera una respuesta mock del LLM."""
    def _create_response(content):
        response = MagicMock()
        response.content = content
        return response
    return _create_response


class TestClasificarPerfiles:
    """Tests para clasificación de perfiles de pagadores."""
    
    @pytest.mark.asyncio
    async def test_clasificar_perfil_puntual(self, mock_neo4j, mock_llm_response):
        """Test clasificación de pagador puntual."""
        # Setup
        mock_neo4j.execute.return_value = [
            {
                "erp_id": 1,
                "nombre": "Juan",
                "apellido": "Pérez",
                "pagos_totales": 12,
                "demora_promedio": 2.5,
                "demora_maxima": 5,
                "notif_ignoradas": 0,
                "tickets_creados": 0
            }
        ]
        
        llm_response = mock_llm_response(json.dumps({
            "perfil": "PUNTUAL",
            "nivel_riesgo": "BAJO",
            "razon": "Paga consistentemente a tiempo",
            "patrones": ["Pagador consistente", "Sin demoras significativas"]
        }))
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.clasificar_perfiles_pagadores()
        
        assert result == 1
        mock_neo4j.execute_write.assert_called()
    
    @pytest.mark.asyncio
    async def test_clasificar_perfil_moroso(self, mock_neo4j, mock_llm_response):
        """Test clasificación de pagador moroso."""
        mock_neo4j.execute.return_value = [
            {
                "erp_id": 2,
                "nombre": "Pedro",
                "apellido": "García",
                "pagos_totales": 8,
                "demora_promedio": 45.0,
                "demora_maxima": 90,
                "notif_ignoradas": 5,
                "tickets_creados": 2
            }
        ]
        
        llm_response = mock_llm_response(json.dumps({
            "perfil": "MOROSO",
            "nivel_riesgo": "ALTO",
            "razon": "Demoras frecuentes y prolongadas",
            "patrones": ["Paga tarde", "Ignora notificaciones"]
        }))
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.clasificar_perfiles_pagadores()
        
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_clasificar_maneja_json_invalido(self, mock_neo4j, mock_llm_response):
        """Test que maneja respuestas JSON inválidas."""
        mock_neo4j.execute.return_value = [
            {
                "erp_id": 3,
                "nombre": "María",
                "apellido": "López",
                "pagos_totales": 5,
                "demora_promedio": 10.0,
                "demora_maxima": 15,
                "notif_ignoradas": 1,
                "tickets_creados": 0
            }
        ]
        
        # Respuesta inválida
        llm_response = mock_llm_response("Esto no es JSON válido")
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.clasificar_perfiles_pagadores()
        
        # Debe continuar sin fallar
        assert result == 0  # No se clasificó ninguno
    
    @pytest.mark.asyncio
    async def test_clasificar_limpia_markdown(self, mock_neo4j, mock_llm_response):
        """Test que limpia código markdown de la respuesta."""
        mock_neo4j.execute.return_value = [
            {
                "erp_id": 4,
                "nombre": "Ana",
                "apellido": "Martínez",
                "pagos_totales": 6,
                "demora_promedio": 8.0,
                "demora_maxima": 12,
                "notif_ignoradas": 0,
                "tickets_creados": 1
            }
        ]
        
        # Respuesta con markdown
        json_content = json.dumps({
            "perfil": "EVENTUAL",
            "nivel_riesgo": "MEDIO",
            "razon": "Algunas demoras moderadas",
            "patrones": ["Pago eventual"]
        })
        llm_response = mock_llm_response(f"```json\n{json_content}\n```")
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.clasificar_perfiles_pagadores()
        
        assert result == 1


class TestGenerarClusters:
    """Tests para generación de clusters de comportamiento."""
    
    @pytest.mark.asyncio
    async def test_generar_cluster(self, mock_neo4j, mock_llm_response):
        """Test generación de cluster."""
        mock_neo4j.execute.return_value = [
            {
                "perfil": "MOROSO",
                "riesgo": "ALTO",
                "muestra_responsables": [
                    {"nombre": "Juan Pérez", "patrones": ["Paga tarde"]}
                ],
                "cantidad": 15
            }
        ]
        
        llm_response = mock_llm_response(json.dumps({
            "descripcion": "Grupo de alto riesgo con demoras frecuentes",
            "caracteristicas": ["Demoras > 30 días", "Ignoran notificaciones"],
            "recomendaciones": ["Llamada directa", "Plan de pagos"],
            "estrategia_comunicacion": "Mañanas entre semana"
        }))
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.generar_clusters_comportamiento()
        
        assert result == 1
        # Verificar que se creó el cluster
        assert mock_neo4j.execute_write.call_count >= 2  # Crear cluster + conectar


class TestGenerarInsights:
    """Tests para generación de insights predictivos."""
    
    @pytest.mark.asyncio
    async def test_generar_insights(self, mock_neo4j, mock_llm_response):
        """Test generación de insights."""
        mock_neo4j.execute.return_value = [
            {
                "total_responsables": 100,
                "alto_riesgo": 15,
                "medio_riesgo": 30,
                "morosos": 10,
                "puntuales": 60,
                "cuotas_vencidas": 25,
                "monto_vencido": 50000.0
            }
        ]
        
        llm_response = mock_llm_response(json.dumps({
            "tendencias": [
                "Incremento de 5% en morosidad",
                "Mayor puntualidad en grados superiores"
            ],
            "riesgos": [
                "15% de responsables en alto riesgo",
                "Posible deserción en casos críticos"
            ],
            "oportunidades": [
                "Implementar recordatorios automáticos",
                "Ofrecer planes de pago flexibles"
            ],
            "acciones": [
                "Contactar responsables de alto riesgo",
                "Revisar casos con 3+ cuotas vencidas"
            ]
        }))
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.generar_insights_predictivos()
        
        assert "insights" in result
        assert "tendencias" in result["insights"]
        assert "riesgos" in result["insights"]
    
    @pytest.mark.asyncio
    async def test_generar_insights_sin_datos(self, mock_neo4j):
        """Test cuando no hay datos para generar insights."""
        mock_neo4j.execute.return_value = []
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.generar_insights_predictivos()
        
        assert "error" in result


class TestEnrichAll:
    """Tests para el proceso completo de enriquecimiento."""
    
    @pytest.mark.asyncio
    async def test_enrich_all(self, mock_neo4j, mock_llm_response):
        """Test proceso completo de enriquecimiento."""
        # Mock para clasificación
        mock_neo4j.execute.side_effect = [
            # clasificar_perfiles
            [{
                "erp_id": 1,
                "nombre": "Test",
                "apellido": "User",
                "pagos_totales": 5,
                "demora_promedio": 5.0,
                "demora_maxima": 10,
                "notif_ignoradas": 0,
                "tickets_creados": 0
            }],
            # generar_clusters
            [{
                "perfil": "PUNTUAL",
                "riesgo": "BAJO",
                "muestra_responsables": [],
                "cantidad": 10
            }],
            # generar_insights
            [{
                "total_responsables": 100,
                "alto_riesgo": 10,
                "medio_riesgo": 20,
                "morosos": 5,
                "puntuales": 75,
                "cuotas_vencidas": 15,
                "monto_vencido": 30000.0
            }]
        ]
        
        llm_response = mock_llm_response(json.dumps({
            "perfil": "PUNTUAL",
            "nivel_riesgo": "BAJO",
            "razon": "Buen pagador",
            "patrones": []
        }))
        
        with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=llm_response)
            mock_get_llm.return_value = mock_llm
            
            enrichment = LLMEnrichment(mock_neo4j)
            result = await enrichment.enrich_all()
        
        assert "perfiles_clasificados" in result
        assert "clusters_generados" in result
        assert "insights_generados" in result


class TestProviderSwitch:
    """Tests para cambio de proveedor LLM."""
    
    @pytest.mark.asyncio
    async def test_usa_openai(self, mock_neo4j):
        """Test que usa OpenAI cuando está configurado."""
        with patch('app.etl.llm_enrichment.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.LLM_MODEL = "gpt-4o"
            
            with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
                enrichment = LLMEnrichment(mock_neo4j)
                _ = enrichment.llm
                
                mock_get_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_usa_google(self, mock_neo4j):
        """Test que usa Google Gemini cuando está configurado."""
        with patch('app.etl.llm_enrichment.settings') as mock_settings:
            mock_settings.LLM_PROVIDER = "google"
            mock_settings.LLM_MODEL = "gemini-2.0-flash-exp"
            
            with patch('app.etl.llm_enrichment.get_llm') as mock_get_llm:
                enrichment = LLMEnrichment(mock_neo4j)
                _ = enrichment.llm
                
                mock_get_llm.assert_called_once()

