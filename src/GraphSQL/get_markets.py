import requests
import json
from dotenv import load_dotenv
import os

def fetch_polymarket_data(first=5):
    """
    get Polymarket splits and merges data
    
    Args:
        first (int): number of records
    
    Returns:
        dict
    """
    load_dotenv()
    api_key=os.getenv("CLOB_API_KEY")
    # GraphQL endpoint
    url = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/Bx1W4S7kDVxs9gC3s2G6DS8kdNBJNVhMviCtin2DiBp"
    
    # 查询语句
    query = """
    {
        splits(first: %d) {
            id
            timestamp
            stakeholder
            condition
        }
        merges(first: %d) {
            id
            timestamp
            stakeholder
            condition
        }
    }
    """ % (first, first)
    
    # set headers
    headers = {
        'Content-Type': 'application/json',
    }
    
    data = {
        'query': query
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON Error: {e}")
        return None

if __name__ == "__main__":
    result = fetch_polymarket_data(first=5)
    
    if result:
        print("Query Results:")
        print(json.dumps(result, indent=2, ensure_ascii=False))