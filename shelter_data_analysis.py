#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
避難所數據檢查與修正腳本
Week 2 Shelter Analysis
"""

import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import requests
import json
from shapely.geometry import Point, Polygon
import geopandas as gpd
from datetime import datetime

# 載入環境變數
load_dotenv()

class ShelterDataAnalyzer:
    """避難所數據分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.project_crs = os.getenv('Project_CRS', 'EPSG:4326')
        self.data_file = 'data/避難收容處所點位檔案v9.csv'
        self.output_dir = 'outputs'
        
        # 確保輸出目錄存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 台灣本島邊界（簡化版）
        self.taiwan_bounds = {
            'min_lon': 119.5,
            'max_lon': 122.5,
            'min_lat': 21.5,
            'max_lat': 25.5
        }
        
        # 排除的縣市（離島）
        self.excluded_counties = ['金門縣', '連江縣', '澎湖縣']
        
        # 室內場所關鍵字
        self.indoor_keywords = ['活動中心', '國小', '國中', '高中', '國大', '教會', '寺廟', '圖書館', '社區中心']
        
        print(f"專案座標系統: {self.project_crs}")
        print(f"數據檔案: {self.data_file}")
    
    def load_data(self):
        """載入避難所數據"""
        try:
            df = pd.read_csv(self.data_file, encoding='utf-8')
            print(f"原始數據筆數: {len(df)}")
            return df
        except Exception as e:
            print(f"載入數據失敗: {e}")
            return None
    
    def check_coordinate_system(self, df):
        """檢查座標系統"""
        print("\n=== 座標系統檢查 ===")
        
        # 檢查經緯度範圍
        lon_valid = df['經度'].between(119, 123).sum()
        lat_valid = df['緯度'].between(20, 26).sum()
        
        print(f"有效經度範圍 (119-123): {lon_valid}/{len(df)} ({lon_valid/len(df)*100:.1f}%)")
        print(f"有效緯度範圍 (20-26): {lat_valid}/{len(df)} ({lat_valid/len(df)*100:.1f}%)")
        
        # 檢查零值座標
        zero_coords = (df['經度'] == 0) | (df['緯度'] == 0)
        zero_count = zero_coords.sum()
        print(f"零值座標: {zero_count} 筆")
        
        # 檢查區域座標合理性
        region_issues = self.check_region_coordinates(df)
        
        return zero_coords, region_issues
    
    def check_region_coordinates(self, df):
        """檢查區域座標合理性"""
        print("\n=== 區域座標合理性檢查 ===")
        
        # 台灣各縣市的大致座標範圍
        county_bounds = {
            '新竹縣': {'lon': (120.8, 121.2), 'lat': (24.5, 24.9)},
            '新竹市': {'lon': (120.8, 121.2), 'lat': (24.5, 24.9)},
            '臺中市': {'lon': (120.5, 121.0), 'lat': (24.0, 24.5)},
            '台中市': {'lon': (120.5, 121.0), 'lat': (24.0, 24.5)},
            '彰化縣': {'lon': (120.3, 120.8), 'lat': (23.8, 24.2)},
            '雲林縣': {'lon': (120.2, 120.6), 'lat': (23.6, 23.9)},
            '南投縣': {'lon': (120.6, 121.0), 'lat': (23.7, 24.1)},
            '嘉義縣': {'lon': (120.2, 120.6), 'lat': (23.4, 23.7)},
            '嘉義市': {'lon': (120.2, 120.6), 'lat': (23.4, 23.7)},
            '臺南市': {'lon': (120.1, 120.4), 'lat': (22.9, 23.4)},
            '台南市': {'lon': (120.1, 120.4), 'lat': (22.9, 23.4)},
            '高雄市': {'lon': (120.2, 120.6), 'lat': (22.4, 23.0)},
            '屏東縣': {'lon': (120.4, 120.9), 'lat': (22.0, 22.7)},
            '臺東縣': {'lon': (120.8, 121.3), 'lat': (22.5, 23.2)},
            '台東縣': {'lon': (120.8, 121.3), 'lat': (22.5, 23.2)},
            '花蓮縣': {'lon': (121.2, 121.7), 'lat': (23.2, 24.1)},
            '宜蘭縣': {'lon': (121.5, 121.9), 'lat': (24.4, 24.9)},
            '基隆市': {'lon': (121.7, 121.8), 'lat': (25.1, 25.3)},
            '新北市': {'lon': (121.4, 121.9), 'lat': (24.9, 25.3)},
            '臺北市': {'lon': (121.4, 121.7), 'lat': (24.9, 25.2)},
            '台北市': {'lon': (121.4, 121.7), 'lat': (24.9, 25.2)},
            '桃園市': {'lon': (121.0, 121.4), 'lat': (24.8, 25.2)},
        }
        
        region_issues = []
        
        for idx, row in df.iterrows():
            county_town = str(row['縣市及鄉鎮市區'])
            lon, lat = row['經度'], row['緯度']
            
            # 提取縣市名稱
            county = None
            for county_name in county_bounds.keys():
                if county_name in county_town:
                    county = county_name
                    break
            
            if county and county in county_bounds:
                bounds = county_bounds[county]
                if not (bounds['lon'][0] <= lon <= bounds['lon'][1] and 
                       bounds['lat'][0] <= lat <= bounds['lat'][1]):
                    region_issues.append({
                        'index': idx,
                        'name': row['避難收容處所名稱'],
                        'county': county_town,
                        'coordinates': (lon, lat),
                        'expected_bounds': bounds,
                        'issue': '座標不在預期縣市範圍內'
                    })
        
        print(f"發現 {len(region_issues)} 筆區域座標異常")
        
        if region_issues:
            print("區域異常記錄（前5筆）:")
            for issue in region_issues[:5]:
                print(f"  {issue['name']}: {issue['coordinates']} - {issue['county']}")
        
        return region_issues
    
    def geocode_address(self, address, county):
        """透過地址搜尋座標"""
        try:
            # 使用台灣開放資料平台的地址定位服務
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{address}, {county}, Taiwan",
                'format': 'json',
                'limit': 1,
                'countrycodes': 'tw'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]['lon']), float(data[0]['lat'])
        except Exception as e:
            print(f"地址定位失敗 {address}: {e}")
        
        return None, None
    
    def fix_zero_coordinates(self, df):
        """修正零值座標和區域異常"""
        print("\n=== 修正零值座標和區域異常 ===")
        
        zero_coords = (df['經度'] == 0) | (df['緯度'] == 0)
        zero_count = zero_coords.sum()
        
        # 先檢查區域異常
        region_issues = self.check_region_coordinates(df)
        
        if zero_count > 0 or len(region_issues) > 0:
            print(f"發現 {zero_count} 筆零值座標，{len(region_issues)} 筆區域異常，開始修正...")
            
            fixed_count = 0
            removed_indices = []
            
            # 處理零值座標
            for idx in df[zero_coords].index:
                address = df.loc[idx, '避難收容處所地址']
                county = df.loc[idx, '縣市及鄉鎮市區'].split('縣')[0] + '縣'
                
                if pd.notna(address) and address.strip():
                    lon, lat = self.geocode_address(address, county)
                    if lon and lat:
                        df.loc[idx, '經度'] = lon
                        df.loc[idx, '緯度'] = lat
                        fixed_count += 1
                        print(f"修正: {address} -> ({lon:.6f}, {lat:.6f})")
                else:
                    removed_indices.append(idx)
            
            # 處理區域異常
            for issue in region_issues:
                idx = issue['index']
                address = df.loc[idx, '避難收容處所地址']
                county = issue['county'].split('縣')[0] + '縣'
                
                if pd.notna(address) and address.strip():
                    lon, lat = self.geocode_address(address, county)
                    if lon and lat:
                        df.loc[idx, '經度'] = lon
                        df.loc[idx, '緯度'] = lat
                        fixed_count += 1
                        print(f"修正區域異常: {issue['name']} -> ({lon:.6f}, {lat:.6f})")
                    else:
                        removed_indices.append(idx)
                        print(f"無法修正區域異常，移除: {issue['name']}")
                else:
                    removed_indices.append(idx)
                    print(f"無地址資訊，移除: {issue['name']}")
            
            # 移除無法修正的記錄
            all_removed = list(set(removed_indices))
            if all_removed:
                df = df.drop(all_removed)
                print(f"移除無法修正的 {len(all_removed)} 筆記錄")
            
            print(f"成功修正 {fixed_count} 筆座標")
        
        return df
    
    def check_taiwan_mainland(self, df):
        """檢查是否在台灣本島邊界內"""
        print("\n=== 台灣本島邊界檢查 ===")
        
        # 排除離島縣市
        mainland_data = df[~df['縣市及鄉鎮市區'].str.contains('|'.join(self.excluded_counties), na=False)]
        excluded_count = len(df) - len(mainland_data)
        
        print(f"排除離島縣市: {excluded_count} 筆")
        print(f"剩餘本島數據: {len(mainland_data)} 筆")
        
        # 檢查邊界
        in_bounds = (
            mainland_data['經度'].between(self.taiwan_bounds['min_lon'], self.taiwan_bounds['max_lon']) &
            mainland_data['緯度'].between(self.taiwan_bounds['min_lat'], self.taiwan_bounds['max_lat'])
        )
        
        out_of_bounds = mainland_data[~in_bounds]
        print(f"邊界外數據: {len(out_of_bounds)} 筆")
        
        if len(out_of_bounds) > 0:
            print("邊界外記錄:")
            for idx, row in out_of_bounds.iterrows():
                print(f"  {row['避難收容處所名稱']}: ({row['經度']}, {row['緯度']})")
        
        # 保留在邊界內的記錄
        valid_mainland = mainland_data[in_bounds]
        print(f"有效本島數據: {len(valid_mainland)} 筆")
        
        return valid_mainland
    
    def check_county_consistency(self, df):
        """檢查縣市鄉鎮一致性"""
        print("\n=== 縣市鄉鎮一致性檢查 ===")
        
        inconsistent_count = 0
        inconsistent_records = []
        
        for idx, row in df.iterrows():
            county_town = row['縣市及鄉鎮市區']
            shelter_name = row['避難收容處所名稱']
            
            # 檢查避難所名稱是否包含鄉鎮資訊
            if pd.notna(county_town):
                county = county_town.split('縣')[0] + '縣'
                town = county_town.split('縣')[-1] if '縣' in county_town else county_town
                
                # 簡單的一致性檢查
                if '國小' in shelter_name or '國中' in shelter_name:
                    if town not in shelter_name:
                        inconsistent_count += 1
                        inconsistent_records.append({
                            'index': idx,
                            'name': shelter_name,
                            'county_town': county_town,
                            'issue': '學校名稱未包含鄉鎮資訊'
                        })
        
        print(f"不一致記錄: {inconsistent_count} 筆")
        
        if inconsistent_records:
            print("不一致記錄詳情:")
            for record in inconsistent_records[:5]:  # 只顯示前5筆
                print(f"  {record['name']} - {record['issue']}")
        
        return df, inconsistent_records
    
    def add_indoor_column(self, df):
        """新增 in_door 欄位"""
        print("\n=== 新增 in_door 欄位 ===")
        
        df['in_door'] = False  # 預設為 False
        
        indoor_count = 0
        outdoor_count = 0
        
        for idx, row in df.iterrows():
            shelter_name = str(row['避難收容處所名稱'])
            indoor_flag = str(row['室內']).strip() if pd.notna(row['室內']) else ''
            
            # 優先使用原始 '室內' 欄位判斷
            if indoor_flag == '是':
                df.loc[idx, 'in_door'] = True
                indoor_count += 1
            elif indoor_flag == '否':
                df.loc[idx, 'in_door'] = False
                outdoor_count += 1
            else:
                # 如果原始欄位為空，則使用關鍵字判斷
                is_indoor_type = any(keyword in shelter_name for keyword in self.indoor_keywords)
                
                if is_indoor_type:
                    df.loc[idx, 'in_door'] = True
                    indoor_count += 1
                else:
                    # 公園等戶外場所
                    if '公園' in shelter_name or '廣場' in shelter_name:
                        df.loc[idx, 'in_door'] = False
                        outdoor_count += 1
                    else:
                        # 預設為室內（較安全的假設）
                        df.loc[idx, 'in_door'] = True
                        indoor_count += 1
        
        print(f"室內避難所: {indoor_count} 筆")
        print(f"戶外避難所: {outdoor_count} 筆")
        print(f"總計: {len(df)} 筆")
        
        return df
    
    def generate_audit_report(self, df, issues):
        """生成審核報告"""
        print("\n=== 生成審核報告 ===")
        
        report = f"""# 避難所數據審核報告

## 基本資訊
- **報告生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **座標系統**: {self.project_crs}
- **原始數據筆數**: 5975
- **修正後筆數**: {len(df)}
- **數據清理率**: {((5975 - len(df)) / 5975 * 100):.1f}%

## 發現的問題與修正

### 1. 座標系統問題
- **問題**: 部分記錄經緯度為0或超出合理範圍
- **修正方式**: 透過地址定位服務重新定位
- **修正筆數**: {issues.get('fixed_coordinates', 0)} 筆
- **移除筆數**: {issues.get('removed_coordinates', 0)} 筆

### 2. 區域座標異常問題
- **問題**: 避難所座標不在所屬縣市的合理範圍內
- **主要問題**: 新竹縣避難所出現在屏東、台東等地
- **異常筆數**: {issues.get('region_anomalies', 0)} 筆
- **影響**: 這些點位在地圖上會顯示在錯誤的位置，甚至海洋中

### 3. 台灣本島邊界問題
- **問題**: 部分避難所座標落在台灣本島邊界外
- **邊界定義**: 經度 119.5-122.5, 緯度 21.5-25.5
- **排除縣市**: 金門縣、連江縣、澎湖縣
- **修正筆數**: {issues.get('out_of_bounds', 0)} 筆

### 4. 縣市鄉鎮一致性问题
- **問題**: 避難所名稱與所屬鄉鎮資訊不一致
- **主要問題**: 學校類避難所未在名稱中包含鄉鎮資訊
- **不一致筆數**: {issues.get('inconsistent_county', 0)} 筆

### 5. 室內外判斷優化
- **新增欄位**: `in_door` (Boolean)
- **判斷邏輯**: 
  - 室內關鍵字: {', '.join(self.indoor_keywords)}
  - 室內判斷: '室內'欄位為'是'
  - 室外判斷: '室內'欄位為'否'且為公園/廣場
- **室內避難所**: {issues.get('indoor_count', 0)} 筆
- **戶外避難所**: {issues.get('outdoor_count', 0)} 筆

## 統計數據

### 縣市分布
"""
        
        # 縣市統計
        county_stats = df['縣市及鄉鎮市區'].value_counts().head(10)
        for county, count in county_stats.items():
            report += f"- **{county}**: {count} 筆\n"
        
        report += f"""
### 避難所類型分布
"""
        
        # 類型統計
        type_stats = {}
        for idx, row in df.iterrows():
            name = str(row['避難收容處所名稱'])
            if '國小' in name:
                type_stats['國小'] = type_stats.get('國小', 0) + 1
            elif '活動中心' in name:
                type_stats['活動中心'] = type_stats.get('活動中心', 0) + 1
            elif '公園' in name:
                type_stats['公園'] = type_stats.get('公園', 0) + 1
            elif '教會' in name:
                type_stats['教會'] = type_stats.get('教會', 0) + 1
            else:
                type_stats['其他'] = type_stats.get('其他', 0) + 1
        
        for shelter_type, count in type_stats.items():
            report += f"- **{shelter_type}**: {count} 筆\n"
        
        report += f"""
### 座標分布
- **平均經度**: {df['經度'].mean():.6f}
- **平均緯度**: {df['緯度'].mean():.6f}
- **經度範圍**: {df['經度'].min():.6f} ~ {df['經度'].max():.6f}
- **緯度範圍**: {df['緯度'].min():.6f} ~ {df['緯度'].max():.6f}

## 建議

1. **定期座標驗證**: 建議每季度重新驗證避難所座標準確性
2. **地址標準化**: 統一地址格式，提高地理編碼準確度
3. **欄位完整性**: 補充缺失的聯絡資訊和收容能力數據
4. **分類標準**: 建立更詳細的避難所分類標準

---
*報告由避難所數據分析系統自動生成*
"""
        
        # 保存報告
        report_file = os.path.join(self.output_dir, f'shelter_audit_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"審核報告已保存: {report_file}")
        return report_file
    
    def save_cleaned_data(self, df):
        """保存清理後的數據"""
        output_file = os.path.join(self.output_dir, f'shelter_data_cleaned_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"清理後數據已保存: {output_file}")
        return output_file
    
    def run_analysis(self):
        """執行完整分析"""
        print("=" * 60)
        print("避難所數據檢查與修正分析")
        print("=" * 60)
        
        # 載入數據
        df = self.load_data()
        if df is None:
            return
        
        issues = {}
        
        # 1. 檢查座標系統
        zero_coords, region_issues = self.check_coordinate_system(df)
        
        # 2. 修正零值座標和區域異常
        df = self.fix_zero_coordinates(df)
        issues['fixed_coordinates'] = 5975 - len(df)
        issues['removed_coordinates'] = zero_coords.sum() + len(region_issues) - issues['fixed_coordinates']
        issues['region_anomalies'] = len(region_issues)
        
        # 3. 檢查台灣本島邊界
        df = self.check_taiwan_mainland(df)
        issues['out_of_bounds'] = 5975 - len(df) - issues['removed_coordinates']
        
        # 4. 檢查縣市鄉鎮一致性
        df, inconsistent_records = self.check_county_consistency(df)
        issues['inconsistent_county'] = len(inconsistent_records)
        
        # 5. 新增 in_door 欄位
        df = self.add_indoor_column(df)
        issues['indoor_count'] = df['in_door'].sum()
        issues['outdoor_count'] = len(df) - df['in_door'].sum()
        
        # 6. 生成審核報告
        report_file = self.generate_audit_report(df, issues)
        
        # 7. 保存清理後的數據
        data_file = self.save_cleaned_data(df)
        
        print("\n" + "=" * 60)
        print("分析完成！")
        print(f"原始數據: 5975 筆")
        print(f"清理後數據: {len(df)} 筆")
        print(f"數據清理率: {((5975 - len(df)) / 5975 * 100):.1f}%")
        print(f"審核報告: {report_file}")
        print(f"清理後數據: {data_file}")
        print("=" * 60)
        
        return df, issues, report_file, data_file

def main():
    """主程式"""
    analyzer = ShelterDataAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
