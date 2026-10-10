# UGANDA-TAX-ENGINE_2
In Uganda, various Taxes are levied upon Employees, businesses and property. Some include: Pay As You Earn(PAYE), LST(Local Service Tax), National Social Security Fund(NSSF) and Consumption and indirect taxes( Value Added Tax(VAT) and Excise Duty).This project aims to create a  Ugandan Tax calculator using principles of Object Oriented Programming. Tax rates used were obtained from Uganda Revenue Authority and the document has been uploaded for reference.
This code was edited using  an Artificial Intelligence tool(CODEX).
### IMPLEMENTATION
- An abstract tax base was created to enforce a common interface and make the system easier to extend, test, and maintain.
- Using Decimal only, a Money value object was created in Ugandan shillings. This is because tax calculations involve money, where precision and explicit rounding are essential.
- Custom exception hierarchies were created for TaxError, InvalideIncomeError and NoScheduleForDateError.
- Boundary tests were created.
- Property based tests were created with hypothesis.
- PAYE calculator using the updated URA rates was created.
- A payroll pipeline that computes NSSF, Local Service Tax (configurable), PAYE, and net pay was created. LST is direct local government tax levied on income of employees earning more than UGX 100,000.
- A Value Added Tax (VAT) module was created. This is tax applied to a product or service whenever value is added to it.
- A Corporate income tax module was created. This is the tax on business profits of corporate entities.
- A withholding tax  module was created. This is an advance tax deducted at the source of a transaction.
- A rental income tax module was created. This is tax levied on earnings generated from leasing or renting immovable property.
- Demonstrated why float is not advisable for tax calculations.

### RECOMMENDATIONS
- Float shouldn’t be used in tax related calculations since it causes precision errors that may cumulatively be significant.
- Inheritance can be used wherever the calculate method is utilized for example in NSSF and PAYE calculations. It would however be avoided in regards to Money and Tax, and TaxContext and Tax.
  
