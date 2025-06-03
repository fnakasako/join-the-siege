import os
import json
import base64
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from enum import Enum
import random
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(Enum):
    OPENAI_GPT4O_MINI = "openai_gpt4o_mini"
    OPENAI_GPT4O = "openai_gpt4o"
    GOOGLE_GEMINI = "google_gemini"
    ANTHROPIC_CLAUDE = "anthropic_claude"

class MultiProviderLLM:
    def __init__(self):
        # Primary provider (GPT-4o-mini)
        self.primary_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Backup providers
        self.backup_providers = {
            LLMProvider.GOOGLE_GEMINI: {
                'api_key': os.getenv('GOOGLE_API_KEY'),
                'enabled': bool(os.getenv('GOOGLE_API_KEY'))
            },
            LLMProvider.ANTHROPIC_CLAUDE: {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'enabled': bool(os.getenv('ANTHROPIC_API_KEY'))
            }
        }
        
        # Quality upgrade provider (GPT-4o)
        self.quality_upgrade_client = OpenAI(api_key=os.getenv('OPENAI_GPT4O_API_KEY', os.getenv('OPENAI_API_KEY')))
        
        # Provider health tracking
        self.provider_health = {
            LLMProvider.OPENAI_GPT4O_MINI: {'failures': 0, 'last_failure': 0},
            LLMProvider.OPENAI_GPT4O: {'failures': 0, 'last_failure': 0},
            LLMProvider.GOOGLE_GEMINI: {'failures': 0, 'last_failure': 0},
            LLMProvider.ANTHROPIC_CLAUDE: {'failures': 0, 'last_failure': 0}
        }
    
    def is_provider_healthy(self, provider: LLMProvider) -> bool:
        """Check if provider is healthy (circuit breaker pattern)"""
        health = self.provider_health[provider]
        
        # If less than 3 failures, provider is healthy
        if health['failures'] < 3:
            return True
        
        # If more than 5 minutes since last failure, reset and try again
        if time.time() - health['last_failure'] > 300:  # 5 minutes
            health['failures'] = 0
            return True
        
        return False
    
    def record_success(self, provider: LLMProvider):
        """Record successful API call"""
        self.provider_health[provider]['failures'] = 0
    
    def record_failure(self, provider: LLMProvider):
        """Record failed API call"""
        self.provider_health[provider]['failures'] += 1
        self.provider_health[provider]['last_failure'] = time.time()
    
    async def classify_with_confidence_upgrade(
        self, 
        prompt: str, 
        image_data: bytes,
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Classify with automatic quality upgrade if confidence is low
        
        Flow:
        1. Try GPT-4o-mini first (fast, cheap)
        2. If confidence < threshold OR classification is 'unknown', upgrade to GPT-4o
        3. If primary fails (including rate limits), try backup providers
        4. If 'unknown' result, try backup providers
        """
        
        # Step 1: Try primary provider (GPT-4o-mini)
        try:
            result = await self._call_openai_gpt4o_mini(prompt, image_data)
            
            if result['success']:
                self.record_success(LLMProvider.OPENAI_GPT4O_MINI)
                
                # Check confidence level and classification
                confidence = result.get('confidence', 0.0)
                classification = result.get('classification', 'unknown')
                
                # Upgrade conditions: low confidence OR unknown classification
                should_upgrade = (
                    confidence < confidence_threshold or 
                    classification == 'unknown'
                )
                
                if not should_upgrade:
                    result['provider_used'] = 'openai_gpt4o_mini'
                    result['upgraded'] = False
                    return result
                else:
                    # Low confidence or unknown - upgrade to GPT-4o
                    reason = "unknown classification" if classification == 'unknown' else f"low confidence ({confidence:.2f})"
                    print(f"{reason} - upgrading to GPT-4o")
                    upgrade_result = await self._call_openai_gpt4o(prompt, image_data)
                    
                    if upgrade_result['success']:
                        self.record_success(LLMProvider.OPENAI_GPT4O)
                        upgrade_result['provider_used'] = 'openai_gpt4o'
                        upgrade_result['upgraded'] = True
                        upgrade_result['upgrade_reason'] = reason
                        upgrade_result['original_confidence'] = confidence
                        upgrade_result['original_classification'] = classification
                        
                        # If still unknown after upgrade, try backup providers
                        if upgrade_result.get('classification') == 'unknown':
                            print("Still unknown after GPT-4o upgrade, trying backup providers")
                            backup_result = await self._try_backup_providers(prompt, image_data)
                            if backup_result and backup_result.get('classification') != 'unknown':
                                backup_result['upgraded'] = True
                                backup_result['upgrade_reason'] = "unknown after GPT-4o"
                                return backup_result
                        
                        return upgrade_result
                    else:
                        # Upgrade failed, try backup providers
                        print("GPT-4o upgrade failed, trying backup providers")
                        backup_result = await self._try_backup_providers(prompt, image_data)
                        if backup_result:
                            return backup_result
                        
                        # All upgrades failed, return original result
                        result['provider_used'] = 'openai_gpt4o_mini'
                        result['upgraded'] = False
                        result['upgrade_failed'] = True
                        return result
            else:
                self.record_failure(LLMProvider.OPENAI_GPT4O_MINI)
                raise Exception(f"Primary provider failed: {result.get('error')}")
                
        except Exception as e:
            error_str = str(e)
            print(f"Primary provider (GPT-4o-mini) failed: {error_str}")
            self.record_failure(LLMProvider.OPENAI_GPT4O_MINI)
            
            # Check if it's a rate limit error
            if "rate limit" in error_str.lower() or "429" in error_str:
                print("Rate limit detected, immediately trying backup providers")
        
        # Step 2: Try backup providers
        backup_result = await self._try_backup_providers(prompt, image_data)
        if backup_result:
            return backup_result
        
        # All providers failed
        raise Exception("All LLM providers failed")
    
    async def _try_backup_providers(self, prompt: str, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Try backup providers in order"""
        backup_order = [LLMProvider.GOOGLE_GEMINI, LLMProvider.ANTHROPIC_CLAUDE]
        
        for provider in backup_order:
            if not self.backup_providers[provider]['enabled']:
                continue
                
            if not self.is_provider_healthy(provider):
                continue
            
            try:
                print(f"Trying backup provider: {provider.value}")
                
                if provider == LLMProvider.GOOGLE_GEMINI:
                    result = await self._call_google_gemini(prompt, image_data)
                elif provider == LLMProvider.ANTHROPIC_CLAUDE:
                    result = await self._call_anthropic_claude(prompt, image_data)
                
                if result['success']:
                    self.record_success(provider)
                    result['provider_used'] = provider.value
                    result['is_backup'] = True
                    return result
                else:
                    self.record_failure(provider)
                    print(f"Backup provider {provider.value} failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"Backup provider {provider.value} failed: {e}")
                self.record_failure(provider)
        
        return None
    
    async def _call_openai_gpt4o_mini(self, prompt: str, image_data: bytes) -> Dict[str, Any]:
        """Call OpenAI GPT-4o-mini"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            response = self.primary_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,  # Reduced to save tokens
                temperature=0.05  # Lower temperature for more consistent results
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            
            result = json.loads(content.strip())
            
            return {
                'success': True,
                'classification': result.get('classification', 'unknown'),
                'confidence': float(result.get('confidence', 0.0)),
                'model': 'gpt-4o-mini',
                'usage': response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _call_openai_gpt4o(self, prompt: str, image_data: bytes) -> Dict[str, Any]:
        """Call OpenAI GPT-4o for quality upgrade"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            response = self.quality_upgrade_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            
            result = json.loads(content.strip())
            
            return {
                'success': True,
                'classification': result.get('classification', 'unknown'),
                'confidence': float(result.get('confidence', 0.0)),
                'model': 'gpt-4o',
                'usage': response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _call_google_gemini(self, prompt: str, image_data: bytes) -> Dict[str, Any]:
        """Call Google Gemini as backup"""
        try:
            api_key = self.backup_providers[LLMProvider.GOOGLE_GEMINI]['api_key']
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Gemini API call
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['candidates'][0]['content']['parts'][0]['text']
                        
                        # Parse JSON response
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        
                        result = json.loads(content.strip())
                        
                        return {
                            'success': True,
                            'classification': result.get('classification', 'unknown'),
                            'confidence': float(result.get('confidence', 0.0)),
                            'model': 'gemini-1.5-flash'
                        }
                    else:
                        error_data = await response.json()
                        return {
                            'success': False,
                            'error': f"Gemini API error: {error_data}"
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _call_anthropic_claude(self, prompt: str, image_data: bytes) -> Dict[str, Any]:
        """Call Anthropic Claude as backup"""
        try:
            api_key = self.backup_providers[LLMProvider.ANTHROPIC_CLAUDE]['api_key']
            
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Claude API call
            url = "https://api.anthropic.com/v1/messages"
            
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "temperature": 0.1,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        }
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data['content'][0]['text']
                        
                        # Parse JSON response
                        if '```json' in content:
                            content = content.split('```json')[1].split('```')[0]
                        
                        result = json.loads(content.strip())
                        
                        return {
                            'success': True,
                            'classification': result.get('classification', 'unknown'),
                            'confidence': float(result.get('confidence', 0.0)),
                            'model': 'claude-3-haiku'
                        }
                    else:
                        error_data = await response.json()
                        return {
                            'success': False,
                            'error': f"Claude API error: {error_data}"
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
multi_provider_llm = MultiProviderLLM()
