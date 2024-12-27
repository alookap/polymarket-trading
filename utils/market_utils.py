import requests
import logging
from typing import Optional

# 获取 logger
logger = logging.getLogger(__name__)

def get_market_slug(clob_token_ids: str) -> Optional[str]:
    """
    通过 clob_token_ids 获取对应的市场 slug
    
    Args:
        clob_token_ids: 市场 token ID
        
    Returns:
        str: 市场 slug
        None: 如果请求失败或数据不存在
    """
    try:
        base_url = "https://gamma-api.polymarket.com"
        endpoint = "/markets"
        url = f"{base_url}{endpoint}?clob_token_ids={clob_token_ids}"
        
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        
        market_data = response.json()
        return market_data[0]['slug'] if market_data else None
        
    except Exception as e:
        logger.error(f"获取市场 slug 失败: {str(e)}")
        return None
    

