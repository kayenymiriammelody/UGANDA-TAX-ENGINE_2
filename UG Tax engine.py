#!/usr/bin/env python
# coding: utf-8

# In[1]:


#imports and custom exceptions
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
class TaxError(Exception):
    """Base exception for tax calculator errors."""
    pass
class InvalidIncomeError(TaxError):
    """Raised when income or a monetary amount is invalid."""
    pass
class NoScheduleForDateError(TaxError):
    """Raised when no tax schedule exists for the requested date."""
    pass


# In[2]:


#Ensuring that all calculations use decimal + other rules
@dataclass(frozen=True)
class Money:
    amount: Decimal
    def __post_init__(self):
        value = Decimal(str(self.amount))
        if not value.is_finite():
            raise InvalidIncomeError("Money must be a finite number.")

        if value < 0:
            raise InvalidIncomeError("Money cannot be negative.")

        object.__setattr__(self, "amount",value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount + other.amount)

    def __mul__(self, rate):
        return Money(self.amount * Decimal(str(rate)))

    def __lt__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount < other.amount

    def __repr__(self):
        return f"UGX {self.amount:,.0f}"


# In[5]:


#abstract tax base class
@dataclass
class TaxContext:
    income: Money
    allowances: Money = Money(Decimal("0"))
    resident: bool = True
    tax_date: date = date(2026, 10, 1)
    deduction_before_paye: Money = Money(Decimal("0"))
@dataclass
class TaxResult:
    tax: Money
    description: str
class Tax(ABC):
    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        pass


# In[6]:


#PAYE class using rates released by URA on 1/7/2026
class PAYE(Tax):
    def calculate(self, ctx: TaxContext) -> TaxResult:
        if ctx.tax_date < date(2026, 7, 1):
            raise NoScheduleForDateError("This calculator contains the PAYE schedule effective from 1 July 2026 only.")
        gross = ctx.income + ctx.allowances

        if ctx.deduction_before_paye.amount > gross.amount:
            raise InvalidIncomeError("Pre-PAYE deduction cannot exceed employment income.")
        income = gross.amount - ctx.deduction_before_paye.amount

        if income < 0:
            raise InvalidIncomeError("Taxable income cannot be negative.")

        if ctx.resident:
            if income <= Decimal("335000"):
                tax = Decimal("0")

            elif income <= Decimal("410000"):
                tax = (income - Decimal("335000")) * Decimal("0.20")

            elif income <= Decimal("485000"):
                tax = (Decimal("15000")+ (income - Decimal("410000")) * Decimal("0.25"))

            else:
                tax = (Decimal("33750")+ (income - Decimal("485000")) * Decimal("0.30"))

        else:
            if income <= Decimal("335000"):
                tax = income * Decimal("0.10")

            elif income <= Decimal("410000"):
                tax = (Decimal("33500")+ (income - Decimal("335000")) * Decimal("0.20"))

            else:
                tax = (Decimal("48500")+ (income - Decimal("410000")) * Decimal("0.30"))

        # Additional 10% on the amount above UGX 10 million.
        if income > Decimal("10000000"):
            tax += (income - Decimal("10000000")) * Decimal("0.10")

        return TaxResult(tax=Money(tax),description="Monthly PAYE")


# In[7]:


#NSSF class
class NSSF(Tax):
    def calculate(self, ctx: TaxContext) -> TaxResult:
        gross = ctx.income + ctx.allowances
        employee_contribution = gross * Decimal("0.05")
        return TaxResult(tax=employee_contribution,description="Employee NSSF contribution (5%)")

    def employer_contribution(self, ctx: TaxContext) -> Money:
        gross = ctx.income + ctx.allowances
        return gross * Decimal("0.10")


# In[8]:


#local service tax
class LocalServiceTax(Tax):
    def __init__(self, amount):
        self.amount = Money(amount)

    def calculate(self, ctx: TaxContext) -> TaxResult:
        return TaxResult(tax=self.amount,description="Local Service Tax")


# In[9]:


#Payroll
class Payroll:

    def __init__(self, lst_amount):
        self.paye = PAYE()
        self.nssf = NSSF()
        self.lst = LocalServiceTax(lst_amount)

    def calculate(self, ctx):
        gross = ctx.income + ctx.allowances

        nssf_result = self.nssf.calculate(ctx)
        lst_result = self.lst.calculate(ctx)
        paye_result = self.paye.calculate(ctx)

        total_deductions = (nssf_result.tax.amount+ lst_result.tax.amount+ paye_result.tax.amount)

        if total_deductions > gross.amount:
            raise InvalidIncomeError("Total deductions exceed gross pay.")

        net_pay = Money(gross.amount - total_deductions)

        return {"gross_pay": gross,"employee_nssf": nssf_result.tax,"employer_nssf": self.nssf.employer_contribution(ctx),
            "local_service_tax": lst_result.tax,"paye": paye_result.tax,"net_pay": net_pay}


# In[11]:


#tesing the payroll
ctx = TaxContext(
    income=Money("2000000"),
    allowances=Money("200000"),
    resident=True
)

payroll = Payroll(lst_amount="5000")
result = payroll.calculate(ctx)

for item, amount in result.items():
    print(item, ":", amount)


# In[12]:


#VAT calculator
class VAT(Tax):

    def calculate(self, ctx: TaxContext) -> TaxResult:
        raise TaxError("Use calculate_invoices() for the VAT module.")

    def calculate_invoices(self, sales, purchases):
        output_vat = Decimal("0")
        input_vat = Decimal("0")

        rates = {"standard": Decimal("0.18"),"zero": Decimal("0"),"exempt": Decimal("0")}

        for invoice in sales:
            amount = Decimal(str(invoice["amount"]))
            supply_type = invoice["type"]

            if amount < 0:
                raise InvalidIncomeError("Invoice amount cannot be negative.")

            if supply_type not in rates:
                raise TaxError("Unknown sales VAT category.")

            output_vat += amount * rates[supply_type]

        for invoice in purchases:
            amount = Decimal(str(invoice["input_vat"]))

            if amount < 0:
                raise InvalidIncomeError("Input VAT cannot be negative.")

            if invoice.get("recoverable", False):
                input_vat += amount

        net_vat = output_vat - input_vat

        return {"output_vat": Money(output_vat),"recoverable_input_vat": Money(input_vat),"net_vat_payable": Money(max(Decimal("0"), net_vat)),
            "excess_input_vat": Money(max(Decimal("0"), -net_vat))}


# In[23]:


#test the vat class
sales = [
    {"amount": "1000000", "type": "standard"},
    {"amount": "200000", "type": "zero"},
    {"amount": "100000", "type": "exempt"}
]

purchases = [
    {"input_vat": "90000", "recoverable": True},
    {"input_vat": "18000", "recoverable": False}
]

vat = VAT()
print(vat.calculate_invoices(sales, purchases))


# In[14]:


#corporate income tax = 30%
class CorporateIncomeTax(Tax):

    def __init__(self, rate=Decimal("0.30")):
        self.rate = Decimal(str(rate))

        if not Decimal("0") <= self.rate <= Decimal("1"):
            raise TaxError("Corporate tax rate must be between 0 and 1.")

    def calculate(self, ctx: TaxContext) -> TaxResult:
        raise TaxError("Use calculate_profit() for corporate income tax.")

    def calculate_profit(self, revenue, allowable_deductions):
        revenue = Decimal(str(revenue))
        deductions = Decimal(str(allowable_deductions))

        if revenue < 0 or deductions < 0:
            raise InvalidIncomeError("Revenue and deductions cannot be negative.")

        chargeable_income = max(Decimal("0"), revenue - deductions)

        tax = chargeable_income * self.rate

        return {"chargeable_income": Money(chargeable_income),"corporate_tax": Money(tax)}


# In[22]:


#testing the corporate income tax class
company_tax = CorporateIncomeTax()
result = company_tax.calculate_profit(revenue="50000000",allowable_deductions="30000000")
print(result)


# In[16]:


#paye test boundaries
def test_paye_boundaries():
    paye = PAYE()

    cases = [("335000", "0"),("335001", "0"),("410000", "15000"),("410001", "15000"),("485000", "33750"),("485001", "33750"),("10000000", "2888250"),
        ("10000001", "2888250") ]

    for income, expected_tax in cases:
        ctx = TaxContext(income=Money(income))
        actual = paye.calculate(ctx).tax.amount
        expected = Money(expected_tax).amount

        assert actual == expected, (f"Income {income}: expected {expected}, got {actual}")

    print("All PAYE boundary tests passed.")

test_paye_boundaries()


# In[18]:


"""withholding tax-tax deducted by a payer and remitted to URA on behalf of the recipient"""
class WithholdingTax(Tax):

    def __init__(self, rate=Decimal("0.06")):
        self.rate = Decimal(str(rate))

        if not Decimal("0") <= self.rate <= Decimal("1"):
            raise TaxError("Withholding tax rate must be between 0 and 1.")

    def calculate(self, ctx: TaxContext) -> TaxResult:
        tax = ctx.income * self.rate

        return TaxResult(tax=tax,description="Withholding Tax")


# In[21]:


#testing the withholding tax class
payment = TaxContext(income=Money("2000000"))
wht = WithholdingTax()
result = wht.calculate(payment)

print("Gross payment:", payment.income)
print("Withholding tax:", result.tax)
print("Net payment:", Money(payment.income.amount - result.tax.amount))


# In[19]:


"""rental icome tax-Individuals: 12% of gross rental income after the annual UGX 2,820,000 allowance.
Companies: 30% of chargeable rental income, calculated after allowable deductions."""
class RentalIncomeTax(Tax):
    def __init__(self, taxpayer_type="individual"):
        if taxpayer_type not in ("individual", "company"):
            raise TaxError("Taxpayer type must be 'individual' or 'company'.")
        self.taxpayer_type = taxpayer_type

    def calculate(self, ctx: TaxContext) -> TaxResult:
        gross_rent = ctx.income.amount
        deductions = ctx.allowances.amount

        if deductions > gross_rent:
            raise InvalidIncomeError("Rental deductions cannot exceed gross rental income.")

        if self.taxpayer_type == "individual":
            taxable_rent = max(Decimal("0"),gross_rent - Decimal("2820000"))
            tax = taxable_rent * Decimal("0.12")

        else:
            taxable_rent = max(Decimal("0"),gross_rent - deductions)
            tax = taxable_rent * Decimal("0.30")

        return TaxResult(tax=Money(tax),description=f"Rental Income Tax ({self.taxpayer_type})")


# In[20]:


#testing the rental icome tax
# individual landlord
individual_rent = TaxContext(income=Money("11000000"))

individual_tax = RentalIncomeTax("individual")
print(individual_tax.calculate(individual_rent))

# company landlord
company_rent = TaxContext(income=Money("13000000"),allowances=Money("3000000"))

company_rental_tax = RentalIncomeTax("company")
print(company_rental_tax.calculate(company_rent))


# In[24]:


#why using float in tax calculations is not advisable
income = 0.1
tax_rate = 0.2

tax = income * tax_rate

print(tax)
print(tax == 0.02)


# In[ ]:




