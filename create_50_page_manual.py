import os
import pymupdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PDF_FILENAME = "TechMart_Enterprise_Operations_and_Support_Manual_50Pages.pdf"

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw accurate 'Page X of Y' footers
    and running enterprise headers on every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Header (Pages 2-50)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "TechMart Enterprise Customer Support & Operations Manual (Master Edition v4.0)")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "Confidential | Internal & Customer Support Knowledge Base | Updated October 2026")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_str)
        self.restoreState()


def build_manual():
    doc = SimpleDocTemplate(
        PDF_FILENAME,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=10,
    )
    
    h1_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#2B6CB0"),
        spaceAfter=6,
    )
    
    h2_style = ParagraphStyle(
        "SubHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "ManualBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ManualBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#2D3748"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.white,
    )

    story = []

    # 50 Pages Definitions
    pages_data = [
        # Page 1
        {
            "title": "TechMart Enterprise Customer Support Manual",
            "section": "Master Table of Contents & Operations Index",
            "text": [
                "<b>Document Purpose:</b> This comprehensive 50-page enterprise manual serves as the authoritative single source of truth for all TechMart consumer policies, enterprise client workflows, technical support resolutions, and legal escalation frameworks.",
                "<b>Scope of Coverage:</b> All policies apply to online transactions at techmart.com, customer interactions through mobile applications, phone support desks, live chat, and all 380 brick-and-mortar stores across the United States, as well as cross-border operations across 68 authorized international countries.",
                "<b>Master Directory Overview:</b>",
            ],
            "bullets": [
                "Pages 1–2: Master Table of Contents & Corporate Overview",
                "Pages 3–6: Flagship Product Catalogue & Technical SKU Specifications",
                "Pages 7–9: Pricing Framework, Price Match Guarantee & Tax Compliance",
                "Pages 10–12: Payment Methods, Buy Now Pay Later (BNPL) & Micro-Financing",
                "Pages 13–15: Order Placement Lifecycle, Address Diverts & Cancellation Rules",
                "Pages 16–18: Domestic Logistics, Free Shipping Thresholds & Carrier SLAs",
                "Pages 19–21: International Shipping, Regional Tariffs, DDU/DDP & Currency Conversion",
                "Pages 22–25: Standard Returns, Category Windows, Restocking Fees & Inspection Criteria",
                "Pages 26–29: Manufacturer Warranties, TechCare Plans & Accidental Damage Coverage",
                "Pages 30–32: Technical Support Tiers, Troubleshooting Trees & Remote Diagnostics",
                "Pages 33–35: In-Store Fix Desk Services, Diagnostic Fees & Setup Offerings",
                "Pages 36–38: User Accounts, Password Encryption, MFA/2FA & Anti-Fraud Security",
                "Pages 39–41: TechMart Plus Loyalty Program, Cashback Accrual & Family Plans",
                "Pages 42–44: TechMart for Business, Tiered Volume Discounts, MDM & Loaner Fleet",
                "Pages 45–46: GreenCycle Environmental Program, Recycling Standards & Trade-Ins",
                "Pages 47–48: Data Privacy Policy, GDPR/CCPA Rights & Record Retention",
                "Pages 49–50: Formal Complaint Escalation, Safety Hazards & Emergency Directory",
            ]
        },
        # Page 2
        {
            "title": "Section 1 — Corporate Overview & Support Philosophy",
            "section": "1.1 Company History & Support Architecture",
            "text": [
                "TechMart was established in 2012 in Seattle, Washington, with the vision of making modern electronics, computing hardware, and smart appliances accessible with absolute consumer transparency. Operating over 380 flagship stores across 48 states and serving over 4 million registered accounts, TechMart maintains carbon-neutral fulfillment centers in North America and Europe.",
                "Our customer engagement infrastructure relies on a rigorous Three-Tier Service Model designed to handle over 150,000 inquiries monthly with sub-minute first-response benchmarks.",
            ],
            "table": [
                ["Support Tier", "Staffing & Channels", "Operational Hours", "Target First Response"],
                ["Tier 1: AI Support", "Website & Mobile App Chatbot", "24/7/365 Non-Stop", "< 5 Seconds"],
                ["Tier 2: Live Specialists", "Human Live Chat & Voice Lines", "Mon–Sun: 8:00 AM – 10:00 PM EST", "< 3 Minutes"],
                ["Tier 3: Escalations Desk", "Hardware Engineers, Legal & Billing", "Mon–Fri: 9:00 AM – 7:00 PM EST", "< 15 Minutes (Supervisor)"],
                ["In-Store Fix Desk", "380 Retail Stores Nationwide", "Mon–Sat: 10:00 AM – 9:00 PM", "< 10 Minute Wait Time"],
            ]
        },
        # Page 3
        {
            "title": "Section 2 — Product Catalogue: Mobile Computing",
            "section": "2.1 Flagship Smartphones & Cellular Devices",
            "text": [
                "TechMart stocks over 50,000 distinct SKUs directly from global Tier-1 original equipment manufacturers (OEMs). All cellular products are verified carrier-unlocked and sold with valid North American and European regulatory certifications.",
            ],
            "table": [
                ["Device Subcategory", "Supported Brands", "Retail Price Range", "Factory Warranty"],
                ["Premium Flagship Phones", "Apple iPhone, Samsung Galaxy S/Z, Google Pixel Pro", "$899 – $1,899", "1 Year Limited OEM"],
                ["Mid-Range Smartphones", "OnePlus, Motorola, Samsung Galaxy A-Series", "$299 – $699", "1 Year Limited OEM"],
                ["Rugged & Outdoor Phones", "CAT, Sonim, Ulefone", "$399 – $799", "2 Year Limited OEM"],
                ["Tablets & E-Readers", "Apple iPad, Samsung Tab, Kindle Oasis", "$199 – $1,499", "1 Year Limited OEM"],
            ],
            "bullets": [
                "Carrier Unlocking: All devices are factory unlocked and compatible with GSM, CDMA, and 5G Sub-6/mmWave networks.",
                "SIM Activation Support: Complimentary eSIM transfer and physical SIM provisioning available in all retail stores.",
                "Box Contents: Certified original charging cables and warranty documentation included. Power adapters vary by OEM.",
            ]
        },
        # Page 4
        {
            "title": "Section 2 — Product Catalogue: Laptops & Workstations",
            "section": "2.2 Computing Hardware & Professional Workstations",
            "text": [
                "TechMart offers computing hardware ranging from lightweight student ultrabooks to enterprise AI workstations and high-refresh-rate gaming rigs.",
            ],
            "table": [
                ["Category", "Featured Models", "Base Hardware Spec", "Price Range"],
                ["Ultrabooks & 2-in-1s", "MacBook Air, Dell XPS 13, Lenovo Yoga 9i", "Intel Core Ultra 7 / Apple M3, 16GB RAM", "$999 – $2,199"],
                ["Gaming Laptops", "ASUS ROG Strix, Razer Blade 16, Alienware m18", "RTX 4080/4090, 240Hz QHD Display, 32GB RAM", "$1,499 – $3,899"],
                ["Mobile Workstations", "ThinkPad P-Series, Dell Precision 7000", "NVIDIA RTX 4000 Ada, ECC RAM, ISV Certified", "$2,299 – $5,499"],
                ["Desktop Towers", "Custom TechMart Forge rigs, HP Omen, Mac Studio", "Liquid-cooled Core i9/Ryzen 9, 64GB DDR5", "$1,299 – $6,999"],
            ],
            "bullets": [
                "Pre-installed OS: Windows 11 Pro or macOS Sonoma with zero third-party bloatware on TechMart Signature editions.",
                "Complimentary Setup: 30-day initial driver configuration and automated cloud recovery image creation included.",
            ]
        },
        # Page 5
        {
            "title": "Section 2 — Product Catalogue: Televisions & Audio",
            "section": "2.3 Displays, Home Theatre & Soundbars",
            "text": [
                "TechMart carries cutting-edge visual displays from 32 inches to 98 inches, covering Mini-LED, QD-OLED, and commercial micro-LED panels.",
            ],
            "table": [
                ["Display Type", "Size Range", "Refresh Rate & Panel Tech", "Starting Price"],
                ["4K OLED Televisions", "42\" – 83\"", "120Hz/144Hz G-Sync, Self-lit Pixels (LG/Sony)", "$899.99"],
                ["8K Neo QLED TVs", "65\" – 98\"", "Real 8K AI Quantum Upscaling, 2000+ nits (Samsung)", "$2,199.99"],
                ["Dolby Atmos Soundbars", "3.1 to 9.1.4 channels", "Wireless subwoofers, eARC, 500W–1000W", "$249.99"],
                ["Commercial Monitors", "27\" – 49\" Curved", "Ultrawide 32:9, 240Hz, USB-C 90W PD", "$499.99"],
            ],
            "bullets": [
                "Mounting Compatibility: Standard VESA patterns supported across all displays. Wall mounting brackets sold separately.",
                "White-Glove Delivery Requirement: All screens 65 inches and above require mandatory scheduled delivery windows.",
            ]
        },
        # Page 6
        {
            "title": "Section 2 — Product Catalogue: Smart Home & Peripherals",
            "section": "2.4 IoT Automation, Wearables & Peripherals",
            "text": [
                "Smart living solutions integrate seamlessly with Apple HomeKit, Google Home, Amazon Alexa, and open-source Matter protocols.",
            ],
            "bullets": [
                "Smart Climate: Nest Learning Thermostat 4th Gen ($279.99), Ecobee Smart Thermostat Premium ($249.99).",
                "Home Security: Ring Video Doorbell Pro ($229.99), Arlo Ultra 2 4K 4-Camera Wireless System ($799.99).",
                "Smart Locks: Schlage Encode Plus with Apple HomeKey ($319.99), Yale Assure Lock 2 ($199.99).",
                "Wearable Devices: Apple Watch Ultra 2 ($799.00), Garmin Fenix 7 Pro ($899.99), Whoop 4.0 bands.",
                "Hygiene Restriction on Wearables: Open-box in-ear earphones and worn smartwatch sports bands cannot be returned for change of mind due to state sanitation regulations unless defective within 14 days.",
                "Computer Peripherals: Mechanical keyboards, high-DPI ergonomic mice, Thunderbolt 4 docks, and NVMe portable SSDs.",
            ]
        },
        # Page 7
        {
            "title": "Section 3 — Pricing Framework & Price Matching",
            "section": "3.1 Price Match Guarantee & Authorized Retailers",
            "text": [
                "TechMart guarantees competitive pricing. We match the current published price of any identical, in-stock brand-new product from authorized national competitors at purchase or within 14 calendar days post-sale.",
                "<b>Authorized Competitors for Price Match:</b> Amazon (shipped & sold by Amazon.com directly), Best Buy, Walmart.com (excluding third-party marketplace sellers), B&H Photo Video, Newegg (direct only), and Costco Wholesale.",
            ],
            "table": [
                ["Eligible Products", "Exclusions & Disqualifications", "Verification Method"],
                ["Factory-sealed identical SKUs", "Marketplace 3rd-party merchants", "Live competitor URL / Print flyer"],
                ["In-stock ready to ship", "Open-box, refurbished, clearance", "Must match color, model & storage"],
                ["Standard advertised retail prices", "Black Friday / Cyber Week hourly doorbusters", "Proof reviewed by support agent"],
            ],
            "bullets": [
                "Price Match Refund Method: If price drops within 14 days, the difference is refunded to original payment method or issued as store credit with an extra 5% bonus.",
            ]
        },
        # Page 8
        {
            "title": "Section 3 — Sales Tax & Exemption Compliance",
            "section": "3.2 State Taxes & Institutional Tax-Exempt Status",
            "text": [
                "TechMart automatically calculates and collects local and state sales taxes across all 48 contiguous US states, Alaska, and Hawaii in compliance with South Dakota v. Wayfair nexus legislation.",
            ],
            "bullets": [
                "Tax Exemption Eligibility: 501(c)(3) non-profit charities, accredited public/private educational institutions, state/local government entities, and certified wholesale resellers.",
                "Submission Workflow: Customers must create an account and navigate to Account &rarr; Tax Exemption Portal to upload signed state-issued exemption certificates.",
                "Verification Turnaround: Institutional certificates are reviewed and validated within 1 business day (24 hours).",
                "Retroactive Tax Refunds: If an exempt organization placed an order before approval, tax refund requests must be submitted within 30 days of the invoice date accompanied by order number TM-ORD-XXXXXXX.",
            ]
        },
        # Page 9
        {
            "title": "Section 3 — Promotional Codes & Education Discounts",
            "section": "3.3 Coupons, Promo Code Stacking & Student Perks",
            "text": [
                "Promotional coupon codes provide exclusive discounts for retail shoppers and verified loyalty members.",
            ],
            "bullets": [
                "Case-Insensitive Input: Codes such as SAVE10 or save10 are processed identically at online checkout.",
                "Single-Code Limitation: Only one promotional coupon code can be applied per order. Coupons cannot be stacked with seasonal sitewide clearance events unless explicitly denoted as 'Stackable'.",
                "Student, Teacher & Military Perks: Verified students, active duty personnel, and first responders receive a flat 10% discount off accessories and 5% off select laptops via ID.me verification.",
                "Expiration Guidelines: Coupon discounts cannot be applied retroactively to orders placed before the promotional window began or after midnight EST on the stated expiration date.",
            ]
        },
        # Page 10
        {
            "title": "Section 4 — Accepted Payment Methods",
            "section": "4.1 Payment Gateways, Cards & Digital Wallets",
            "text": [
                "TechMart employs Level-1 PCI-DSS compliant payment processing, utilizing 256-bit AES encryption through Stripe and Adyen gateways.",
            ],
            "table": [
                ["Payment Instrument", "Processing Fee", "Settlement Time", "Security Validation"],
                ["Visa, MasterCard, Amex, Discover", "0% Fee", "Immediate Instant Capture", "3D Secure 2.0 / CVV Match"],
                ["Apple Pay / Google Pay", "0% Fee", "Immediate Tokenized Auth", "Biometric Touch/FaceID Token"],
                ["PayPal & PayPal Credit", "0% Fee", "Immediate Instant", "PayPal Two-Factor Shield"],
                ["TechMart Gift Cards", "0% Fee", "Immediate Deducted", "16-digit PIN + Card Number"],
                ["Direct Bank Transfer (ACH/Wire)", "0% Fee", "2 to 3 Business Days", "Mandatory for orders >$5,000"],
            ],
            "bullets": [
                "Gift Card Policies: Valid for purchase of all physical and digital merchandise. Balances never expire and cannot be redeemed for cash or refunded.",
            ]
        },
        # Page 11
        {
            "title": "Section 4 — Buy Now Pay Later (BNPL) Solutions",
            "section": "4.2 Klarna, Affirm & PayPal Pay in 4 Workflows",
            "text": [
                "Flexible installment solutions allow customers to divide their purchases into manageable payments at 0% APR for qualified buyers.",
            ],
            "table": [
                ["Provider", "Order Value Limits", "Installment Structure", "Late Fees"],
                ["Klarna Pay in 4", "$35 – $1,500", "4 equal payments every 2 weeks (0% APR)", "Up to $7.00 per missed payment"],
                ["Klarna Monthly Financing", "$500 – $4,000", "6, 12, or 24 monthly installments", "0% – 24.99% APR depending on credit"],
                ["Affirm Financing", "$150 – $10,000", "3, 6, 12, or 36 months", "0% – 36% APR; zero late penalty fees"],
                ["PayPal Pay in 4", "$30 – $1,500", "4 bi-weekly payments", "Zero late fees"],
            ],
            "bullets": [
                "Refunds on BNPL Orders: When a return is processed for a Klarna or Affirm order, TechMart returns the funds directly to the provider, which automatically credits paid amounts and cancels outstanding balances.",
            ]
        },
        # Page 12
        {
            "title": "Section 4 — TechMart Co-Branded Financing",
            "section": "4.3 TechMart Credit Card & Promotional APR Terms",
            "text": [
                "The TechMart Mastercard, issued by Citi Bank, offers dedicated store financing and accelerated cashback rewards for retail shoppers.",
            ],
            "bullets": [
                "24-Month Interest-Free Financing: Available on purchases of $499 or more when the total account balance is paid in full within 24 billing cycles.",
                "Post-Promotional Interest APR: If any balance remains unpaid at the end of the 24-month period, a variable regular APR of 29.99% is applied retroactively to the date of purchase.",
                "Minimum Monthly Payments: Monthly minimum required payments equal 1% of the total balance plus interest or $35, whichever is greater.",
                "Cashback Earning Alternative: Cardholders may elect to choose 5% instant cashback in TechMart rewards points instead of the 24-month financing offer.",
                "Late Payment Charges: Up to $39 for payments received after the monthly due date.",
            ]
        },
        # Page 13
        {
            "title": "Section 5 — Order Processing & Lifecycle",
            "section": "5.1 Order Verification, Picking & Fulfillment Stages",
            "text": [
                "Every order placed on techmart.com transitions through standard operational states logged transparently in the customer dashboard.",
            ],
            "table": [
                ["Order Status Code", "System Definition", "Customer Action Required", "Avg Stage Duration"],
                ["Pending Verification", "Payment gateway review & address check", "None (system automated)", "5 – 15 Minutes"],
                ["Confirmed", "Inventory allocated in regional warehouse", "Review order details in email", "1 – 2 Hours"],
                ["Processing", "Picking, scanning, serial logging & packing", "Order can no longer be edited", "4 – 12 Hours"],
                ["Shipped", "Manifested and handed to carrier", "Track shipment via carrier link", "Carrier Transit"],
                ["Out for Delivery", "Loaded on final delivery vehicle", "Ensure adult recipient available", "Day of Delivery"],
                ["Delivered", "Delivered to doorstep / signed for", "Inspect outer package within 48h", "Completed"],
            ]
        },
        # Page 14
        {
            "title": "Section 5 — Cancellations & Address Modifications",
            "section": "5.2 Changing Shipping Address & Order Cancellation",
            "text": [
                "TechMart provides customers with a narrow operational window to modify or cancel orders prior to warehouse packaging.",
            ],
            "bullets": [
                "2-Hour Grace Period: Customers can modify shipping address, contact phone number, or cancel order entirely within 2 hours of checkout via My Account &rarr; Order Details.",
                "Cut-Off Boundary: Once an order reaches 'Processing' status, automated conveyor and sorting systems prevent manual retrieval. The order cannot be modified or canceled.",
                "Carrier Address Intercept: If the package has already shipped, an address diversion request can be submitted to FedEx or UPS for a non-refundable $15.00 carrier administrative fee.",
                "Canceled Order Refunds: Orders canceled before fulfillment are refunded within 2 hours to store credit or 3–5 business days to payment card.",
            ]
        },
        # Page 15
        {
            "title": "Section 5 — Pre-Orders & Allocation Management",
            "section": "5.3 Pre-Orders, Backorders & Release Day Guarantees",
            "text": [
                "Pre-orders allow customers to reserve highly anticipated gaming consoles, graphic cards, and flagship mobile devices prior to official launch dates.",
            ],
            "bullets": [
                "Billing Policy: Pre-orders are charged in full at checkout to guarantee allocation priority in the national warehouse queue.",
                "Cancellation Rights: Customers may cancel any pre-order free of charge up to 24 hours prior to the official carrier ship date for a 100% full refund.",
                "Delayed Launch Date Protocol: If an OEM delays product launch by more than 30 calendar days, TechMart issues a courtesy $10 store credit coupon and provides an opt-out refund prompt.",
                "Backorder Delivery Estimates: If inventory is exhausted, estimated replenishment dates are updated bi-weekly in the order tracking portal.",
            ]
        },
        # Page 16
        {
            "title": "Section 6 — Domestic Shipping Options & SLAs",
            "section": "6.1 Domestic Courier Services & Delivery Timelines",
            "text": [
                "TechMart partners with FedEx, UPS, and the United States Postal Service (USPS) to deliver packages across all 50 states.",
            ],
            "table": [
                ["Shipping Method", "Transit Timeframe", "Base Shipping Cost", "Order Cut-Off Time"],
                ["Standard Ground", "5 – 7 Business Days", "$5.99 (Free over $35)", "11:59 PM EST Daily"],
                ["Expedited Shipping", "2 – 3 Business Days", "$9.99 Flat Rate", "3:00 PM EST Mon–Fri"],
                ["Priority Overnight", "Next Business Day (by 10:30 AM)", "$24.99 Flat Rate", "2:00 PM EST Mon–Fri"],
                ["Same-Day Local Courier", "Same Day (4:00 PM – 9:00 PM)", "$14.99 Flat Rate", "12:00 PM Local Time"],
                ["In-Store Pickup (BOPIS)", "Ready in 2 – 4 Hours", "Free on all orders", "Store closing hours"],
            ],
            "bullets": [
                "PO Boxes & Military Addresses: APO/FPO/DPO deliveries are handled exclusively via USPS Priority Mail (7–21 business days). Hazardous lithium batteries cannot be shipped to APO boxes.",
            ]
        },
        # Page 17
        {
            "title": "Section 6 — Free Shipping Thresholds & Freight",
            "section": "6.2 Threshold Rules & White-Glove Heavy Freight",
            "text": [
                "Qualifying for free shipping depends on total cart value, loyalty tier status, and physical dimensions of the merchandise.",
            ],
            "bullets": [
                "Standard Free Shipping: Cart total must equal or exceed $35.00 calculated after all promotional discounts and prior to state sales tax.",
                "TechMart Plus Member Perk: Plus members receive complimentary zero-minimum free shipping on all orders regardless of cart value.",
                "Heavy Freight Deliveries: Televisions 65 inches and above, server racks, and oversized appliances exceeding 75 lbs ship via specialized freight carriers.",
                "Scheduled White-Glove Fee: Optional white-glove inside room placement, unboxing, and debris removal is available for $49.99 for freight items.",
            ]
        },
        # Page 18
        {
            "title": "Section 6 — Missed Deliveries & Transit Damage",
            "section": "6.3 Failed Deliveries, Hold Windows & Transit Claims",
            "text": [
                "Couriers follow strict signature and holding protocols to safeguard high-value electronics from package theft.",
            ],
            "bullets": [
                "Three Delivery Attempts: Carriers make up to three consecutive delivery attempts before redirecting the parcel.",
                "3-Day Carrier Pickup Window: If all attempts fail, the carrier holds the parcel at a local pickup facility for 3 business days.",
                "Return to Sender Protocol: After 3 days of non-collection, the parcel is returned to TechMart warehouse. The order is automatically canceled and refunded minus an outbound shipping fee of $6.99 (or $19.99 for freight).",
                "Damaged in Transit Claims: Customers must photograph packaging damage and submit a claim within 48 hours of delivery. TechMart immediately ships an expedited replacement at no extra charge.",
            ]
        },
        # Page 19
        {
            "title": "Section 7 — International Shipping Coverage",
            "section": "7.1 Global Shipping Destinations & Customs Hubs",
            "text": [
                "TechMart delivers consumer electronics across 68 countries worldwide through integrated partnerships with DHL Express and FedEx International.",
            ],
            "bullets": [
                "North America: Canada and Mexico.",
                "Europe: United Kingdom, Germany, France, Italy, Spain, Netherlands, Switzerland, and 21 other EU member states.",
                "Asia-Pacific: Japan, South Korea, Australia, New Zealand, Singapore, and Malaysia.",
                "Middle East & South Asia: UAE, Saudi Arabia, Qatar, and Pakistan.",
                "Export Restrictions: High-performance cryptographic enterprise routers, dual-use thermal imaging drones, and lithium battery banks exceeding 100Wh cannot be shipped internationally due to US Department of Commerce export controls.",
            ]
        },
        # Page 20
        {
            "title": "Section 7 — International Shipping Rates & Times",
            "section": "7.2 Country Shipping Matrix & Delivery SLAs",
            "text": [
                "International transit times are calculated from dispatch and exclude local customs inspection holding periods.",
            ],
            "table": [
                ["Destination Region", "Standard Shipping SLA", "Express Shipping SLA", "Starting Base Cost"],
                ["Canada", "5 – 8 Business Days", "2 – 4 Business Days", "$14.99 USD"],
                ["United Kingdom & EU", "7 – 12 Business Days", "3 – 6 Business Days", "$19.99 USD"],
                ["Australia & New Zealand", "8 – 14 Business Days", "4 – 7 Business Days", "$24.99 USD"],
                ["East & Southeast Asia", "7 – 14 Business Days", "3 – 6 Business Days", "$22.99 USD"],
                ["Middle East & South Asia", "10 – 18 Business Days", "5 – 8 Business Days", "$27.99 USD"],
            ]
        },
        # Page 21
        {
            "title": "Section 7 — Customs, Tariffs & International Returns",
            "section": "7.3 Import Duties, DDU/DDP & Currency Conversion",
            "text": [
                "All international shipments are handled on a Delivery Duty Unpaid (DDU) basis unless the customer selects the prepaid DDP checkout option.",
            ],
            "bullets": [
                "Customs Duties & VAT Liability: The recipient is legally responsible for all import duties, VAT/GST taxes, and brokerage clearance charges assessed by local border authorities.",
                "Customs Valuation: TechMart declares the 100% full commercial invoice purchase price. Packages will never be designated as 'Gift' or declared at undervalued amounts.",
                "International Returns Policy: International customers may return items within 30 days of delivery. However, the customer is 100% responsible for return shipping and insurance costs. TechMart prepaid return labels are valid only within the US.",
                "Currency Exchange Rules: All refunds are executed in USD to the original card. The customer's card issuer or bank determines the exchange rate applied when converting back to Euros, Pounds, or Rupees.",
            ]
        },
        # Page 22
        {
            "title": "Section 8 — Standard Return Policy",
            "section": "8.1 General 30-Day Consumer Return Window",
            "text": [
                "TechMart accepts returns on the vast majority of brand-new products within 30 days of confirmed carrier delivery.",
            ],
            "bullets": [
                "Condition Requirements: Products must be returned in like-new, fully functional condition with all original manufacturer packaging, manuals, accessories, UPC barcodes, and inserts intact.",
                "Personal Data Responsibility: Customers must sign out of all cloud accounts (Apple iCloud, Google Account, Microsoft ID) and perform a factory reset before returning laptops, tablets, or smartphones.",
                "Proof of Purchase: Valid order confirmation email, printed store receipt, or TechMart Plus account phone number required for return authorization.",
            ]
        },
        # Page 23
        {
            "title": "Section 8 — Category-Specific Return Windows",
            "section": "8.2 Return Windows by Product Category",
            "text": [
                "Specific electronic categories have tailored return horizons due to rapid depreciation and sanitation requirements.",
            ],
            "table": [
                ["Product Category", "Standard Return Window", "TechMart Plus Member Window", "Mandatory Return Condition"],
                ["Smartphones & Tablets", "14 Days from delivery", "30 Days from delivery", "Factory reset, zero PIN locks"],
                ["Laptops & Desktops", "14 Days from delivery", "30 Days from delivery", "Original box, wiped personal data"],
                ["Televisions & Projectors", "30 Days from delivery", "45 Days from delivery", "Original internal foam packaging"],
                ["Accessories & Cables", "90 Days from delivery", "90 Days from delivery", "Unused preferred; functional used accepted"],
                ["Wearables & Smartwatches", "14 Days from delivery", "30 Days from delivery", "Like-new, zero skin contact hygiene wear"],
                ["Gaming Consoles", "30 Days from delivery", "30 Days from delivery", "Factory reset, controller included"],
            ]
        },
        # Page 24
        {
            "title": "Section 8 — Restocking Fees & Non-Returnable Items",
            "section": "8.3 Restocking Deductions & Final Sale Items",
            "text": [
                "Restocking deductions apply to opened consumer merchandise returned solely for customer change-of-mind reasons.",
            ],
            "bullets": [
                "15% Restocking Fee: Applies to opened laptops, smartphones, tablets, cameras, and drones returned for change of mind. Deducted automatically from the refund.",
                "0% Restocking Fee: Unopened products in factory-sealed packaging and verified defective or damaged hardware incur ZERO restocking fees.",
                "Non-Returnable Merchandise: Digital software licenses, downloadable gaming product keys, gift cards, prepaid airtime cards, personalized/engraved products, and opened in-ear headphones (sanitary hygiene policy).",
                "Clearance Items: Products marked 'Liquidation Final Sale' are non-returnable and non-refundable unless damaged on arrival.",
            ]
        },
        # Page 25
        {
            "title": "Section 8 — Refund Methods & Bonus Store Credit",
            "section": "8.4 Refund Timelines & 10% Store Credit Incentive",
            "text": [
                "Once returns arrive at the central returns facility, technical staff inspect items within 2 business days.",
            ],
            "table": [
                ["Refund Destination", "Transfer Duration", "Deductions Applied", "Bonus Incentive"],
                ["Original Credit/Debit Card", "3 – 5 Business Days", "Minus return fee & restocking fee", "Standard 100% refund"],
                ["Bank Transfer (ACH)", "3 – 7 Business Days", "Minus return fee & restocking fee", "Standard 100% refund"],
                ["TechMart Store Credit", "Instant (Within 1 hour)", "Minus return fee & restocking fee", "10% BONUS Added to Balance"],
                ["Klarna / Affirm Account", "3 – 5 Business Days", "Adjusts remaining balance owed", "Per BNPL terms"],
            ]
        },
        # Page 26
        {
            "title": "Section 9 — Manufacturer Warranty Coverage",
            "section": "9.1 OEM Warranty Protection & TechMart Liaison Role",
            "text": [
                "All brand-new electronic hardware sold by TechMart includes the original manufacturer's factory warranty.",
            ],
            "bullets": [
                "1-Year Baseline: Most computers, displays, and smartphones carry a 12-month manufacturer warranty covering internal component defects, screen backlight failures, and battery defects.",
                "TechMart as Direct Liaison: Customers do not need to contact overseas manufacturers directly. TechMart coordinates authorized manufacturer warranty claims, packing, and courier dispatch free of charge.",
                "Warranty Exclusions: Water damage, cracked screens caused by drops, unauthorized third-party board repairs, firmware rooting/jailbreaking, and power surge damage without surge protector.",
            ]
        },
        # Page 27
        {
            "title": "Section 9 — TechCare Basic Extended Warranty",
            "section": "9.2 TechCare Basic Plan Specifications & Deductibles",
            "text": [
                "TechCare Basic extends consumer protection beyond the standard factory warranty period.",
            ],
            "bullets": [
                "2-Year Total Coverage: Extends manufacturer hardware failure coverage to 24 months from the purchase date.",
                "Accidental Damage Claim: Includes exactly 1 accidental damage claim (covers drops, cracked glass, or liquid spills) subject to a standard $49.00 deductible.",
                "Power Surge Protection: 100% covered from day one with zero deductible.",
                "Plan Pricing: Tiered between $29.99 and $79.99 depending on retail equipment value. Must be purchased within 30 days of device sale.",
            ]
        },
        # Page 28
        {
            "title": "Section 9 — TechCare Plus Extended Warranty",
            "section": "9.3 TechCare Plus Comprehensive Protection",
            "text": [
                "TechCare Plus is our most popular 3-year warranty tier for professionals and students.",
            ],
            "table": [
                ["Coverage Feature", "TechCare Basic", "TechCare Plus", "TechCare Premium"],
                ["Hardware Failure Duration", "2 Years", "3 Years", "4 Years"],
                ["Accidental Damage Claims", "1 Claim total", "2 Claims total", "Unlimited Claims"],
                ["Battery Replacement", "Not included", "Free if health <80%", "Free if health <80%"],
                ["Free Loaner Device", "No", "Yes (if repair >7 days)", "Yes (Immediate overnight)"],
                ["Loss & Theft Protection", "Not included", "Not included", "Included with deductible"],
                ["Plan Price Range", "$29 – $79", "$99 – $199", "$199 – $349"],
            ]
        },
        # Page 29
        {
            "title": "Section 9 — TechCare Premium & Fleet Coverage",
            "section": "9.4 TechCare Premium & B2B Multi-Device Plans",
            "text": [
                "TechCare Premium offers 4 years of comprehensive coverage designed for enterprise fleets and high-end hardware.",
            ],
            "bullets": [
                "4 Years Complete Hardware Protection: Covers internal components, motherboards, GPUs, power supplies, and storage drives.",
                "Unlimited Screen Repairs: No limit on cracked screen replacements with a reduced $29.00 copay.",
                "Theft & Total Loss Coverage: If a device is stolen, an insurance police report must be filed within 72 hours; replacement units ship within 2 business days following a 20% hardware deductible.",
                "Fleet Commercial Warranty: Companies purchasing 10+ devices qualify for unified billing and pool accidental damage claims across the entire organization.",
            ]
        },
        # Page 30
        {
            "title": "Section 10 — Technical Support Architecture",
            "section": "10.1 Diagnostic Tiers & Escalation Workflows",
            "text": [
                "TechMart provides structured technical assistance across three unified tiers to resolve software, firmware, and hardware faults.",
            ],
            "bullets": [
                "Tier 1: Frontline AI & Digital Agents: Available 24/7/365. Handles order queries, return setup, warranty status lookups, and basic device resets.",
                "Tier 2: Certified Remote Technicians: Staffed 8:00 AM – 10:00 PM EST. Handles driver conflicts, network configuration, and operating system recovery via SecureConnect.",
                "Tier 3: In-Store Master Technicians: Walk-in lab staffed by Apple-certified and CompTIA A+ technicians for board-level repairs, screen replacements, and chip-level soldering.",
                "Auto-Escalation Rule: Any technical chat inquiry that remains unresolved after two troubleshooting attempts is automatically transferred to a Tier-2 human specialist within 90 seconds.",
            ]
        },
        # Page 31
        {
            "title": "Section 10 — Troubleshooting Trees: Connectivity & Power",
            "section": "10.2 Wi-Fi, Bluetooth & Power Diagnostic Steps",
            "text": [
                "Standard operating procedures for customer-facing frontline troubleshooting.",
            ],
            "bullets": [
                "Wi-Fi Connection Failure: (1) Toggle Airplane mode on for 15s then off. (2) Forget Wi-Fi network and re-enter WPA3 key. (3) Verify router 2.4GHz / 5GHz band steering. (4) Flush DNS and reset network adapter.",
                "Device Fails to Power On: (1) Disconnect all external USB peripherals. (2) Connect to official OEM wall adapter for 30 minutes. (3) Perform hard power-cycle (hold power button for 30 seconds). (4) Test wall outlet with another appliance.",
                "Bluetooth Audio Latency & Drops: (1) Keep device within 1 meter of receiver. (2) Remove existing pairing and re-pair. (3) Verify earphone firmware via companion app.",
            ]
        },
        # Page 32
        {
            "title": "Section 10 — Remote Diagnostic Protocols",
            "section": "10.3 SecureConnect Screen Sharing & Data Safeguards",
            "text": [
                "TechMart SecureConnect allows technicians to access customer computers remotely with explicit one-time authorization.",
            ],
            "bullets": [
                "Encrypted Session: All remote desktop streams utilize TLS 1.3 and end-to-end 256-bit AES encryption.",
                "One-Time PIN Code: Sessions can only begin when the customer generates and reads a 6-digit dynamic PIN code from the SecureConnect client.",
                "Visual Transparency: The customer sees every cursor movement on screen. The customer can sever the connection instantly by clicking 'Disconnect' or closing their laptop lid.",
                "Zero File Access: Technicians cannot transfer files from the customer's machine without an explicit on-screen customer dialog approval.",
                "Service Pricing: Complimentary for all TechCare Plus and Premium subscribers. A flat fee of $49.00 per 45-minute session applies to non-subscribers.",
            ]
        },
        # Page 33
        {
            "title": "Section 11 — In-Store Fix Desk Services",
            "section": "11.1 Retail Repair Lab Turnaround Times & Walk-Ins",
            "text": [
                "Every TechMart retail superstore contains an in-store Fix Desk equipped with ESD-safe workstations and certified diagnostic tools.",
            ],
            "table": [
                ["Repair Service", "Typical Turnaround Time", "In-Store Lab Cost", "Warranty Status"],
                ["Smartphone Screen Replacement", "1 – 2 Hours", "$89 – $249", "Free under TechCare"],
                ["Battery Replacement", "45 Minutes", "$49 – $89", "Free if TechCare health <80%"],
                ["Laptop Keyboard / Trackpad", "2 – 4 Hours", "$79 – $169", "OEM covered or TechCare"],
                ["Cooling Fan Clean & Repaste", "1 Hour", "$39.99 Flat", "Maintenance service"],
                ["Water Damage Ultrasonic Clean", "24 – 48 Hours", "$99.00 Quote", "Non-warranty diagnostic"],
            ]
        },
        # Page 34
        {
            "title": "Section 11 — Data Migration & Virus Removal",
            "section": "11.2 PC Data Transfer, OS Reinstallation & Security",
            "text": [
                "Software and data services protect user productivity when upgrading hardware or recovering from software corruption.",
            ],
            "bullets": [
                "Complete PC Data Migration: Transfer up to 1TB of user files, documents, photos, and browser profiles from old PC/Mac to new device ($59.00; free with TechCare Plus).",
                "Clean Operating System Reinstall: Factory fresh installation of Windows 11 Pro or macOS with driver optimization ($49.00).",
                "Malware & Spyware Removal: Deep heuristic scan, rootkit eradication, and antivirus configuration ($79.00).",
                "Data Recovery Diagnostic: Free initial inspection. Logical data extraction from failing drives starts at $149.00 (cleanroom mechanical recovery quoted separately).",
            ]
        },
        # Page 35
        {
            "title": "Section 11 — In-Home Installation Services",
            "section": "11.3 TV Mounting, Home Theatre & Smart Hub Setup",
            "text": [
                "Certified TechMart field installers provide in-home setup, wall-mounting, and network integration.",
            ],
            "table": [
                ["Installation Package", "Scope of In-Home Work", "Standard Price", "Plus Member Price"],
                ["Standard TV Wall Mount", "Up to 65\" TV mounting, bracket included, basic wire concealment", "$129.99", "$99.99"],
                ["Large TV Wall Mount (66\"–98\")", "Heavy-duty dual-arm bracket, wall stud reinforcement, wire chase", "$199.99", "$149.99"],
                ["Home Theatre Audio Setup", "5.1/7.1 speaker placement, receiver tuning, subwoofer calibration", "$249.99", "$199.99"],
                ["Mesh Wi-Fi Installation", "Up to 3 mesh nodes configured, dead zone elimination, QoS setup", "$99.99", "$69.99"],
            ]
        },
        # Page 36
        {
            "title": "Section 12 — Account Security & Architecture",
            "section": "12.1 User Accounts, Passwords & Encryption Standards",
            "text": [
                "Customer profile data and credentials are secure in accordance with ISO 27001 and NIST 800-63B standards.",
            ],
            "bullets": [
                "Password Storage: TechMart never stores plain-text passwords. All credentials are encrypted using salted bcrypt hashing with a work factor of 12.",
                "Complexity Enforcement: Passwords must contain a minimum of 12 characters, including uppercase, lowercase, numbers, and symbols.",
                "Inactivity Session Expiry: Web sessions expire automatically after 30 days of inactivity, or 15 minutes of inactivity on payment and account credential pages.",
                "Password Reset Links: Sent exclusively to the verified registered email and expire exactly 15 minutes after issuance for security.",
            ]
        },
        # Page 37
        {
            "title": "Section 12 — Two-Factor Authentication (2FA)",
            "section": "12.2 Multi-Factor Security Options & Account Recovery",
            "text": [
                "Two-Factor Authentication adds an indispensable layer of defense against credential stuffing and brute-force intrusion.",
            ],
            "bullets": [
                "Supported 2FA Methods: Time-based One-Time Password (TOTP) apps (Google Authenticator, Microsoft Authenticator, Authy), SMS text codes, and hardware security keys (FIDO2 / YubiKey).",
                "Mandatory 2FA Enforcement: 2FA is strictly mandatory for all B2B Corporate business accounts and administrator accounts.",
                "Lost 2FA Recovery Protocol: If a customer loses their 2FA device and backup codes, account recovery requires government photo ID verification processed by the Trust & Safety team within 24 hours.",
            ]
        },
        # Page 38
        {
            "title": "Section 12 — Fraud Prevention & Suspensions",
            "section": "12.3 Account Locks, Dispute Abuse & Suspension Appeals",
            "text": [
                "Automated risk scoring algorithms monitor transaction velocity to protect consumers from stolen card fraud.",
            ],
            "bullets": [
                "Automated Security Lockout: Accounts are locked for 30 minutes following 5 consecutive failed password attempts.",
                "Fraud Trigger Triggers: Mismatched credit card billing address country vs shipping IP address, rapid multi-order gift card draining, or unverified high-value orders trigger temporary review holds.",
                "Chargeback Abuse Policy: Filing an unauthorized bank chargeback before contacting TechMart customer support results in temporary account suspension pending resolution.",
                "Suspension Appeals: Appeals are reviewed by submitting government identification to security@techmart.com within 2 business days.",
            ]
        },
        # Page 39
        {
            "title": "Section 13 — TechMart Plus Loyalty Program",
            "section": "13.1 Loyalty Program Overview & Annual Tiers",
            "text": [
                "TechMart Plus is our premium multi-tier subscription program delivering cashback rewards, exclusive discounts, and white-glove support.",
            ],
            "table": [
                ["Membership Tier", "Annual Spend Requirement", "Annual Membership Fee", "Core Tier Benefits"],
                ["Silver Tier", "$0 – $999 / year", "Free to Join", "2% Cashback, Free shipping over $50"],
                ["Gold Tier", "$1,000 – $2,999 / year", "$99 / year (or $9.99/mo)", "4% Cashback, Free expedited shipping, 30-day returns"],
                ["Platinum Tier", "$3,000+ / year", "$179 / year (or $19.99/mo)", "6% Cashback, Free same-day shipping, Dedicated phone line, Free repair labor"],
            ]
        },
        # Page 40
        {
            "title": "Section 13 — Points Accrual & Redemption",
            "section": "13.2 Cashback Calculations & Points Expiration",
            "text": [
                "Cashback rewards accumulate automatically on all eligible retail and online merchandise purchases.",
            ],
            "bullets": [
                "Points Accrual Value: 100 points equals exactly $1.00 in spendable store credit.",
                "Accrual Timing: Earned cashback points post to the customer account within 48 hours following carrier delivery confirmation.",
                "Minimum Redemption Threshold: Points can be redeemed at checkout starting at a minimum of 500 points ($5.00 value).",
                "Points Expiration Window: Unused loyalty points expire exactly 18 months from the date they were credited to the account.",
                "Exclusions: Gift card purchases, third-party carrier shipping fees, and sales taxes do not earn loyalty cashback points.",
            ]
        },
        # Page 41
        {
            "title": "Section 13 — Family Plans & Trade-In Guarantees",
            "section": "13.3 Family Sub-Accounts & Platinum 12-Month Upgrade",
            "text": [
                "Family and hardware upgrade privileges ensure shared benefits across households.",
            ],
            "bullets": [
                "Family Plan Add-On: Gold and Platinum members may add up to 4 family members for $4.99/month per additional user. Family members enjoy shared expedited shipping while maintaining private purchase histories.",
                "Platinum Annual Upgrade Guarantee: Platinum members can trade in flagship smartphones or laptops every 12 months for guaranteed trade-in credit of at least 50% of the original retail value toward a next-generation device.",
                "Cancellation & Downgrades: Members may cancel their subscription at any time. If canceled within 14 days without using benefits, a 100% full refund is issued. After 14 days, unused full months are refunded prorated. Earned cashback remains valid for 90 days following cancellation.",
            ]
        },
        # Page 42
        {
            "title": "Section 14 — TechMart for Business",
            "section": "14.1 Corporate Accounts & Dedicated B2B Portal",
            "text": [
                "TechMart for Business provides corporate procurement solutions, volume discount pricing, and dedicated enterprise account executives for over 22,000 corporate clients.",
            ],
            "bullets": [
                "Registration Requirements: Companies register at techmart.com/business providing their federal Employer Identification Number (EIN) or VAT ID, company email, and expected annual tech spend.",
                "Approval Timeline: Corporate accounts are verified and activated within 1 to 2 business days.",
                "Dedicated B2B Portal: Enables multi-seat employee purchasing with customizable spending limits, approval hierarchies, and downloadable monthly consolidated invoices.",
            ]
        },
        # Page 43
        {
            "title": "Section 14 — Business Volume Discounts & Net Terms",
            "section": "14.2 Tiered Corporate Discounts & Invoicing Terms",
            "text": [
                "Business accounts receive automated tiered pricing applied dynamically at checkout based on monthly procurement volume.",
            ],
            "table": [
                ["Monthly Spend Bracket", "Volume Discount", "Credit Payment Terms", "Dedicated Account Executive"],
                ["$1,000 – $4,999", "3% Volume Discount", "Net-15 Invoice Terms", "No (Shared Business Desk)"],
                ["$5,000 – $19,999", "7% Volume Discount", "Net-30 Invoice Terms", "No (Priority Support Queue)"],
                ["$20,000 – $49,999", "12% Volume Discount", "Net-30 Invoice Terms", "Yes (Dedicated Account Manager)"],
                ["$50,000 and above", "18% Custom Negotiated", "Net-60 Invoice Terms", "Yes (Senior VP Account Director)"],
            ]
        },
        # Page 44
        {
            "title": "Section 14 — Mobile Device Management & Loaner Fleet",
            "section": "14.3 MDM Zero-Touch Enrollment & Replacement Fleet",
            "text": [
                "Corporate fleet management tools eliminate IT deployment friction for enterprise IT administrators.",
            ],
            "bullets": [
                "Zero-Touch MDM Enrollment: TechMart can pre-enroll laptops, tablets, and phones directly into Apple Business Manager (ABM) or Microsoft Intune/Autopilot prior to warehouse dispatch for $15.00 per unit.",
                "Corporate Loaner Device Fleet: Business clients with 10 or more registered hardware units receive complimentary overnight loaner laptops during repair periods. Loaners may be held up to 14 calendar days.",
                "Custom Imaging: Pre-loading proprietary company operating system disk images available for bulk orders of 50 units or more.",
            ]
        },
        # Page 45
        {
            "title": "Section 15 — Environmental & Recycling Program",
            "section": "15.1 GreenCycle E-Waste Standards & Drop-Off Zones",
            "text": [
                "TechMart operates one of the nation's largest certified e-waste recycling initiatives, processing over 15 million pounds of consumer electronics annually.",
            ],
            "bullets": [
                "Accepted Items: Desktop computers, laptops, monitors (up to 60 inches), tablets, phones, cables, chargers, power banks, and ink cartridges (all brands accepted, any condition).",
                "Non-Accepted Items: Large household appliances (refrigerators, washers), CRT monitors with broken tubes, automotive lead-acid batteries, and commercial industrial machinery.",
                "Store Drop-Off: Dedicated GreenCycle bins are positioned at the entrance of all 380 TechMart retail superstores.",
                "Environmental Bonus: Customers drop off e-waste receive 100 TechMart Plus loyalty points per recycling visit.",
            ]
        },
        # Page 46
        {
            "title": "Section 15 — Trade-In Valuation & Battery Safety",
            "section": "15.2 Device Appraisal Matrix & Lithium Battery Hazards",
            "text": [
                "Trade-in allowances give functional electronics a second lifecycle through certified refurbishing.",
            ],
            "bullets": [
                "Instant Trade-In Valuation: Evaluate working devices online at techmart.com/tradein to receive a prepaid shipping kit or bring items directly to any retail Fix Desk.",
                "Valuation Grades: Grade A (Mint, no scratches), Grade B (Minor cosmetic scuffs), Grade C (Functional with visible wear). Even non-functional broken devices receive a minimum $25.00 recycling voucher.",
                "CRITICAL BATTERY SAFETY WARNING: Lithium-ion batteries showing signs of swelling, bulging, cracking, hissing, or chemical leakage must NEVER be shipped via postal carriers. Swollen batteries must be brought immediately in a fire-safe container to an in-store Fix Desk for hazardous disposal.",
            ]
        },
        # Page 47
        {
            "title": "Section 16 — Privacy & Data Governance",
            "section": "16.1 Information Collection, Storage & Zero-Sale Guarantee",
            "text": [
                "TechMart respects consumer privacy and adheres to the highest global data governance principles.",
            ],
            "table": [
                ["Data Category", "Collected Elements", "Operational Purpose", "Retention Horizon"],
                ["Account Profile", "Name, verified email, phone, hashed password", "Account authentication", "Retained until deletion"],
                ["Transaction Records", "Order history, SKU details, invoice total", "Tax & legal compliance", "7 Years (Mandatory tax law)"],
                ["Device Hardware Data", "Serial numbers, IMEI, TechCare claims", "Warranty & theft registry", "5 Years from purchase"],
                ["Support Transcripts", "Live chat logs, AI interactions, emails", "Quality assurance & training", "3 Years (24h for raw AI chats)"],
            ],
            "bullets": [
                "ABSOLUTE ZERO-SALE GUARANTEE: TechMart NEVER sells, rents, monetizes, or trades personal customer information, purchase histories, or phone numbers to third-party advertisers, data brokers, or marketing networks under any circumstance.",
            ]
        },
        # Page 48
        {
            "title": "Section 16 — Consumer Privacy Rights (GDPR & CCPA)",
            "section": "16.2 Statutory Data Rights & Deletion Request Workflows",
            "text": [
                "Customers in California, the European Union, the United Kingdom, and worldwide possess enforceable data autonomy rights.",
            ],
            "bullets": [
                "Right to Access / Portability: Request an export of all personal data in structured JSON or CSV format at any time.",
                "Right to Rectification: Correct inaccurate or outdated account details in user profile settings.",
                "Right to Erasure (Right to be Forgotten): Request permanent account and data deletion via Privacy Settings or by emailing privacy@techmart.com.",
                "Deletion Timelines: Account data is permanently purged across all live systems within 30 days of request (excluding financial records retained for 7 years under statutory tax law).",
                "Cookie Preferences: Opt-out of non-essential marketing cookies via the persistent consent banner in footer settings.",
            ]
        },
        # Page 49
        {
            "title": "Section 17 — Complaint Escalation & Dispute Resolution",
            "section": "17.1 Tiered Complaint Workflow & Service Guarantees",
            "text": [
                "When service breakdowns occur, TechMart operates an expedited four-step escalation framework to achieve fair customer resolution.",
            ],
            "bullets": [
                "Step 1: Contact Standard Support: Chat, phone, or email a frontline specialist (90% of issues resolved here).",
                "Step 2: On-Demand Supervisor Escalation: If unsatisfied, request an immediate supervisor transfer. Supervisors are guaranteed available on chat or phone within 15 minutes.",
                "Step 3: Formal Complaint Submission: Submit a ticket at techmart.com/complaints. A formal case tracking number (format CMP-XXXXX) is generated within 1 hour.",
                "Step 4: Executive Senior Specialist Contact: A senior case manager reviews the file and contacts the customer with a definitive resolution within 24 hours.",
                "External Arbitration: If unresolved, consumers may file dispute cases with the Better Business Bureau (bbb.org), Consumer Financial Protection Bureau (cfpb.gov), or state Attorney General.",
            ]
        },
        # Page 50
        {
            "title": "Section 17 — Emergency Protocols & Contact Directory",
            "section": "17.2 Critical Safety Hazards & Master Directory",
            "text": [
                "<b>CRITICAL PRODUCT SAFETY PROTOCOL:</b> If an electronic device emits a burning smell, smoke, sparks, electrical shock, or displays battery swelling, the customer must immediately STOP using the device, disconnect charging cables, and place the device on a non-flammable surface (such as concrete or ceramic tile) away from combustible materials.",
                "Safety incidents bypass all standard warranty queues and receive 24/7 emergency dispatch within 4 hours via 1-800-TECHMART (Extension 9).",
            ],
            "table": [
                ["Support Department", "Contact Method", "Operating Hours", "Guaranteed SLA"],
                ["Customer Support Hotline", "1-800-TECHMART (1-800-832-4627)", "Mon–Sun: 8:00 AM – 10:00 PM EST", "< 5 Minute Wait"],
                ["AI Support Chat", "techmart.com/chat (Web & App)", "24/7/365 Non-Stop", "< 5 Seconds"],
                ["Returns & Refunds Desk", "1-800-TECHMART ext 2", "Mon–Fri: 9:00 AM – 7:00 PM EST", "< 48 Hours Processing"],
                ["TechCare Warranty Claims", "1-800-TECHMART ext 3", "Mon–Fri: 9:00 AM – 7:00 PM EST", "Same-Day Claim Number"],
                ["Business Accounts Desk", "business@techmart.com", "Mon–Fri: 8:00 AM – 8:00 PM EST", "< 4 Hour Response"],
                ["Safety Emergency Hotline", "1-800-TECHMART ext 9", "24/7/365 Emergency Dispatch", "< 4 Hour Escalation"],
                ["Data Privacy & Legal", "privacy@techmart.com / legal@techmart.com", "Mon–Fri: 9:00 AM – 5:00 PM EST", "30 Days (Legal) / 5 Days"],
                ["Formal Complaints Portal", "techmart.com/complaints", "24/7 Submission Intake", "< 1 Hour Case Number"],
            ]
        },
    ]

    for p_idx, page in enumerate(pages_data, start=1):
        # Page Header Title
        story.append(Paragraph(page["title"], h1_style))
        story.append(Paragraph(page["section"], h2_style))
        story.append(Spacer(1, 4))

        # Text paragraphs
        for t in page.get("text", []):
            story.append(Paragraph(t, body_style))

        # Data table if any
        if "table" in page:
            table_data = []
            for r_idx, row in enumerate(page["table"]):
                row_cells = []
                for cell in row:
                    style_to_use = table_header_style if r_idx == 0 else table_cell_style
                    row_cells.append(Paragraph(cell, style_to_use))
                table_data.append(row_cells)

            # Standardized column width to fit nicely in 504pt printable area
            col_count = len(page["table"][0])
            col_width = 504.0 / col_count
            t = Table(table_data, colWidths=[col_width] * col_count)
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                ])
            )
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 4))

        # Bullet points if any
        if "bullets" in page:
            story.append(Spacer(1, 2))
            for b in page["bullets"]:
                story.append(Paragraph(f"• {b}", bullet_style))

        # PageBreak for every page except the last
        if p_idx < 50:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    
    # Verification
    pdoc = pymupdf.open(PDF_FILENAME)
    print(f"Successfully generated {PDF_FILENAME} with exactly {len(pdoc)} pages!")
    pdoc.close()

if __name__ == "__main__":
    build_manual()
