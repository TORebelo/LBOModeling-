# 📊 LBO Model Generator

A Python tool that automates the creation of Leveraged Buyout (LBO) financial models. Perform comprehensive LBO analysis including debt structuring, financial projections, and return metrics with visual insights.

---

## 🔍 Overview

This tool implements a complete framework for LBO analysis, enabling users to:

- Model detailed financial projections  
- Analyze capital structure  
- Evaluate investment returns (IRR, MOIC)  
- Visualize key metrics over the holding period  

---

## ✨ Features

### 🧾 Complete LBO Modeling Framework

- Income statement projections: `Revenue → EBITDA → Net Income`
- Cash flow statement with integrated debt repayment
- Balance sheet projections
- IRR and MOIC calculations

### 📈 Key Metrics

- Entry/exit valuation multiples
- Debt/equity financing breakdown
- Free cash flow generation
- Amortization and debt paydown schedule

### 📊 Visualizations

- Revenue & EBITDA growth
- Margin improvement trends
- Debt balance over time
- Cumulative free cash flow

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/lbo-model-generator.git
cd lbo-model-generator
pip install -r requirements.txt
```

## 🚀 Usage
```
from lbo_model import LBOModel

# Initialize model
lbo = LBOModel(
    company_name="Acme Corp",
    entry_year=2023,
    exit_year=2028,
    revenue_entry=500,             # $500M
    ebitda_margin_entry=25,        # 25%
    revenue_growth=8,              # 8% per year
    ebitda_margin_exit=30,         # 30% at exit
    capex_percent=4,               # 4% of revenue
    dso=45, dpo=60, dsi=30,        # Working capital
    purchase_price_multiple=10.0,  # 10x EBITDA
    debt_percentage=60,            # 60% debt
    interest_rate=8,               # 8% interest
    amortization_years=5           # Amortized over 5 years
)

# Generate summary
lbo.summary()

# Visualize outputs
lbo.visualize()

# Access financials
print(lbo.income_stmt)
print(lbo.cash_flow)
print(lbo.balance_sheet)
```




