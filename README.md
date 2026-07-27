# Brazilian E-Commerce SQL Analytics

## Project Overview
This project is an end-to-end data pipeline and SQL analytics portfolio piece built during a 24-hour data sprint. It transforms 100,000+ rows of raw, real-world e-commerce data into a fully functional relational database to uncover business insights regarding customer behavior, revenue generation, and supply chain efficiency.

🇧🇷 Brazil E-Commerce Analytics & Customer Segmentation

An end-to-end data engineering and analytics project using Python and SQL to extract actionable business insights from a real-world e-commerce database (100k+ orders).

📊 Key Business Insights

1. Logistics Dictate Customer SatisfactionThe Data: Orders delivered before their estimated date received an average review score of 4.29 / 5.0.  The Data: Orders delivered after their estimated date saw a catastrophic drop in average review score to 2.34 / 5.0.  Actionable Takeaway: Supply chain bottlenecks are  harming brand reputation. The business must prioritize fulfillment speed and set more conservative estimated delivery dates to manage expectations.
2. Payment Architecture & Big SpendersThe Data: Credit cards absolutely dominate the platform, generating over 12.5 million BRL in revenue. Customers also use an average of 3.5 installments when paying by credit card.  Actionable Takeaway: The installment feature is a massive driver for high-ticket items. Marketing campaigns should prominently feature "buy now, pay later" messaging to continue driving conversion on expensive products.
3. Product Quality Outliers The Data: The fraldas_higiene (diapers/hygiene) and moveis_escritorio (office furniture) categories have the lowest average review scores on the platform (3.25 and 3.49, respectively) despite having a statistically significant number of reviews.  Actionable Takeaway: The vendor management team needs to audit the suppliers in these two categories immediately to reduce return rates and customer churn.

🎯 Customer Retention (RFM Model)

Using an advanced RFM (Recency, Frequency, Monetary) segmentation model built entirely in SQL with CTEs and Window Functions, the customer base was classified into distinct marketing groups:

Champions (15,554 customers): Your absolute best customers. They bought recently, buy often, and spend the most.

    Strategy: Reward them. Provide early access to new products, exclusive VIP support, and do not waste margin by sending them heavy discount codes (they will buy anyway).

Loyal (7,792 customers): Reliable customers with high frequency and solid spend, though they may not have purchased in the last few days.

    Strategy: Focus on upselling higher-margin items and introducing a loyalty or referral program to turn them into Champions.

Recent Customer (14,796 customers): High recency but low frequency. They just discovered your brand and made their first purchase.

    Strategy: Capitalize on their current interest. Enter them into an automated onboarding email sequence with a slight discount on their second purchase to build a habit.

At Risk (22,467 customers): "Churning Whales." These customers used to buy frequently and spend a lot, but haven't visited the site in a long time.

    Strategy: Deploy aggressive win-back email campaigns with highly personalized messaging and your biggest discount codes to prevent them from moving to a competitor.

Lost (15,784 customers): Customers with the lowest scores across recency, frequency, and monetary value. They bought a long time ago, didn't spend much, and never came back.

    Strategy: Stop allocating active marketing budget here. Send one final automated "hail mary" reactivation email, and if they don't click, remove them from active mailing lists to protect your email sender reputation.

Other (19,702 customers): The "average" middle-of-the-pack consumers who don't fit the extreme highs or lows of the other buckets.

    Strategy: Keep them engaged with standard promotional newsletters and seasonal sales, testing different messaging to see if they can be pushed into the "Loyal" tier.

![RFM Customer Segments](assets/rfm_result.png)

## Tech Stack
*   **Language:** Python 3.9
*   **Libraries:** `pandas`, `sqlite3`, `os`
*   **Database:** SQLite
*   **Environment:** Jupyter Notebooks / VS Code

---

## The Data Source
The dataset used in this project is the **Brazilian E-Commerce Public Dataset by Olist**, provided by Kaggle. It contains information on 100k orders made at multiple marketplaces in Brazil from 2016 to 2018.

**How to get the data:**
1. Create a free account on [Kaggle](https://www.kaggle.com/).
2. Search for `Brazilian E-Commerce Public Dataset by Olist`.
3. Download the archive and extract the CSV files.
4. Place the extracted CSV files into a folder named `/data` in the root of this repository. *(Note: The raw CSV files are ignored by git due to their size).*

---

## Project Structure
```text
ecommerce-sql-project/
├── data/                  <-- User must create this and add Kaggle CSVs
├── load_data.ipynb        <-- Python ETL script that builds the database
├── olist.db               <-- Generated SQLite database (Ignored in Git)
├── queries/
│   └── rfm_segmentation.sql
├── .gitignore             <-- Excludes environments and heavy data files
└── README.md              <-- Project documentation