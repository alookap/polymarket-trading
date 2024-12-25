# scripts/collect_transactions.py

import sys
from pathlib import Path
import yaml
from datetime import datetime
import argparse

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.data_collection.transaction_collector import TransactionDataCollector, Config

def load_config(config_path: Path) -> dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def create_collector_config(yaml_config: dict) -> Config:
    "Create Config Class From yaml file"
    # 确保路径是相对于项目根目录的
    data_path = project_root / yaml_config['paths']['data']
    metadata_path = project_root / yaml_config['paths']['metadata']

    return Config(
        api_endpoint=yaml_config['api']['endpoint'],
        api_key=yaml_config['api']['key'],
        data_path=data_path,
        metadata_path=metadata_path,
        contract_address=yaml_config['contract']['address']
    )

def save_data(df, metadata, config: Config, end_block: int, blocks_back: int):
    """Save data and metadata"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    data_filename = f"transactions_{end_block-blocks_back}_{end_block}_{timestamp}.csv"
    metadata_filename = f"metadata_{end_block-blocks_back}_{end_block}_{timestamp}.yaml"
    
    data_path = config.data_path / data_filename
    metadata_path = config.metadata_path / metadata_filename
    
    df.to_csv(data_path, index=False)
    with open(metadata_path, 'w') as f:
        yaml.dump(metadata, f)
    
    print(f"Data saved to: {data_path}")
    print(f"Metadata saved to: {metadata_path}")

def main():
    parser = argparse.ArgumentParser(description='Collect blockchain transaction data')
    parser.add_argument('--end-block', type=int, help='End block number')
    parser.add_argument('--blocks-back', type=int, help='Number of blocks to look back')
    parser.add_argument('--config', type=str, default='configs/collector_config.yaml',
                      help='Path to config file')
    args = parser.parse_args()

    # 加载配置
    config_path = project_root / args.config
    yaml_config = load_config(config_path)
    collector_config = create_collector_config(yaml_config)

    # 创建收集器
    collector = TransactionDataCollector(collector_config)
    blocks_back = args.blocks_back or yaml_config['collection']['default_blocks_back']
    
    # 如果没有指定end_block，使用当前最新区块
    if args.end_block is None:
        w3 = collector.blockchain.w3
        end_block = w3.eth.block_number
    else:
        end_block = args.end_block

    print(f"Starting collection from block {end_block - blocks_back} to {end_block}")
    
    # 收集数据
    df, metadata = collector.collect_data_from_block(
        end_block=end_block,
        blocks_back=blocks_back
    )
    
    # 保存数据
    save_data(df, metadata, collector_config, end_block, blocks_back)

if __name__ == "__main__":
    main()