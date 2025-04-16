import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

class LBOModel:
    def __init__(self, company_name, entry_year, exit_year, revenue_entry, ebitda_margin_entry, 
                 revenue_growth, ebitda_margin_exit, capex_percent, dso, dpo, dsi, 
                 purchase_price_multiple, debt_percentage, interest_rate, amortization_years,
                 tax_rate=0.21):
        """
        Initialize LBO model with key parameters.
        
        Parameters:
        - company_name: Name of target company
        - entry_year: Year of acquisition
        - exit_year: Year of exit
        - revenue_entry: Starting revenue ($ millions)
        - ebitda_margin_entry: Starting EBITDA margin (%)
        - revenue_growth: Annual revenue growth rate (%)
        - ebitda_margin_exit: Exit EBITDA margin (%)
        - capex_percent: Capital expenditures as % of revenue
        - dso: Days sales outstanding
        - dpo: Days payable outstanding
        - dsi: Days sales in inventory
        - purchase_price_multiple: Entry EBITDA multiple
        - debt_percentage: % of purchase price financed with debt
        - interest_rate: Annual interest rate on debt (%)
        - amortization_years: Years to amortize debt
        - tax_rate: Corporate tax rate (default 21%)
        """
        self.company_name = company_name
        self.entry_year = entry_year
        self.exit_year = exit_year
        self.holding_period = exit_year - entry_year
        self.revenue_entry = revenue_entry
        self.ebitda_margin_entry = ebitda_margin_entry / 100
        self.revenue_growth = revenue_growth / 100
        self.ebitda_margin_exit = ebitda_margin_exit / 100
        self.capex_percent = capex_percent / 100
        self.dso = dso
        self.dpo = dpo
        self.dsi = dsi
        self.purchase_price_multiple = purchase_price_multiple
        self.debt_percentage = debt_percentage / 100
        self.interest_rate = interest_rate / 100
        self.amortization_years = amortization_years
        self.tax_rate = tax_rate
        
        # Initialize model
        self._setup_model()
        self._build_income_statement()
        self._build_cash_flow()
        self._build_balance_sheet()
        self._calculate_returns()
        
    def _setup_model(self):
        """Initialize model structure and calculate entry/exit metrics."""
        # Calculate entry EBITDA and purchase price
        self.entry_ebitda = self.revenue_entry * self.ebitda_margin_entry
        self.purchase_price = self.entry_ebitda * self.purchase_price_multiple
        
        # Calculate financing structure
        self.debt_amount = self.purchase_price * self.debt_percentage
        self.equity_amount = self.purchase_price - self.debt_amount
        
        # Create timeline
        self.years = list(range(self.entry_year, self.exit_year + 1))
        self.num_years = len(self.years)
        
    def _build_income_statement(self):
        """Build projected income statement."""
        self.income_stmt = pd.DataFrame(index=self.years)
        
        # Revenue projection
        self.income_stmt['Revenue'] = self.revenue_entry * (1 + self.revenue_growth) ** np.arange(self.num_years)
        
        # EBITDA projection (linearly interpolate margin from entry to exit)
        margin_growth = (self.ebitda_margin_exit - self.ebitda_margin_entry) / (self.num_years - 1)
        self.income_stmt['EBITDA Margin'] = self.ebitda_margin_entry + margin_growth * np.arange(self.num_years)
        self.income_stmt['EBITDA'] = self.income_stmt['Revenue'] * self.income_stmt['EBITDA Margin']
        
        # Depreciation (simplified as % of capex)
        self.income_stmt['Depreciation'] = self.income_stmt['Revenue'] * self.capex_percent * 0.8  # 80% of capex
        
        # EBIT
        self.income_stmt['EBIT'] = self.income_stmt['EBITDA'] - self.income_stmt['Depreciation']
        
        # Calculate remaining debt for each year to determine interest expense
        remaining_debt = [self.debt_amount]
        annual_payment = self.debt_amount / self.amortization_years
        
        for i in range(1, self.num_years):
            new_debt = max(0, remaining_debt[-1] - annual_payment)
            remaining_debt.append(new_debt)
        
        # Interest expense based on remaining debt
        self.income_stmt['Interest Expense'] = [debt * self.interest_rate for debt in remaining_debt]
        
        # EBT and Net Income
        self.income_stmt['EBT'] = self.income_stmt['EBIT'] - self.income_stmt['Interest Expense']
        self.income_stmt['Tax'] = self.income_stmt['EBT'].apply(lambda x: max(0, x * self.tax_rate))  # No tax benefit if EBT negative
        self.income_stmt['Net Income'] = self.income_stmt['EBT'] - self.income_stmt['Tax']
        
    def _build_cash_flow(self):
        """Build projected cash flow statement."""
        self.cash_flow = pd.DataFrame(index=self.years)
        
        # Start with net income
        self.cash_flow['Net Income'] = self.income_stmt['Net Income']
        
        # Add back non-cash items
        self.cash_flow['D&A'] = self.income_stmt['Depreciation']
        
        # Changes in working capital based on DSO/DPO/DSI
        revenue_diff = self.income_stmt['Revenue'].diff().fillna(0)
        
        # Simplified working capital calculation
        # Accounts Receivable change: (Revenue * DSO/365) delta
        # Inventory change: (Revenue * DSI/365) delta
        # Accounts Payable change: (Revenue * DPO/365) delta
        ar_change = revenue_diff * self.dso / 365
        inv_change = revenue_diff * self.dsi / 365
        ap_change = revenue_diff * self.dpo / 365
        
        # Net working capital change (negative means cash outflow)
        self.cash_flow['ΔWC'] = ap_change - (ar_change + inv_change)
        
        # Capital expenditures
        self.cash_flow['Capex'] = -self.income_stmt['Revenue'] * self.capex_percent
        
        # Debt amortization - Fixed to avoid circular reference
        annual_debt_payment = self.debt_amount / self.amortization_years
        debt_amortization = []
        remaining_debt = self.debt_amount
        
        for i in range(self.num_years):
            if i == 0:
                # No debt payment in year 0 (acquisition year)
                debt_amortization.append(0)
            else:
                # Calculate debt payment for this year
                payment = min(annual_debt_payment, remaining_debt)
                debt_amortization.append(-payment)
                remaining_debt -= payment
        
        self.cash_flow['Debt Amortization'] = debt_amortization
        
        # Interest payments
        self.cash_flow['Interest Paid'] = -self.income_stmt['Interest Expense']
        
        # Calculate free cash flow
        self.cash_flow['FCF'] = (self.cash_flow['Net Income'] + 
                                self.cash_flow['D&A'] + 
                                self.cash_flow['ΔWC'] + 
                                self.cash_flow['Capex'])
        
        # Levered free cash flow (after debt service)
        self.cash_flow['LFCF'] = (self.cash_flow['FCF'] + 
                                 self.cash_flow['Debt Amortization'] + 
                                 self.cash_flow['Interest Paid'])
        
        # Cumulative FCF
        self.cash_flow['Cumulative FCF'] = self.cash_flow['LFCF'].cumsum()
        
    def _build_balance_sheet(self):
        """Build projected balance sheet."""
        self.balance_sheet = pd.DataFrame(index=self.years)
        
        # Debt balance - Calculate based on debt amortization from cash flow
        debt_balance = [self.debt_amount]
        for i in range(1, self.num_years):
            debt_payment = -self.cash_flow.loc[self.years[i], 'Debt Amortization']
            new_balance = debt_balance[-1] - debt_payment
            debt_balance.append(new_balance)
        
        self.balance_sheet['Debt'] = debt_balance
        
        # Equity (starting equity + retained earnings)
        self.balance_sheet['Equity'] = self.equity_amount + self.cash_flow['Cumulative FCF']
        
        # Enterprise value (simplified as debt + equity)
        self.balance_sheet['Enterprise Value'] = self.balance_sheet['Debt'] + self.balance_sheet['Equity']
        
        # Implied EV/EBITDA multiple
        self.balance_sheet['Implied EV/EBITDA'] = (self.balance_sheet['Enterprise Value'] / 
                                                  self.income_stmt['EBITDA'])
        
    def _calculate_returns(self):
        """Calculate IRR, MOIC and other return metrics for the LBO."""
        # Cash flows (negative equity at entry, positive at exit)
        cash_flows = [-self.equity_amount]
        
        # Add intermediate cash flows (dividends, etc.)
        for year in range(self.entry_year + 1, self.exit_year):
            year_idx = year - self.entry_year
            cash_flows.append(self.cash_flow.loc[year, 'LFCF'])
        
        # Calculate exit value
        exit_ebitda = self.income_stmt.loc[self.exit_year, 'EBITDA']
        exit_multiple = self.purchase_price_multiple  # Same as entry for simplicity
        exit_enterprise_value = exit_ebitda * exit_multiple
        
        # Net debt at exit
        net_debt = self.balance_sheet.loc[self.exit_year, 'Debt']
        
        # Equity value at exit
        exit_equity_value = exit_enterprise_value - net_debt
        
        # Final cash flow
        cash_flows.append(exit_equity_value)
        
        # Calculate IRR using numpy_financial
        self.irr = npf.irr(cash_flows) * 100  # as percentage
        
        # Calculate MOIC (Multiple on Invested Capital)
        self.moic = exit_equity_value / self.equity_amount
        
        # Calculate DPI (Distributions to Paid-In)
        self.dpi = sum(max(0, cf) for cf in cash_flows[1:]) / self.equity_amount
        
        # Calculate TVPI (Total Value to Paid-In)
        self.tvpi = self.moic  # Same as MOIC in this simple model
        
    def summary(self):
        """Print summary of the LBO model."""
        print(f"\nLBO Model Summary for {self.company_name}")
        print("="*50)
        print(f"Entry Year: {self.entry_year}")
        print(f"Exit Year: {self.exit_year}")
        print(f"Holding Period: {self.holding_period} years")
        print(f"\nEntry EBITDA: ${self.entry_ebitda:,.2f}M")
        print(f"Purchase Price (at {self.purchase_price_multiple}x EBITDA): ${self.purchase_price:,.2f}M")
        print(f"Financing Structure:")
        print(f"  - Debt: ${self.debt_amount:,.2f}M ({self.debt_percentage*100:.1f}%)")
        print(f"  - Equity: ${self.equity_amount:,.2f}M ({(1-self.debt_percentage)*100:.1f}%)")
        
        print("\nExit Metrics:")
        exit_ebitda = self.income_stmt.loc[self.exit_year, 'EBITDA']
        print(f"Exit EBITDA: ${exit_ebitda:,.2f}M")
        print(f"Exit EBITDA Margin: {self.income_stmt.loc[self.exit_year, 'EBITDA Margin']*100:.1f}%")
        
        print("\nReturns:")
        print(f"IRR: {self.irr:.1f}%")
        print(f"MOIC: {self.moic:.2f}x")
        print(f"DPI: {self.dpi:.2f}x")
        print(f"TVPI: {self.tvpi:.2f}x")
        
    def visualize(self):
        """Create visualizations of key metrics."""
        plt.figure(figsize=(15, 10))
        
        # Revenue and EBITDA growth
        plt.subplot(2, 2, 1)
        ax1 = self.income_stmt[['Revenue']].plot(kind='bar', color='blue', alpha=0.7, ax=plt.gca())
        ax2 = plt.twinx()
        self.income_stmt[['EBITDA']].plot(kind='line', marker='o', color='green', ax=ax2)
        plt.title('Revenue and EBITDA Growth')
        ax1.set_ylabel('Revenue ($ Millions)')
        ax2.set_ylabel('EBITDA ($ Millions)')
        plt.grid(True, alpha=0.3)
        
        # EBITDA Margin
        plt.subplot(2, 2, 2)
        (self.income_stmt['EBITDA Margin'] * 100).plot(kind='line', marker='o', color='green')
        plt.title('EBITDA Margin')
        plt.ylabel('Percentage (%)')
        plt.grid(True, alpha=0.3)
        
        # Debt Paydown
        plt.subplot(2, 2, 3)
        self.balance_sheet['Debt'].plot(kind='bar', color='red', alpha=0.7)
        plt.title('Debt Balance')
        plt.ylabel('$ Millions')
        plt.grid(True, alpha=0.3)
        
        # Cumulative FCF
        plt.subplot(2, 2, 4)
        self.cash_flow['Cumulative FCF'].plot(kind='line', marker='o', color='purple')
        plt.title('Cumulative Free Cash Flow')
        plt.ylabel('$ Millions')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
    def sensitivity_analysis(self, exit_multiples=None, revenue_growths=None, ebitda_margins=None):
        """
        Perform sensitivity analysis on key variables.
        
        Parameters:
        - exit_multiples: List of exit EBITDA multiples to test
        - revenue_growths: List of revenue growth rates to test
        - ebitda_margins: List of exit EBITDA margins to test
        """
        if exit_multiples is None:
            exit_multiples = [self.purchase_price_multiple - 2, 
                             self.purchase_price_multiple - 1, 
                             self.purchase_price_multiple, 
                             self.purchase_price_multiple + 1, 
                             self.purchase_price_multiple + 2]
        
        if revenue_growths is None:
            revenue_growths = [(self.revenue_growth * 100) - 2, 
                              (self.revenue_growth * 100) - 1, 
                              (self.revenue_growth * 100), 
                              (self.revenue_growth * 100) + 1, 
                              (self.revenue_growth * 100) + 2]
        
        if ebitda_margins is None:
            ebitda_margins = [(self.ebitda_margin_exit * 100) - 2, 
                             (self.ebitda_margin_exit * 100) - 1, 
                             (self.ebitda_margin_exit * 100), 
                             (self.ebitda_margin_exit * 100) + 1, 
                             (self.ebitda_margin_exit * 100) + 2]
        
        # Exit multiple sensitivity
        print("\nExit Multiple Sensitivity:")
        print("Exit Multiple\tIRR\tMOIC")
        for multiple in exit_multiples:
            # Calculate exit value with this multiple
            exit_ebitda = self.income_stmt.loc[self.exit_year, 'EBITDA']
            exit_enterprise_value = exit_ebitda * multiple
            exit_debt = self.balance_sheet.loc[self.exit_year, 'Debt']
            exit_equity_value = exit_enterprise_value - exit_debt
            
            # Calculate returns
            moic = exit_equity_value / self.equity_amount
            
            # Calculate IRR
            cash_flows = [-self.equity_amount]
            cash_flows.append(exit_equity_value)
            irr = npf.irr(cash_flows) * 100
            
            print(f"{multiple:.1f}x\t{irr:.1f}%\t{moic:.2f}x")
        
        # Revenue growth sensitivity
        print("\nRevenue Growth Sensitivity:")
        print("Growth Rate\tIRR\tMOIC")
        for growth in revenue_growths:
            # Create a temporary model with this growth rate
            temp_model = LBOModel(
                company_name=self.company_name,
                entry_year=self.entry_year,
                exit_year=self.exit_year,
                revenue_entry=self.revenue_entry,
                ebitda_margin_entry=self.ebitda_margin_entry * 100,
                revenue_growth=growth,
                ebitda_margin_exit=self.ebitda_margin_exit * 100,
                capex_percent=self.capex_percent * 100,
                dso=self.dso,
                dpo=self.dpo,
                dsi=self.dsi,
                purchase_price_multiple=self.purchase_price_multiple,
                debt_percentage=self.debt_percentage * 100,
                interest_rate=self.interest_rate * 100,
                amortization_years=self.amortization_years
            )
            
            print(f"{growth:.1f}%\t{temp_model.irr:.1f}%\t{temp_model.moic:.2f}x")
        
        # EBITDA margin sensitivity
        print("\nEBITDA Margin Sensitivity:")
        print("Exit Margin\tIRR\tMOIC")
        for margin in ebitda_margins:
            # Create a temporary model with this margin
            temp_model = LBOModel(
                company_name=self.company_name,
                entry_year=self.entry_year,
                exit_year=self.exit_year,
                revenue_entry=self.revenue_entry,
                ebitda_margin_entry=self.ebitda_margin_entry * 100,
                revenue_growth=self.revenue_growth * 100,
                ebitda_margin_exit=margin,
                capex_percent=self.capex_percent * 100,
                dso=self.dso,
                dpo=self.dpo,
                dsi=self.dsi,
                purchase_price_multiple=self.purchase_price_multiple,
                debt_percentage=self.debt_percentage * 100,
                interest_rate=self.interest_rate * 100,
                amortization_years=self.amortization_years
            )
            
            print(f"{margin:.1f}%\t{temp_model.irr:.1f}%\t{temp_model.moic:.2f}x")


# Example usage
if __name__ == "__main__":
    # Example parameters for a sample LBO
    lbo = LBOModel(
        company_name="Acme Corp",
        entry_year=2023,
        exit_year=2028,
        revenue_entry=500,          # $500M
        ebitda_margin_entry=25,     # 25%
        revenue_growth=8,           # 8% annually
        ebitda_margin_exit=30,      # 30% at exit
        capex_percent=4,            # 4% of revenue
        dso=45,                     # 45 days
        dpo=60,                     # 60 days
        dsi=30,                     # 30 days
        purchase_price_multiple=10.0,  # 10x EBITDA
        debt_percentage=60,         # 60% debt
        interest_rate=8,            # 8% interest
        amortization_years=5        # 5 year amortization
    )
    
    # Print summary
    lbo.summary()
    
    # Show visualizations
    lbo.visualize()
    
    # Run sensitivity analysis
    lbo.sensitivity_analysis()
    
    # Access detailed projections
    print("\nIncome Statement Projections:")
    print(lbo.income_stmt.round(2))
    
    print("\nCash Flow Projections:")
    print(lbo.cash_flow.round(2))
    
    print("\nBalance Sheet Projections:")
    print(lbo.balance_sheet.round(2))