"""
Tests para el LLM Factory.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.llm.factory import (
    get_llm,
    validate_llm_config,
    get_provider_info,
    OpenAIProvider,
    GoogleProvider,
    PROVIDERS
)


class TestLLMFactory:
    """Tests para el factory de LLM."""
    
    def test_providers_registered(self):
        """Test que los providers están registrados."""
        assert "openai" in PROVIDERS
        assert "google" in PROVIDERS
        assert len(PROVIDERS) == 2
    
    @patch('app.llm.factory.settings')
    def test_get_llm_openai(self, mock_settings):
        """Test obtener LLM de OpenAI."""
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.LLM_TEMPERATURE = 0.7
        mock_settings.LLM_MAX_TOKENS = 4000
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        
        with patch('app.llm.factory.ChatOpenAI') as mock_chat:
            mock_chat.return_value = MagicMock()
            llm = get_llm()
            
            mock_chat.assert_called_once_with(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=4000,
                api_key="sk-test-key"
            )
    
    @patch('app.llm.factory.settings')
    def test_get_llm_google(self, mock_settings):
        """Test obtener LLM de Google."""
        mock_settings.LLM_PROVIDER = "google"
        mock_settings.LLM_MODEL = "gemini-2.0-flash-exp"
        mock_settings.LLM_TEMPERATURE = 0.7
        mock_settings.LLM_MAX_TOKENS = 4000
        mock_settings.GOOGLE_API_KEY = "AIza-test-key"
        
        with patch('app.llm.factory.ChatGoogleGenerativeAI') as mock_chat:
            mock_chat.return_value = MagicMock()
            llm = get_llm()
            
            mock_chat.assert_called_once_with(
                model="gemini-2.0-flash-exp",
                temperature=0.7,
                max_output_tokens=4000,
                google_api_key="AIza-test-key"
            )
    
    @patch('app.llm.factory.settings')
    def test_get_llm_invalid_provider(self, mock_settings):
        """Test que falla con provider inválido."""
        mock_settings.LLM_PROVIDER = "invalid_provider"
        
        with pytest.raises(ValueError) as excinfo:
            get_llm()
        
        assert "no válido" in str(excinfo.value)
        assert "invalid_provider" in str(excinfo.value)
    
    @patch('app.llm.factory.settings')
    def test_get_provider_info(self, mock_settings):
        """Test obtener información del provider."""
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.LLM_TEMPERATURE = 0.7
        mock_settings.LLM_MAX_TOKENS = 4000
        
        info = get_provider_info()
        
        assert info["provider"] == "openai"
        assert info["model"] == "gpt-4o"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 4000
        assert "openai" in info["available_providers"]
        assert "google" in info["available_providers"]


class TestOpenAIProvider:
    """Tests para OpenAIProvider."""
    
    @patch('app.llm.factory.settings')
    def test_validate_config_success(self, mock_settings):
        """Test validación exitosa."""
        mock_settings.OPENAI_API_KEY = "sk-test-key"
        
        provider = OpenAIProvider()
        assert provider.validate_config() is True
    
    @patch('app.llm.factory.settings')
    def test_validate_config_missing_key(self, mock_settings):
        """Test que falla sin API key."""
        mock_settings.OPENAI_API_KEY = None
        
        provider = OpenAIProvider()
        
        with pytest.raises(ValueError) as excinfo:
            provider.validate_config()
        
        assert "OPENAI_API_KEY" in str(excinfo.value)
    
    def test_provider_name(self):
        """Test nombre del provider."""
        provider = OpenAIProvider()
        assert provider.provider_name == "OpenAI"


class TestGoogleProvider:
    """Tests para GoogleProvider."""
    
    @patch('app.llm.factory.settings')
    def test_validate_config_success(self, mock_settings):
        """Test validación exitosa."""
        mock_settings.GOOGLE_API_KEY = "AIza-test-key"
        
        provider = GoogleProvider()
        assert provider.validate_config() is True
    
    @patch('app.llm.factory.settings')
    def test_validate_config_missing_key(self, mock_settings):
        """Test que falla sin API key."""
        mock_settings.GOOGLE_API_KEY = None
        
        provider = GoogleProvider()
        
        with pytest.raises(ValueError) as excinfo:
            provider.validate_config()
        
        assert "GOOGLE_API_KEY" in str(excinfo.value)
    
    def test_provider_name(self):
        """Test nombre del provider."""
        provider = GoogleProvider()
        assert provider.provider_name == "Google"


class TestFactorySwitch:
    """Tests para cambio entre providers."""
    
    @patch('app.llm.factory.settings')
    @patch('app.llm.factory.ChatOpenAI')
    @patch('app.llm.factory.ChatGoogleGenerativeAI')
    def test_switch_between_providers(
        self,
        mock_google,
        mock_openai,
        mock_settings
    ):
        """Test cambio entre OpenAI y Google."""
        mock_openai.return_value = MagicMock(name="OpenAI")
        mock_google.return_value = MagicMock(name="Google")
        
        # OpenAI
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_MODEL = "gpt-4o"
        mock_settings.LLM_TEMPERATURE = 0.7
        mock_settings.LLM_MAX_TOKENS = 4000
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.GOOGLE_API_KEY = "AIza-test"
        
        llm_openai = get_llm()
        mock_openai.assert_called()
        
        # Google
        mock_settings.LLM_PROVIDER = "google"
        mock_settings.LLM_MODEL = "gemini-2.0-flash-exp"
        
        llm_google = get_llm()
        mock_google.assert_called()

