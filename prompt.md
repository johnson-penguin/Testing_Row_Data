# Role
你是一位資深的系統可靠性工程師 (SRE) 與 LLM 評測專家，專精於 5G 通訊協議棧 (OAI) 的自動化測試與日誌深度分析。

# Context & Goal
我正在評估「有無 Repo 上下文」對 LLM 生成錯誤案例（Error Generation）的影響。
我需要透過量化指標與自動化腳本來分析生成結果與系統反應之間的差異。

# Dataset Description
本實驗包含兩組測試數據，每組皆包含 LLM 生成的 JSON 指令與系統執行後的 LOG：
- **Option 1 (Baseline)**: LLM 僅參考輸入的 conf 檔案進行生成（無 Context）。
  - JSON: `C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\json\processed`
  - LOG: `C:\Users\wasd0\Desktop\Testing_Row_Data\option_1\log`
- **Option 2 (Context-Aware)**: Antigravity 閱讀 `openairinterface5g` 全域代碼後生成（具備 Context）。
  - JSON: `C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\json\processed`
  - LOG: `C:\Users\wasd0\Desktop\Testing_Row_Data\option_2\log`

# Task 1: 定義可重現的量化指標 (Python-based Metrics)
請在生成的 Python 腳本中實作以下量化邏輯，確保結果具備統計科學性：

1. **詞彙豐富度與專業度 (Lexical & Domain Diversity)**:
   - 計算 `JSON` 中 `error_description` 的 Type-Token Ratio (TTR)。
   - 統計 OAI 關鍵字（如: RRC, S1AP, NGAP, gNB, PDCP）的出頻率密度。
2. **結構重複率 (Jaccard Similarity)**:
   - 計算組內各 Case 的 Jaccard 相似度。數值越低代表生成多樣性越高，越不依賴固定模板。
3. **錯誤觸發深度 (Error Propagation Depth)**:
   - 分析 `LOG` 檔案，統計從觸發點到系統停止或報錯間，涉及的不同 C 語言模組（Module）數量。
4. **日誌模式獨特性 (Unique Log Patterns)**:
   - 利用 Regex 提取 LOG 中的 Unique Error Signatures，分析 Option 2 是否觸發了更底層的系統路徑。

# Task 2: 產出自動化分析 Python 腳本
請提供一段完整的 Python 代碼，要求如下：
1. **資料讀取**: 自動遍歷上述路徑下的所有 `.json` 與無副檔名（或 `.log`）的日誌檔案。
2. **指標計算**: 實作 Task 1 提到的所有數學公式。
3. **結果可視化**: 
   - 使用 `pandas` 產出指標對照表 (Mean, Std Dev)。
   - 使用 `matplotlib` 繪製 **Radar Chart (雷達圖)**，對比 Option 1 與 Option 2 在「專業度」、「多樣性」、「系統衝擊力」的維度。
   - 使用 `seaborn` 繪製 **Heatmap**，顯示不同生成策略與系統 Error Code 之間的相關性。

# Task 3: 深度質性比對分析
請在分析檔案後，回答以下問題：
- Option 2 生成的錯誤案例中，有哪些是顯然受益於「閱讀過 Repo」才產生的？（例如涉及了特定的 C 結構體邊界值或協議狀態機轉移）。
- 從 LOG 反應來看，Option 2 是否能更有效地導致系統進入異常狀態，而非僅僅是輸入檢查失敗（Input Validation Failure）？

# Output Format
1. 指標定義說明。
2. 完整的 Python 分析代碼塊。
3. 根據目前讀取到的檔案內容，給出初步的對比總結。