# متدولوژی محاسبات مالی، گمرکی و سناریوسازی سودآوری (CALCULATION_METHODOLOGY.md)

این سند مرجع ریاضی، فرمول‌های حسابداری صنعتی و منطق محاسبات ماژول `core/calculator.py` در پروژه **iTrade China** است.

---

## ۱. اصول حاکم بر محاسبات
1. **دقت قطعی اعشاری (Pure Decimal Arithmetic):** تمام محاسبات ارزی و ریالی با استفاده از کلاس `Decimal` در پایتون و ماژول `core.money.Money` با روش گردکردن بانکداری `ROUND_HALF_UP` انجام می‌شود. استفاده از متغیرهای `float` به دلیل ایجاد خطاهای باینری (مانند `0.1 + 0.2 != 0.3`) کاملاً منسوخ شده است.
2. **نسخه‌بندی قوانین و تاریخ‌گذاری:** کلیه نرخ‌های حقوق ورودی، سود بازرگانی و مالیات بر ارزش افزوده دارای برچسب نسخه هستند (`IR-CUSTOMS-1403-1404-V2` به تاریخ مارس ۲۰۲۶) و هیچ مقداری فرض همیشگی گرفته نمی‌شود.
3. **تفکیک واحد پولی:** کلیه مقادیر فاکتورهای داخلی به **تومان (IRT)** گرد شده و در صورت لزوم تبدیل به ریال، ضریب صریح ۱۰ اعمال می‌شود.

---

## ۲. شرایط بازرگانی بین‌المللی (Incoterms 2020) و تخصیص هزینه‌ها

سامانه iTrade China به صورت دقیق هزینه‌ها را بر مبنای اینکوترمز قرارداد تخصیص می‌دهد:

1. **شرایط تحویل درب کارخانه (EXW - Ex Works):**
   - خریدار موظف به پرداخت حمل داخلی در چین (از کارخانه تا فرودگاه یا بندر بارگیری) و ترخیص صادراتی چین (Export Customs Clearance & THC) است.
   - سرفصل هزینه‌ای `china_origin_handling` (معادل ۲٪ ارزش کالا) به بهای تمام‌شده مستقیم اضافه می‌شود.
2. **شرایط تحویل روی عرشه (FOB - Free on Board):**
   - فروشنده چینی کلیه هزینه‌های حمل داخلی مبدأ و ترخیص گمرکی چین را تقبل نموده است.
   - هزینه `china_origin_handling` برای خریدار برابر با **صفر** محاسبه می‌شود.
3. **شرایط بهای کالا، بیمه و کرایه (CIF - Cost, Insurance & Freight):**
   - فروشنده چینی کرایه حمل بین‌المللی تا بندر مقصد (بندرعباس / فرودگاه امام) و بیمه باربری دریایی را در فاکتور لحاظ کرده است.
   - ردیف‌های `international_freight` و `cargo_insurance` در سرفصل‌های بهای تمام‌شده خریدار برابر با **صفر** منظور می‌شوند.

بنابراین، برای یک مظنه یکسان فاکتور کارخانه چین، رابطه بهای تمام‌شده قطعی به صورت زیر برقرار است:
$$\text{Landed Cost (EXW)} > \text{Landed Cost (FOB)} > \text{Landed Cost (CIF)}$$

---

## ۳. فرمول‌های ریاضی سرفصل‌های هزینه (Line Items)

### ۲.۱. هزینه خرید مبدأ و کارمزد حواله
$$\text{Unit Purchase (IRR/IRT)} = \text{Unit CNY} \times \text{Exchange Rate (RMB/IRT)}$$
$$\text{Remittance Fee} = \text{Unit Purchase} \times 1.5\%$$
$$\text{Inspection (QC) Unit} = \frac{\text{Batch Inspection USD} \times \text{Exchange Rate (USD/IRT)}}{\text{Batch Quantity}}$$

### ۲.۲. وزن محاسباتی و کرایه حمل بین‌المللی (Chargeable Weight)
- **حمل هوایی (Air Cargo):**
  $$\text{Volumetric Weight (kg)} = \frac{L(\text{cm}) \times W(\text{cm}) \times H(\text{cm})}{5000} \quad (\text{یا } \text{CBM} \times 167)$$
  $$\text{Chargeable Weight} = \max(\text{Actual Weight}, \text{Volumetric Weight})$$
  $$\text{Air Freight (IRT)} = \text{Chargeable Weight} \times \text{Rate (USD/kg)} \times \text{USD Rate}$$

- **حمل دریایی (Sea Freight LCL):**
  $$\text{Sea Freight (IRT)} = \text{Volume (CBM)} \times \text{Rate (USD/CBM)} \times \text{USD Rate}$$

### ۲.۳. ارزش CIF گمرک ایران و بیمه باربری
$$\text{C\&F} = \text{Unit Purchase} + \text{Freight}$$
$$\text{Insurance} = \text{C\&F} \times 0.5\%$$
$$\text{CIF Value} = \text{C\&F} + \text{Insurance}$$

### ۲.۴. حقوق ورودی، سود بازرگانی و مالیات بر ارزش افزوده (VAT)
$$\text{Customs Duty} = \text{CIF} \times \text{Tariff Rate}\%$$
$$\text{Commercial Benefit} = \text{CIF} \times \text{Benefit Rate}\%$$
$$\text{Taxable Base} = \text{CIF} + \text{Customs Duty} + \text{Commercial Benefit}$$
$$\text{VAT (10\%)} = \text{Taxable Base} \times 10\%$$

### ۲.۵. هزینه‌های ترخیص، انبارداری و دموراژ
$$\text{Clearance Brokerage} = \text{CIF} \times 4.5\%$$
$$\text{Demurrage Reserve Unit} = \frac{\text{Batch Demurrage Reserve (IRT)}}{\text{Batch Quantity}}$$
$$\text{Domestic Logistics} = \text{CIF} \times 3.0\%$$

### ۲.۶. هزینه خواب سرمایه و ضایعات (Financing & Risk)
$$\text{Direct Landed Subtotal} = \text{Purchase} + \text{Remittance} + \text{QC} + \text{Freight} + \text{Insurance} + \text{Duty} + \text{Benefit} + \text{VAT} + \text{Brokerage} + \text{Demurrage} + \text{Logistics}$$
$$\text{Financing Cost} = \text{Direct Landed Subtotal} \times \left(\frac{24\%}{12}\right) \times \text{Months}$$
$$\text{Scrap/Defect Reserve} = \text{Direct Landed Subtotal} \times \text{Defect Rate}\% \quad (1\% \text{ to } 4\%)$$
$$\text{Total Landed Cost per Unit} = \text{Direct Landed Subtotal} + \text{Financing Cost} + \text{Scrap Reserve}$$

---

## ۳. شاخص‌های سودآوری، مارجین و نقطه سر به سر

### ۳.۱. درآمد مؤثر فروش با کسر کمیسیون توزیع
$$\text{Effective Net Revenue} = \text{Target Selling Price} \times (1 - \text{Marketplace Fee}\%)$$
$$\text{Net Profit per Unit} = \text{Effective Net Revenue} - \text{Total Landed Cost}$$

### ۳.۲. حاشیه سود و بازده سرمایه (Margin vs Markup vs ROI)
$$\text{Net Margin \%} = \left(\frac{\text{Net Profit}}{\text{Target Selling Price}}\right) \times 100$$
$$\text{Markup \%} = \left(\frac{\text{Net Profit}}{\text{Total Landed Cost}}\right) \times 100$$
$$\text{ROI \%} = \text{Markup \%} \quad (\text{بازده سرمایه در گردش پارت وارداتی})$$

### ۳.۳. نقطه سر به سر قیمتی و تعدادی (Break-Even)
- **حداقل قیمت فروش بدون ضرر (Break-Even Selling Price):**
  $$\text{Break-Even Price} = \frac{\text{Total Landed Cost}}{1 - \text{Marketplace Fee}\%}$$
- **حداقل تیراژ پوشش‌دهنده هزینه‌های ثابت سفارش (Break-Even Units):**
  $$\text{Contribution Margin Unit} = \text{Effective Revenue} - \text{Variable Unit Costs}$$
  $$\text{Break-Even Units} = \left\lceil \frac{\text{Fixed Batch Overhead (QC + Demurrage)}}{\text{Contribution Margin Unit}} \right\rceil$$

---

## ۴. ماتریس سناریوهای ۳گانه (3-Scenario Modeling)

| متغیر | حالت واقع‌بینانه (Realistic) | حالت خوش‌بینانه (Optimistic) | حالت بدبینانه (Pessimistic) |
| :--- | :--- | :--- | :--- |
| **نرخ ارز حواله** | نرخ روز صرافی نیما/بازار | ۴٪ پایین‌تر (تقویت ریال یا تخصیص دولتی) | ۱۰٪ بالاتر (جهش تورمی نرخ ارز) |
| **کرایه حمل بین‌المللی** | نرخ پیش‌فاکتور استاندارد کارگو | ۵٪ تخفیف تجمیعی حمل | ۲۰٪ افزایش به دلیل نوسانات سوخت/فصل شلوغی |
| **دوره خواب سرمایه** | ۳ ماه (فرآیند متداول گمرکی) | ۲ ماه (ترخیص مسیر سبز با حداقل ایستایی) | ۵ ماه (صف طولانی ارزی و آزمایشگاه تخصصی) |
| **ذخیره دموراژ کانتینر** | ۵ میلیون تومان برای کل پارت | ۲ میلیون تومان | ۱۵ میلیون تومان (تاخیر در اظهار اسناد) |
| **نرخ ضایعات و مرجوعی** | ۲.۰٪ | ۱.۰٪ | ۴.۰٪ |
| **قیمت فروش بازار ایران** | میانگین بازار آنلاین | ۵٪ بالاتر به دلیل فروش باکیفیت و بازاریابی | ۸٪ پایین‌تر بر اثر جنگ قیمتی رقبا |
