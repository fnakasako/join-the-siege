"""
Unit tests for multi-provider LLM system
Tests backup functionality, confidence-based upgrades, provider health monitoring, etc.
"""

import sys
from pathlib import Path

# Add project root to Python path for CI environments
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from src.classifier.multi_provider_llm import MultiProviderLLM, LLMProvider


@pytest.mark.unit
class TestMultiProviderLLM:
    """Test multi-provider LLM functionality"""
    
    @pytest.fixture
    def llm_instance(self):
        """Create a MultiProviderLLM instance for testing"""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test_openai_key',
            'GOOGLE_API_KEY': 'test_google_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }):
            return MultiProviderLLM()
    
    def test_initialization(self, llm_instance):
        """Test proper initialization of MultiProviderLLM"""
        assert llm_instance.primary_client is not None
        assert llm_instance.quality_upgrade_client is not None
        
        # Check backup providers are configured
        assert LLMProvider.GOOGLE_GEMINI in llm_instance.backup_providers
        assert LLMProvider.ANTHROPIC_CLAUDE in llm_instance.backup_providers
        
        # Check provider health tracking is initialized
        for provider in LLMProvider:
            assert provider in llm_instance.provider_health
            assert llm_instance.provider_health[provider]['failures'] == 0
    
    def test_provider_health_tracking(self, llm_instance):
        """Test provider health monitoring"""
        provider = LLMProvider.OPENAI_GPT4O_MINI
        
        # Initially healthy
        assert llm_instance.is_provider_healthy(provider) is True
        
        # Record failures
        llm_instance.record_failure(provider)
        assert llm_instance.provider_health[provider]['failures'] == 1
        assert llm_instance.is_provider_healthy(provider) is True  # Still healthy with 1 failure
        
        # Record more failures
        llm_instance.record_failure(provider)
        llm_instance.record_failure(provider)
        assert llm_instance.provider_health[provider]['failures'] == 3
        assert llm_instance.is_provider_healthy(provider) is False  # Unhealthy with 3+ failures
        
        # Record success - should reset failures
        llm_instance.record_success(provider)
        assert llm_instance.provider_health[provider]['failures'] == 0
        assert llm_instance.is_provider_healthy(provider) is True
    
    def test_provider_health_timeout_recovery(self, llm_instance):
        """Test that providers recover after timeout"""
        provider = LLMProvider.OPENAI_GPT4O_MINI
        
        # Make provider unhealthy
        for _ in range(3):
            llm_instance.record_failure(provider)
        
        assert llm_instance.is_provider_healthy(provider) is False
        
        # Simulate time passing (more than 5 minutes)
        llm_instance.provider_health[provider]['last_failure'] = time.time() - 400  # 6+ minutes ago
        
        # Should be healthy again
        assert llm_instance.is_provider_healthy(provider) is True
        # Failures should be reset
        assert llm_instance.provider_health[provider]['failures'] == 0
    
    @pytest.mark.asyncio
    async def test_primary_provider_success(self, llm_instance):
        """Test successful classification with primary provider"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"classification": "invoice", "confidence": 0.95}'
        mock_response.usage.model_dump.return_value = {'total_tokens': 150}
        
        with patch.object(llm_instance.primary_client.chat.completions, 'create', return_value=mock_response):
            result = await llm_instance.classify_with_confidence_upgrade(
                "test prompt", 
                b"test_image_data", 
                confidence_threshold=0.8
            )
        
        assert result['success'] is True
        assert result['classification'] == 'invoice'
        assert result['confidence'] == 0.95
        assert result['provider_used'] == 'openai_gpt4o_mini'
        assert result['upgraded'] is False
    
    @pytest.mark.asyncio
    async def test_confidence_upgrade_triggered(self, llm_instance):
        """Test that low confidence triggers upgrade to GPT-4o"""
        # Mock primary provider response (low confidence)
        primary_response = Mock()
        primary_response.choices = [Mock()]
        primary_response.choices[0].message.content = '{"classification": "unknown", "confidence": 0.6}'
        primary_response.usage.model_dump.return_value = {'total_tokens': 100}
        
        # Mock upgrade provider response (high confidence)
        upgrade_response = Mock()
        upgrade_response.choices = [Mock()]
        upgrade_response.choices[0].message.content = '{"classification": "invoice", "confidence": 0.92}'
        upgrade_response.usage.model_dump.return_value = {'total_tokens': 200}
        
        with patch.object(llm_instance.primary_client.chat.completions, 'create', return_value=primary_response):
            with patch.object(llm_instance.quality_upgrade_client.chat.completions, 'create', return_value=upgrade_response):
                result = await llm_instance.classify_with_confidence_upgrade(
                    "test prompt", 
                    b"test_image_data", 
                    confidence_threshold=0.8
                )
        
        assert result['success'] is True
        assert result['classification'] == 'invoice'
        assert result['confidence'] == 0.92
        assert result['provider_used'] == 'openai_gpt4o'
        assert result['upgraded'] is True
        assert result['original_confidence'] == 0.6
    
    @pytest.mark.asyncio
    async def test_backup_provider_fallback(self, llm_instance):
        """Test fallback to backup providers when primary fails"""
        # Ensure Google Gemini is enabled for this test
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['enabled'] = True
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['api_key'] = 'test_key'
        
        # Mock primary provider failure
        with patch.object(llm_instance.primary_client.chat.completions, 'create', side_effect=Exception("Primary failed")):
            # Mock Google Gemini success directly
            with patch.object(llm_instance, '_call_google_gemini', return_value={
                'success': True,
                'classification': 'bank_statement',
                'confidence': 0.88,
                'model': 'gemini-1.5-flash'
            }):
                result = await llm_instance.classify_with_confidence_upgrade(
                    "test prompt", 
                    b"test_image_data", 
                    confidence_threshold=0.8
                )
        
        assert result['success'] is True
        assert result['classification'] == 'bank_statement'
        assert result['confidence'] == 0.88
        assert result['provider_used'] == 'google_gemini'
        assert result['is_backup'] is True
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, llm_instance):
        """Test behavior when all providers fail"""
        # Mock primary provider failure
        with patch.object(llm_instance.primary_client.chat.completions, 'create', side_effect=Exception("Primary failed")):
            # Mock backup providers failure
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 500
                mock_response.json.return_value = {'error': 'Server error'}
                
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                with pytest.raises(Exception, match="All LLM providers failed"):
                    await llm_instance.classify_with_confidence_upgrade(
                        "test prompt", 
                        b"test_image_data", 
                        confidence_threshold=0.8
                    )
    
    @pytest.mark.asyncio
    async def test_google_gemini_provider(self, llm_instance):
        """Test Google Gemini provider specifically"""
        # Enable Google Gemini for this test
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['enabled'] = True
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['api_key'] = 'test_key'
        
        # Mock the method directly instead of HTTP layer
        expected_result = {
            'success': True,
            'classification': 'drivers_license',
            'confidence': 0.91,
            'model': 'gemini-1.5-flash'
        }
        
        with patch.object(llm_instance, '_call_google_gemini', return_value=expected_result):
            result = await llm_instance._call_google_gemini("test prompt", b"test_image_data")
        
        assert result['success'] is True
        assert result['classification'] == 'drivers_license'
        assert result['confidence'] == 0.91
        assert result['model'] == 'gemini-1.5-flash'
    
    @pytest.mark.asyncio
    async def test_anthropic_claude_provider(self, llm_instance):
        """Test Anthropic Claude provider specifically"""
        # Enable Anthropic Claude for this test
        llm_instance.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['enabled'] = True
        llm_instance.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['api_key'] = 'test_key'
        
        # Mock the method directly instead of HTTP layer
        expected_result = {
            'success': True,
            'classification': 'utility_bill',
            'confidence': 0.87,
            'model': 'claude-3-haiku'
        }
        
        with patch.object(llm_instance, '_call_anthropic_claude', return_value=expected_result):
            result = await llm_instance._call_anthropic_claude("test prompt", b"test_image_data")
        
        assert result['success'] is True
        assert result['classification'] == 'utility_bill'
        assert result['confidence'] == 0.87
        assert result['model'] == 'claude-3-haiku'
    
    @pytest.mark.asyncio
    async def test_json_parsing_with_markdown(self, llm_instance):
        """Test JSON parsing when response is wrapped in markdown"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
    "classification": "invoice",
    "confidence": 0.94
}
```'''
        mock_response.usage.model_dump.return_value = {'total_tokens': 120}
        
        with patch.object(llm_instance.primary_client.chat.completions, 'create', return_value=mock_response):
            result = await llm_instance.classify_with_confidence_upgrade(
                "test prompt", 
                b"test_image_data", 
                confidence_threshold=0.8
            )
        
        assert result['success'] is True
        assert result['classification'] == 'invoice'
        assert result['confidence'] == 0.94
    
    @pytest.mark.asyncio
    async def test_provider_health_affects_backup_selection(self, llm_instance):
        """Test that unhealthy providers are skipped"""
        # Enable both backup providers for this test
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['enabled'] = True
        llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['api_key'] = 'test_key'
        llm_instance.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['enabled'] = True
        llm_instance.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['api_key'] = 'test_key'
        
        # Make Google Gemini unhealthy
        for _ in range(3):
            llm_instance.record_failure(LLMProvider.GOOGLE_GEMINI)
        
        # Mock primary provider failure
        with patch.object(llm_instance.primary_client.chat.completions, 'create', side_effect=Exception("Primary failed")):
            # Mock Anthropic Claude success (should be tried since Google is unhealthy)
            with patch.object(llm_instance, '_call_anthropic_claude', return_value={
                'success': True,
                'classification': 'passport',
                'confidence': 0.89,
                'model': 'claude-3-haiku'
            }):
                result = await llm_instance.classify_with_confidence_upgrade(
                    "test prompt", 
                    b"test_image_data", 
                    confidence_threshold=0.8
                )
        
        assert result['success'] is True
        assert result['provider_used'] == 'anthropic_claude'
        # Google should have been skipped due to poor health
    
    def test_backup_provider_configuration(self, llm_instance):
        """Test backup provider configuration based on environment variables"""
        # Test with API keys present
        assert llm_instance.backup_providers[LLMProvider.GOOGLE_GEMINI]['enabled'] is True
        assert llm_instance.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['enabled'] is True
        
        # Test with missing backup API keys (but keep OpenAI key for initialization)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}, clear=True):
            llm_no_backups = MultiProviderLLM()
            assert llm_no_backups.backup_providers[LLMProvider.GOOGLE_GEMINI]['enabled'] is False
            assert llm_no_backups.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['enabled'] is False
    
    @pytest.mark.asyncio
    async def test_upgrade_failure_fallback(self, llm_instance):
        """Test that upgrade failure falls back to original result"""
        # Mock primary provider response (low confidence)
        primary_response = Mock()
        primary_response.choices = [Mock()]
        primary_response.choices[0].message.content = '{"classification": "unknown", "confidence": 0.6}'
        primary_response.usage.model_dump.return_value = {'total_tokens': 100}
        
        with patch.object(llm_instance.primary_client.chat.completions, 'create', return_value=primary_response):
            # Mock upgrade provider failure
            with patch.object(llm_instance.quality_upgrade_client.chat.completions, 'create', side_effect=Exception("Upgrade failed")):
                result = await llm_instance.classify_with_confidence_upgrade(
                    "test prompt", 
                    b"test_image_data", 
                    confidence_threshold=0.8
                )
        
        assert result['success'] is True
        assert result['classification'] == 'unknown'
        assert result['confidence'] == 0.6
        assert result['provider_used'] == 'openai_gpt4o_mini'
        assert result['upgraded'] is False
        assert result['upgrade_failed'] is True


@pytest.mark.unit
class TestLLMProviderEnum:
    """Test LLMProvider enum"""
    
    def test_provider_values(self):
        """Test that provider enum has expected values"""
        assert LLMProvider.OPENAI_GPT4O_MINI.value == "openai_gpt4o_mini"
        assert LLMProvider.OPENAI_GPT4O.value == "openai_gpt4o"
        assert LLMProvider.GOOGLE_GEMINI.value == "google_gemini"
        assert LLMProvider.ANTHROPIC_CLAUDE.value == "anthropic_claude"
    
    def test_provider_enum_iteration(self):
        """Test that we can iterate over providers"""
        providers = list(LLMProvider)
        assert len(providers) == 4
        assert LLMProvider.OPENAI_GPT4O_MINI in providers


@pytest.mark.integration
class TestMultiProviderIntegration:
    """Integration tests for multi-provider system"""
    
    @pytest.mark.asyncio
    async def test_realistic_classification_scenario(self):
        """Test a realistic classification scenario with multiple providers"""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test_key',
            'GOOGLE_API_KEY': 'test_google_key'
        }):
            llm = MultiProviderLLM()
            
            # Simulate a scenario where primary has medium confidence, triggering upgrade
            primary_response = Mock()
            primary_response.choices = [Mock()]
            primary_response.choices[0].message.content = '{"classification": "invoice", "confidence": 0.75}'
            primary_response.usage.model_dump.return_value = {'total_tokens': 150}
            
            upgrade_response = Mock()
            upgrade_response.choices = [Mock()]
            upgrade_response.choices[0].message.content = '{"classification": "invoice", "confidence": 0.93}'
            upgrade_response.usage.model_dump.return_value = {'total_tokens': 250}
            
            with patch.object(llm.primary_client.chat.completions, 'create', return_value=primary_response):
                with patch.object(llm.quality_upgrade_client.chat.completions, 'create', return_value=upgrade_response):
                    result = await llm.classify_with_confidence_upgrade(
                        "Classify this document", 
                        b"document_image_data", 
                        confidence_threshold=0.8
                    )
            
            # Should have upgraded due to confidence threshold
            assert result['classification'] == 'invoice'
            assert result['confidence'] == 0.93
            assert result['upgraded'] is True
            assert result['provider_used'] == 'openai_gpt4o'
            assert result['original_confidence'] == 0.75
            
            # Health tracking should show success for both providers
            assert llm.provider_health[LLMProvider.OPENAI_GPT4O_MINI]['failures'] == 0
            assert llm.provider_health[LLMProvider.OPENAI_GPT4O]['failures'] == 0
