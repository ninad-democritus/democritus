# Chart Generation - Generic Design for Any Dataset

## ✅ COMPLETE GENERIC APPROACH

The chart generation logic is **100% data-agnostic** and works for any dataset with any entity names. Here's how:

## How It Identifies Data Structure (No Hardcoding)

### 1. **Column Type Detection** (Type-Based, Not Name-Based)

```python
for col, val in first_row.items():
    if isinstance(val, (int, float)):
        numeric_cols.append(col)      # ANY numeric column
        column_info[col] = "numeric"
    elif isinstance(val, str):
        categorical_cols.append(col)   # ANY string column
        column_info[col] = "categorical"
```

**Works for**:
- ✅ `Team, Gold, Silver, Bronze` (current dataset)
- ✅ `Product, Revenue, Profit, Margin` (sales dataset)
- ✅ `City, Temperature, Humidity, Rainfall` (weather dataset)
- ✅ `Employee, Salary, Bonus` (HR dataset)
- ✅ ANY combination of string + number columns

### 2. **Series Creation** (Dynamic, Not Hardcoded)

```python
for num_col in numeric_cols:
    series_data = [row[num_col] for row in data]
    series.append({
        "type": chart_type,
        "name": num_col.replace("_", " ").title(),  # Auto-format name
        "data": series_data
    })
```

**Works for**:
- 3 numeric columns → 3 series (Gold/Silver/Bronze)
- 5 numeric columns → 5 series (Revenue/Cost/Profit/Margin/Tax)
- 1 numeric column → 1 series (Population)
- 10 numeric columns → 10 series (any metrics)

### 3. **X-Axis Labels** (First String Column)

```python
for col, val in first_row.items():
    if isinstance(val, str):
        categorical_col = col  # FIRST string column found
        break
```

**Works for**:
- `Team` column (current)
- `Product` column (sales data)
- `City` column (location data)
- `Name` column (employee data)
- ANY first string column

### 4. **Data Limiting** (Chart-Type Based)

```python
chart_limits = {
    'pie': 50,    # Pies get cluttered
    'bar': 100,   # Bars get too long
    'line': 500,  # Lines can handle more
    'scatter': 1000  # Scatter handles many
}
```

**Based on chart rendering characteristics, not data content**

## Example: Different Datasets

### Current Dataset (Olympics)
```python
Input: {
  "Team": "USA",
  "Gold_Winners": 47540,
  "Silver_Winners": 29460,
  "Bronze_Winners": 23800
}

Detection:
  categorical_cols = ["Team"]
  numeric_cols = ["Gold_Winners", "Silver_Winners", "Bronze_Winners"]

Output:
  xAxis.data = ["USA", "Soviet Union", ...]
  series = [
    {name: "Gold Winners", data: [47540, 21160, ...]},
    {name: "Silver Winners", data: [29460, 14320, ...]},
    {name: "Bronze Winners", data: [23800, 13540, ...]}
  ]
```

### Sales Dataset (Hypothetical)
```python
Input: {
  "Product": "Laptop",
  "Q1_Revenue": 150000,
  "Q2_Revenue": 180000,
  "Q3_Revenue": 200000,
  "Q4_Revenue": 220000
}

Detection:
  categorical_cols = ["Product"]
  numeric_cols = ["Q1_Revenue", "Q2_Revenue", "Q3_Revenue", "Q4_Revenue"]

Output:
  xAxis.data = ["Laptop", "Phone", "Tablet", ...]
  series = [
    {name: "Q1 Revenue", data: [150000, 90000, ...]},
    {name: "Q2 Revenue", data: [180000, 95000, ...]},
    {name: "Q3 Revenue", data: [200000, 98000, ...]},
    {name: "Q4 Revenue", data: [220000, 102000, ...]}
  ]
```

### Weather Dataset (Hypothetical)
```python
Input: {
  "City": "New York",
  "Temperature": 72,
  "Humidity": 65,
  "Rainfall": 3.2
}

Detection:
  categorical_cols = ["City"]
  numeric_cols = ["Temperature", "Humidity", "Rainfall"]

Output:
  xAxis.data = ["New York", "Los Angeles", ...]
  series = [
    {name: "Temperature", data: [72, 85, ...]},
    {name: "Humidity", data: [65, 45, ...]},
    {name: "Rainfall", data: [3.2, 0.8, ...]}
  ]
```

### Single Metric Dataset (Population)
```python
Input: {
  "Country": "China",
  "Population": 1400000000
}

Detection:
  categorical_cols = ["Country"]
  numeric_cols = ["Population"]

Output:
  xAxis.data = ["China", "India", "USA", ...]
  series = [
    {name: "Population", data: [1400000000, 1380000000, 331000000, ...]}
  ]
```

## No Hardcoded Values

❌ **NEVER uses**: "Team", "Gold", "Silver", "Bronze", "medal", etc.
✅ **ALWAYS uses**: Type detection (int/float/string), dynamic iteration

## Zero Configuration for New Datasets

When you add a **completely different dataset**:
1. ✅ No code changes needed
2. ✅ No configuration needed
3. ✅ No prompt engineering needed
4. ✅ Just works automatically

## Testing with Your Dataset

**Current query**: "Give me number of medal winners per team"
- Detects: 1 categorical (`Team`), 3 numeric (medals)
- Creates: 3 series bar chart

**Try these on different data**:
- "Show me sales by product" → Auto-detects product name and revenue columns
- "Display temperatures by city" → Auto-detects city and temperature
- "Compare metrics by region" → Auto-detects region and all numeric metrics

## Summary

The system is **completely data-agnostic**:

| Aspect | Implementation | Generic? |
|--------|---------------|----------|
| Column detection | `isinstance(val, (int, float))` | ✅ Yes |
| Series creation | Loop through all numeric columns | ✅ Yes |
| X-axis labels | First string column found | ✅ Yes |
| Data limiting | Based on chart type only | ✅ Yes |
| Color assignment | Cycles through theme colors | ✅ Yes |
| Tooltip format | Standard ECharts format | ✅ Yes |

**Result**: Works with ANY tabular data structure (string + numbers)!

