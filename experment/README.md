# LLM 錯誤生成質量量化分析工具

## 目錄結構

```
experment/
├── analyze_llm_errors.py      # 主分析腳本
├── metrics_summary.csv         # 指標摘要（Op1 vs Op2 對比）
├── cases_with_features.csv     # 每個案例的詳細特徵數據
├── metrics_barplot.png         # 指標對比長條圖
└── README.md                   # 本說明文件
```

## 使用方法

### 基本執行（從 testing_row_data 目錄）

```bash
python experment\analyze_llm_errors.py
```

### 進階選項

```bash
# 指定 OAI 代碼庫路徑（用於計算 code-mapping precision）
python experment\analyze_llm_errors.py --oai-repo-root "C:\path\to\openairinterface5g"

# 自定義輸出路徑
python experment\analyze_llm_errors.py --out-metrics-csv "custom_metrics.csv" --out-plot "custom_plot.png"
```

## 量化指標說明

### 1. Domain Term Density (領域詞彙密度)
- **定義**: `impact_description` 中出現 OAI/5G 專用術語的頻率
- **範圍**: 0.0 - 1.0（越高越好）
- **結果**: Op1=0.0611, Op2=0.0828 ✓ Op2 更高

### 2. Structural Novelty (結構創新度)
- **定義**: 基於 Jaccard Similarity，衡量生成內容的多樣性（非模板化）
- **範圍**: 0.0 - 1.0（越高越好）
- **結果**: Op1=0.8167, Op2=0.8679 ✓ Op2 更高

### 3. Code-Mapping Precision (代碼映射精確度)
- **定義**: 生成的錯誤參數是否真實存在於 OAI 源碼中
- **範圍**: 0.0 - 1.0（越高越好）
- **狀態**: 需要 `--oai-repo-root` 參數和 `ripgrep` (rg) 工具

### 4. Information Entropy (信息熵)
- **定義**: 錯誤類型分佈的熵值，量化生成的隨機性與覆蓋廣度
- **範圍**: 0.0 - 1.0（越高越好，表示分佈更均勻）
- **結果**: Op1=0.6512, Op2=0.8199 ✓ Op2 更高

## 當前結果摘要

| 指標 | Option 1 | Option 2 | 勝者 |
|------|----------|----------|------|
| Domain Term Density | 0.0611 | 0.0828 | Op2 ✓ |
| Structural Novelty | 0.8167 | 0.8679 | Op2 ✓ |
| Error Type Entropy | 0.6512 | 0.8199 | Op2 ✓ |
| Code Mapping Precision | N/A | N/A | 需 OAI repo |

## 依賴套件

```bash
pip install pandas matplotlib seaborn
```

## 數據來源

- `option_1/json/processed/op1_100_case_1.json`
- `option_1/json/processed/op1_100_case_2.json`
- `option_2/json/processed/op2_100_case_1.json`
- `option_2/json/processed/op2_100_case_2.json`

## 注意事項

1. 腳本會自動檢測是否在 `experment` 目錄中運行，並相應調整路徑
2. Code-Mapping Precision 需要安裝 `ripgrep` (rg) 工具
3. 所有輸出文件默認保存在 `experment` 目錄中

