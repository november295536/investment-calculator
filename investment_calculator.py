import decimal
from decimal import Decimal
import argparse
import json
from tabulate import tabulate
import datetime
import os

# 設定小數點精度
decimal.getcontext().prec = 28

class InvestmentCalculator:
    def __init__(self, config=None):
        """
        初始化投資計算器

        Args:
            config: 包含投資標的設定的字典或None
        """
        self.assets = []
        if config:
            self.load_config(config)

    def load_config(self, config):
        """從配置中加載資產"""
        asset_configs = config.get('assets', [])
        self.assets = []

        # 為每個資產轉換數據類型
        for asset_config in asset_configs:
            try:
                asset = {
                    'name': asset_config['name'],
                    'available_funds': Decimal(str(asset_config['available_funds'])),
                    'current_price': Decimal(str(asset_config['current_price'])),
                    'max_drop_percentage': Decimal(str(asset_config['max_drop_percentage'])),
                    'entry_interval': Decimal(str(asset_config['entry_interval'])),
                    'acceleration_factor': Decimal(str(asset_config.get('acceleration_factor', '1.5')))
                }
                self.assets.append(asset)
            except KeyError as e:
                print(f"配置檔案缺少必要的欄位: {e}")
            except (ValueError, decimal.InvalidOperation) as e:
                print(f"資料轉換錯誤: {e}，標的: {asset_config.get('name', 'unknown')}")
                print(f"請確認所有數值資料格式正確")

    def add_asset(self, name, available_funds, current_price, max_drop_percentage, entry_interval, acceleration_factor=Decimal('1.5')):
        """
        新增一個投資標的

        Args:
            name: 標的名稱
            available_funds: 可投入資金總額
            current_price: 當前價格
            max_drop_percentage: 預測最大下跌百分比
            entry_interval: 進場間隔百分比
            acceleration_factor: 加速因子，控制資金投入增長速度
        """
        # 將所有數值參數轉換為Decimal類型以確保準確計算
        try:
            asset = {
                'name': name,
                'available_funds': Decimal(str(available_funds)),
                'current_price': Decimal(str(current_price)),
                'max_drop_percentage': Decimal(str(max_drop_percentage)),
                'entry_interval': Decimal(str(entry_interval)),
                'acceleration_factor': Decimal(str(acceleration_factor))
            }
            self.assets.append(asset)
            return len(self.assets) - 1  # 返回資產索引
        except Exception as e:
            print(f"資料轉換錯誤: {e}")
            print(f"請確認所有數值資料格式正確: available_funds={available_funds}, current_price={current_price}, max_drop_percentage={max_drop_percentage}, entry_interval={entry_interval}, acceleration_factor={acceleration_factor}")
            return -1  # 表示添加失敗

    def calculate_entry_points(self, asset_index):
        """
        計算特定標的的所有進場點

        Args:
            asset_index: 資產在assets列表中的索引

        Returns:
            含有所有進場點詳情的列表
        """
        asset = self.assets[asset_index]
        name = asset['name']

        # 確保所有值都是Decimal類型
        # 這裡先檢查類型，如果是字符串則轉為Decimal
        available_funds = asset['available_funds'] if isinstance(asset['available_funds'], Decimal) else Decimal(str(asset['available_funds']))
        current_price = asset['current_price'] if isinstance(asset['current_price'], Decimal) else Decimal(str(asset['current_price']))
        max_drop_percentage = asset['max_drop_percentage'] if isinstance(asset['max_drop_percentage'], Decimal) else Decimal(str(asset['max_drop_percentage']))
        entry_interval = asset['entry_interval'] if isinstance(asset['entry_interval'], Decimal) else Decimal(str(asset['entry_interval']))
        acceleration_factor = asset['acceleration_factor'] if isinstance(asset['acceleration_factor'], Decimal) else Decimal(str(asset['acceleration_factor']))

        # 計算總共有幾次進場
        num_entries = int((max_drop_percentage / entry_interval).to_integral_exact())

        if num_entries == 0:
            return []

        # 計算每次進場的資金比例（非線性增長）
        # 使用加速因子使得後期投入比例更大
        total_weight = Decimal('0')
        weights = []

        for i in range(num_entries):
            # 使用加速因子讓權重隨著時間增加
            weight = (Decimal('1') + Decimal(str(i)) / Decimal(str(num_entries - 1))) ** acceleration_factor
            weights.append(weight)
            total_weight += weight

        # 標準化權重使其總和為1
        normalized_weights = [w / total_weight for w in weights]

        # 計算每個進場點的具體細節
        entry_points = []

        for i in range(num_entries):
            drop_percentage = entry_interval * Decimal(str(i + 1))
            entry_price = current_price * (Decimal('1') - drop_percentage / Decimal('100'))

            # 使用權重分配資金
            investment_amount = available_funds * normalized_weights[i]

            # 計算可購買的股數
            shares = investment_amount / entry_price

            # 四捨五入到小數點後第二位
            rounded_entry_price = entry_price.quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            rounded_investment = investment_amount.quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
            rounded_shares = shares.quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)

            entry_point = {
                'entry_number': i + 1,
                'drop_percentage': drop_percentage.quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP),
                'entry_price': rounded_entry_price,
                'investment_amount': rounded_investment,
                'weight_percentage': (normalized_weights[i] * Decimal('100')).quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP),
                'shares': rounded_shares
            }

            entry_points.append(entry_point)

        return entry_points

    def display_entry_points(self, asset_index):
        """
        顯示特定標的的進場點詳情

        Args:
            asset_index: 資產在assets列表中的索引
        """
        asset = self.assets[asset_index]
        entry_points = self.calculate_entry_points(asset_index)

        if not entry_points:
            print(f"標的 '{asset['name']}' 沒有計算出進場點，請檢查參數設定。")
            return

        print(f"\n標的: {asset['name']}")
        print(f"當前價格: {asset['current_price']}")
        print(f"可投入資金: {asset['available_funds']}")
        print(f"預測最大下跌: {asset['max_drop_percentage']}%")
        print(f"進場間隔: {asset['entry_interval']}%")
        print(f"加速因子: {asset['acceleration_factor']}\n")

        # 使用tabulate美化輸出
        table_data = []
        for entry in entry_points:
            table_data.append([
                entry['entry_number'],
                f"{entry['drop_percentage']}%",
                entry['entry_price'],
                entry['investment_amount'],
                f"{entry['weight_percentage']}%",
                entry['shares']
            ])

        # Translated headers to English
        # headers = ["進場次數", "下跌百分比", "進場價格", "投入金額", "資金權重", "購買股數"]
        headers = ["Entry No.", "Drop %", "Entry Price", "Inv. Amount", "Weight %", "Shares"]
        # Changed tablefmt from "grid" to "psql"
        print(tabulate(table_data, headers=headers, tablefmt="psql", numalign="right", stralign="center"))

        # 顯示總資金使用情況
        total_investment = sum(entry['investment_amount'] for entry in entry_points)
        print(f"\n總投入資金: {total_investment.quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)}")
        print(f"總購買股數: {sum(entry['shares'] for entry in entry_points).quantize(Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)}")

    def export_to_json(self, filename):
        """
        將所有標的的進場點詳情導出為JSON檔案

        Args:
            filename: 輸出檔案名稱
        """
        export_data = []

        for i, asset in enumerate(self.assets):
            entry_points = self.calculate_entry_points(i)

            # 將Decimal轉換為字符串，以便正確序列化為JSON
            asset_export = {
                'name': asset['name'],
                'available_funds': str(asset['available_funds']),
                'current_price': str(asset['current_price']),
                'max_drop_percentage': str(asset['max_drop_percentage']),
                'entry_interval': str(asset['entry_interval']),
                'acceleration_factor': str(asset['acceleration_factor']),
                'entry_points': []
            }

            for entry in entry_points:
                entry_export = {
                    'entry_number': entry['entry_number'],
                    'drop_percentage': str(entry['drop_percentage']),
                    'entry_price': str(entry['entry_price']),
                    'investment_amount': str(entry['investment_amount']),
                    'weight_percentage': str(entry['weight_percentage']),
                    'shares': str(entry['shares'])
                }
                asset_export['entry_points'].append(entry_export)

            export_data.append(asset_export)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"數據已成功導出至 {filename}")


def main():
    parser = argparse.ArgumentParser(description='投資進場計算工具')
    parser.add_argument('--config', type=str, help='配置文件路徑 (JSON)')
    parser.add_argument('--export', type=str, help='導出結果到指定的JSON檔案')
    parser.add_argument('--interactive', action='store_true', help='進入互動模式')

    args = parser.parse_args()

    calculator = InvestmentCalculator()

    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            calculator.load_config(config)
        except Exception as e:
            print(f"讀取配置文件時出錯: {e}")
            return

    if args.interactive or not args.config:
        # 進入互動模式
        try:
            while True:
                print("\n===== 投資進場計算工具 =====")
                print("1. 新增投資標的")
                print("2. 顯示所有標的的進場點")
                print("3. 導出數據到JSON檔案")
                print("4. 退出")

                choice = input("\n請選擇操作 (1-4): ")

                if choice == '1':
                    name = input("標的名稱: ")
                    available_funds = input("可投入資金: ")
                    current_price = input("當前價格: ")
                    max_drop_percentage = input("預測最大下跌百分比: ")
                    entry_interval = input("進場間隔百分比: ")

                    try:
                        acceleration_factor = input("加速因子 (預設為1.5，數值越大越傾向後期投入): ")
                        if not acceleration_factor:
                            acceleration_factor = '1.5'

                        asset_index = calculator.add_asset(
                            name,
                            available_funds,
                            current_price,
                            max_drop_percentage,
                            entry_interval,
                            acceleration_factor
                        )
                        print(f"已新增標的 '{name}'")
                        calculator.display_entry_points(asset_index)
                    except Exception as e:
                        print(f"新增標的時出錯: {e}")

                elif choice == '2':
                    if not calculator.assets:
                        print("尚未設定任何投資標的")
                    else:
                        print("\n===== 投資標的列表 =====")
                        for i, asset in enumerate(calculator.assets):
                            print(f"{i+1}. {asset['name']}")

                        while True:
                            asset_choice = input("\n請選擇要顯示的標的編號 (按Enter返回): ")
                            if not asset_choice:
                                break

                            try:
                                asset_index = int(asset_choice) - 1
                                if 0 <= asset_index < len(calculator.assets):
                                    calculator.display_entry_points(asset_index)
                                else:
                                    print("無效的標的編號")
                            except ValueError:
                                print("請輸入有效的數字")

                elif choice == '3':
                    if not calculator.assets:
                        print("尚未設定任何投資標的")
                    else:
                        # Generate timestamped filename
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"investment_plan_{timestamp}.json"
                        # Define result directory and create if not exists
                        result_dir = "result"
                        if not os.path.exists(result_dir):
                            os.makedirs(result_dir)
                        # Construct full path
                        filepath = os.path.join(result_dir, filename)
                        calculator.export_to_json(filepath)
                        # No longer asks for filename, just exports
                        print(f"\n結果已導出至 {filepath}") # Update message

                elif choice == '4':
                    break

                else:
                    print("無效的選擇，請重新選擇")

        except KeyboardInterrupt:
            print("\n程式已中止")
    else:
        # Non-interactive mode
        if not calculator.assets:
             print("配置文件中未找到有效的資產數據或讀取失敗。")
             return # Exit if no assets loaded from config

        # Display entry points for all assets loaded from config
        for i in range(len(calculator.assets)):
            calculator.display_entry_points(i)

        # Export logic for non-interactive mode
        result_dir = "result" # Define result directory
        if not os.path.exists(result_dir):
             os.makedirs(result_dir) # Create if not exists

        if args.export:
            # Use the filename provided by the user, place in result dir
            filepath = os.path.join(result_dir, args.export)
            calculator.export_to_json(filepath)
        else:
            # Generate timestamped filename and export automatically to result dir
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"investment_plan_{timestamp}.json"
            filepath = os.path.join(result_dir, filename)
            calculator.export_to_json(filepath)


if __name__ == "__main__":
    main()
