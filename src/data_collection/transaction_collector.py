from pathlib import Path
import pandas as pd
from web3 import Web3
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from eth_abi import decode
from hexbytes import HexBytes

@dataclass
class Config:
    """配置数据类"""
    api_endpoint: str
    api_key: str
    data_path: Path
    metadata_path: Path
    contract_address: str

class BlockchainConnector:
    """处理与区块链交互的基础类"""
    def __init__(self, config: Config):
        self.w3 = Web3(Web3.HTTPProvider(f"{config.api_endpoint}{config.api_key}"))
        self.contract_address = Web3.to_checksum_address(config.contract_address)

    def get_logs(self, filter_params: Dict) -> List:
        """获取区块链日志"""
        return self.w3.eth.get_logs(filter_params)

class EventDecoder:
    """事件解码器类"""
    def __init__(self):
        self.order_filled_signature = '0x' + Web3.keccak(
            text="OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
        ).hex()

    def decode_order_filled_event(self, event: Dict) -> Dict:
        """解码OrderFilled事件"""
        try:
            data = HexBytes(event['data'])
            decoded_data = decode(
                ['uint256', 'uint256', 'uint256', 'uint256', 'uint256'],
                data
            )
            
            return {
                'orderHash': event['topics'][1].hex(),
                'maker': '0x' + event['topics'][2].hex()[-40:],
                'taker': '0x' + event['topics'][3].hex()[-40:],
                'makerAssetId': decoded_data[0],
                'takerAssetId': decoded_data[1],
                'makerAmountFilled': decoded_data[2],
                'takerAmountFilled': decoded_data[3],
                'fee': decoded_data[4],
                'transactionHash': event['transactionHash'].hex(),
                'blockNumber': event['blockNumber']
            }
        except Exception as e:
            print(f"Error decoding event: {e}")
            raise

class DataProcessor:
    """数据处理类"""
    def __init__(self, contract_address: str):
        self.contract_address = contract_address

    def create_dataframe(self, events_data: List[Dict]) -> pd.DataFrame:
        """将事件数据转换为DataFrame"""
        if not events_data:
            return pd.DataFrame()

        df = pd.DataFrame(events_data)
        return self._process_dataframe(df)

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理DataFrame数据"""
        columns_order = [
            'blockNumber', 'transactionHash', 'orderHash', 'maker', 'taker',
            'makerAssetId', 'takerAssetId', 'makerAmountFilled', 'takerAmountFilled', 'fee'
        ]
        
        df = df[columns_order]
        
        df['makerAmountFilled'] = df['makerAmountFilled'] / 1e6
        df['takerAmountFilled'] = df['takerAmountFilled'] / 1e6
        
        df = df[
            (df['taker'] != self.contract_address) & 
            (df['maker'] != self.contract_address)
        ]
        
        df['direction'] = df.apply(self._get_direction, axis=1)
        df['price'] = df.apply(self._calculate_price, axis=1)
        
        return df

    @staticmethod
    def _get_direction(row: pd.Series) -> str:
        """判断交易方向"""
        if row['makerAssetId'] == 0:
            return 'sell'
        elif row['takerAssetId'] == 0:
            return 'buy'
        return 'unknown'

    @staticmethod
    def _calculate_price(row: pd.Series) -> Optional[float]:
        """计算交易价格"""
        if row['makerAssetId'] == 0:
            return row['makerAmountFilled'] / row['takerAmountFilled']
        elif row['takerAssetId'] == 0:
            return row['takerAmountFilled'] / row['makerAmountFilled']
        return None

class TransactionDataCollector:
    """主要数据收集类"""
    def __init__(self, config: Config):
        self.config = config
        self.blockchain = BlockchainConnector(config)
        self.decoder = EventDecoder()
        self.processor = DataProcessor(config.contract_address) # Non-checksumed
        self.checksum_address = Web3.to_checksum_address(config.contract_address)
        
        # 创建必要的目录
        self.config.data_path.mkdir(parents=True, exist_ok=True)
        self.config.metadata_path.mkdir(parents=True, exist_ok=True)

    def get_logs_in_batches(self, from_block: int, to_block: int, batch_size: int = 1000) -> List:
        """分批获取事件日志"""
        logs = []
        current_block = from_block
        
        while current_block <= to_block:
            batch_size = min(batch_size, 1000)
            end_block = min(current_block + batch_size - 1, to_block)
            
            try:
                filter_params = {
                    'fromBlock': current_block,
                    'toBlock': end_block,
                    'address': [self.checksum_address],
                    'topics': [[self.decoder.order_filled_signature]]
                }
                
                print(f"Fetching logs from block {current_block} to {end_block}")
                batch_logs = self.blockchain.get_logs(filter_params)
                logs.extend(batch_logs)
                print(f"Found {len(batch_logs)} logs in this batch")
                
            except Exception as e:
                print(f"Error fetching logs: {e}")
                if batch_size > 100:
                    print(f"Reducing batch size to {batch_size // 2}")
                    return self.get_logs_in_batches(current_block, to_block, batch_size // 2)
                raise e
            
            current_block = end_block + 1
        
        return logs

    def process_events(self, events: List) -> pd.DataFrame:
        """处理事件数据"""
        events_data = []
        for event in events:
            try:
                decoded_event = self.decoder.decode_order_filled_event(event)
                events_data.append(decoded_event)
            except Exception as e:
                print(f"Error processing event in block {event['blockNumber']}: {e}")
        
        return self.processor.create_dataframe(events_data)

    def collect_data_from_block(self, end_block: int, blocks_back: int = 43200) -> tuple:
        """收集指定区块范围的数据"""
        from_block = end_block - blocks_back
        all_logs = self.get_logs_in_batches(from_block, end_block)
        df = self.process_events(all_logs)
        
        metadata = {
            'start_block': from_block,
            'end_block': end_block,
            'timestamp': datetime.now().isoformat()
        }
        
        return df, metadata