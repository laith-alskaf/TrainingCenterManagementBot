"""
Meta Graph API adapter for Facebook and Instagram publishing.
"""
import logging
from typing import Optional
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    post_id: Optional[str] = None
    error_message: Optional[str] = None


class MetaGraphAdapter:
    """
    Adapter for Meta Graph API (Facebook and Instagram).
    
    Note: Instagram requires a valid public image URL.
    Text-only Instagram posts are not supported.
    """
    
    GRAPH_API_BASE = "https://graph.facebook.com/v18.0"
    
    def __init__(
        self,
        access_token: str,
        facebook_page_id: str,
        instagram_account_id: str,
    ):
        """
        Initialize the Meta Graph API adapter.
        
        Args:
            access_token: Meta Graph API access token
            facebook_page_id: Facebook Page ID
            instagram_account_id: Instagram Business Account ID
        """
        self._access_token = access_token
        self._facebook_page_id = facebook_page_id
        self._instagram_account_id = instagram_account_id
    
    async def publish_to_facebook(
        self,
        content: str,
        image_url: Optional[str] = None,
    ) -> PublishResult:
        """
        Publish a post to Facebook.
        
        Args:
            content: Post text content
            image_url: Optional public URL to an image
            
        Returns:
            PublishResult with success status and post ID
        """
        try:
            async with httpx.AsyncClient() as client:
                if image_url:
                    # Photo post
                    url = f"{self.GRAPH_API_BASE}/{self._facebook_page_id}/photos"
                    data = {
                        "url": image_url,
                        "caption": content,
                        "access_token": self._access_token,
                    }
                else:
                    # Text-only post
                    url = f"{self.GRAPH_API_BASE}/{self._facebook_page_id}/feed"
                    data = {
                        "message": content,
                        "access_token": self._access_token,
                    }
                
                response = await client.post(url, data=data)
                response_data = response.json()
                
                if response.status_code == 200 and "id" in response_data:
                    logger.info(f"Published to Facebook: {response_data['id']}")
                    return PublishResult(
                        success=True,
                        post_id=response_data['id']
                    )
                else:
                    error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"Facebook publish failed: {error_msg}")
                    return PublishResult(
                        success=False,
                        error_message=error_msg
                    )
                    
        except Exception as e:
            logger.error(f"Failed to publish to Facebook: {e}")
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    async def publish_to_instagram(
        self,
        image_url: str,
        caption: str,
    ) -> PublishResult:
        """
        Publish a post to Instagram.
        
        Note: Instagram requires a valid public image URL.
        
        Args:
            image_url: Public URL to the image (REQUIRED)
            caption: Post caption
            
        Returns:
            PublishResult with success status and post ID
        """
        if not image_url or not image_url.strip():
            return PublishResult(
                success=False,
                error_message="Instagram posts require a valid image_url"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                container_url = f"{self.GRAPH_API_BASE}/{self._instagram_account_id}/media"
                container_data = {
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": self._access_token,
                }
                
                container_response = await client.post(container_url, data=container_data)
                container_result = container_response.json()
                
                if "id" not in container_result:
                    error_msg = container_result.get('error', {}).get('message', 'Failed to create media container')
                    logger.error(f"Instagram container creation failed: {error_msg}")
                    return PublishResult(
                        success=False,
                        error_message=error_msg
                    )
                
                container_id = container_result['id']
                
                # Step 2: Publish the container
                publish_url = f"{self.GRAPH_API_BASE}/{self._instagram_account_id}/media_publish"
                publish_data = {
                    "creation_id": container_id,
                    "access_token": self._access_token,
                }
                
                publish_response = await client.post(publish_url, data=publish_data)
                publish_result = publish_response.json()
                
                if "id" in publish_result:
                    logger.info(f"Published to Instagram: {publish_result['id']}")
                    return PublishResult(
                        success=True,
                        post_id=publish_result['id']
                    )
                else:
                    error_msg = publish_result.get('error', {}).get('message', 'Failed to publish')
                    logger.error(f"Instagram publish failed: {error_msg}")
                    return PublishResult(
                        success=False,
                        error_message=error_msg
                    )
                    
        except Exception as e:
            logger.error(f"Failed to publish to Instagram: {e}")
            return PublishResult(
                success=False,
                error_message=str(e)
            )
    
    async def publish_post(
        self,
        content: str,
        platform: str,
        image_url: Optional[str] = None,
    ) -> dict:
        """
        Publish a post to specified platform(s).
        
        Args:
            content: Post content
            platform: 'facebook', 'instagram', or 'both'
            image_url: Optional image URL (required for Instagram)
            
        Returns:
            Dict with results for each platform
        """
        results = {}
        
        if platform in ('facebook', 'both'):
            results['facebook'] = await self.publish_to_facebook(content, image_url)
        
        if platform in ('instagram', 'both'):
            if not image_url:
                results['instagram'] = PublishResult(
                    success=False,
                    error_message="Instagram requires an image_url"
                )
            else:
                results['instagram'] = await self.publish_to_instagram(image_url, content)
        
        return results
